"""
SAT Modeler API – High-level constraint language → DIMACS CNF → Solve
=====================================================================

Provides:
  • A MiniZinc-inspired mini-language for Boolean SAT problems.
  • Parser + compiler that turns the high-level model into DIMACS CNF.
  • Endpoints to parse, compile, solve (with any ready solver), and
    manage saved models.

Language reference (BNF-ish):
  model        ::= statement*
  statement    ::= var_decl | constraint | comment
  var_decl     ::= 'var' 'bool' ':' IDENT (',' IDENT)* ';'
  constraint   ::= 'constraint' expr ';'
  expr         ::= or_expr
  or_expr      ::= and_expr ( ('\\/' | 'or') and_expr )*
  and_expr     ::= not_expr ( ('/\\' | 'and') not_expr )*
  not_expr     ::= ('not' | '~' | '!') not_expr | atom
  atom         ::= IDENT
               |   'true' | 'false'
               |   '(' expr ')'
               |   IDENT '->' expr          (implication)
               |   IDENT '<->' expr         (equivalence)
               |   'xor' '(' expr ',' expr ')'
               |   'atmost' '(' INT ',' '[' IDENT (',' IDENT)* ']' ')'
               |   'atleast' '(' INT ',' '[' IDENT (',' IDENT)* ']' ')'
               |   'exactly' '(' INT ',' '[' IDENT (',' IDENT)* ']' ')'
  comment      ::= '%' ... newline   |   '//' ... newline
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# ────────────────────────────────────────────
# Directories
# ────────────────────────────────────────────
MODELS_DIR = Path("/app/data/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)
CNF_DIR = Path("/app/data/generated_cnf")
CNF_DIR.mkdir(parents=True, exist_ok=True)


# ================================================================
# 1.  TOKENIZER
# ================================================================

class TokenKind:
    IDENT = "IDENT"
    INT = "INT"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACK = "LBRACK"
    RBRACK = "RBRACK"
    SEMI = "SEMI"
    COLON = "COLON"
    COMMA = "COMMA"
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    IMPL = "IMPL"
    IFF = "IFF"
    KW_VAR = "KW_VAR"
    KW_BOOL = "KW_BOOL"
    KW_CONSTRAINT = "KW_CONSTRAINT"
    KW_TRUE = "KW_TRUE"
    KW_FALSE = "KW_FALSE"
    KW_XOR = "KW_XOR"
    KW_ATMOST = "KW_ATMOST"
    KW_ATLEAST = "KW_ATLEAST"
    KW_EXACTLY = "KW_EXACTLY"
    KW_SOLVE = "KW_SOLVE"
    KW_SATISFY = "KW_SATISFY"
    EOF = "EOF"


_KEYWORDS = {
    "var": TokenKind.KW_VAR,
    "bool": TokenKind.KW_BOOL,
    "constraint": TokenKind.KW_CONSTRAINT,
    "true": TokenKind.KW_TRUE,
    "false": TokenKind.KW_FALSE,
    "not": TokenKind.NOT,
    "and": TokenKind.AND,
    "or": TokenKind.OR,
    "xor": TokenKind.KW_XOR,
    "atmost": TokenKind.KW_ATMOST,
    "atleast": TokenKind.KW_ATLEAST,
    "exactly": TokenKind.KW_EXACTLY,
    "solve": TokenKind.KW_SOLVE,
    "satisfy": TokenKind.KW_SATISFY,
}


class Token:
    __slots__ = ("kind", "value", "line", "col")

    def __init__(self, kind: str, value: str, line: int, col: int):
        self.kind = kind
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.kind}, {self.value!r}, L{self.line}:{self.col})"


def tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    line = 1
    col = 1
    n = len(source)

    while i < n:
        ch = source[i]

        # Skip whitespace
        if ch in " \t\r":
            i += 1
            col += 1
            continue
        if ch == "\n":
            i += 1
            line += 1
            col = 1
            continue

        # Comments: % … or // …
        if ch == "%" or (ch == "/" and i + 1 < n and source[i + 1] == "/"):
            while i < n and source[i] != "\n":
                i += 1
            continue

        # Two-char operators
        if ch == "/" and i + 1 < n and source[i + 1] == "\\":
            tokens.append(Token(TokenKind.AND, "/\\", line, col))
            i += 2; col += 2; continue
        if ch == "\\" and i + 1 < n and source[i + 1] == "/":
            tokens.append(Token(TokenKind.OR, "\\/", line, col))
            i += 2; col += 2; continue
        if ch == "-" and i + 1 < n and source[i + 1] == ">":
            tokens.append(Token(TokenKind.IMPL, "->", line, col))
            i += 2; col += 2; continue
        if ch == "<" and i + 2 < n and source[i + 1] == "-" and source[i + 2] == ">":
            tokens.append(Token(TokenKind.IFF, "<->", line, col))
            i += 3; col += 3; continue

        # Single-char
        simple = {
            "(": TokenKind.LPAREN, ")": TokenKind.RPAREN,
            "[": TokenKind.LBRACK, "]": TokenKind.RBRACK,
            ";": TokenKind.SEMI, ":": TokenKind.COLON,
            ",": TokenKind.COMMA, "~": TokenKind.NOT,
            "!": TokenKind.NOT,
        }
        if ch in simple:
            tokens.append(Token(simple[ch], ch, line, col))
            i += 1; col += 1; continue

        # Numbers
        if ch.isdigit():
            start = i
            while i < n and source[i].isdigit():
                i += 1
            tokens.append(Token(TokenKind.INT, source[start:i], line, col))
            col += i - start
            continue

        # Identifiers / keywords
        if ch.isalpha() or ch == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            word = source[start:i]
            kind = _KEYWORDS.get(word.lower(), TokenKind.IDENT)
            tokens.append(Token(kind, word, line, col))
            col += i - start
            continue

        raise SyntaxError(f"Unexpected character {ch!r} at line {line} col {col}")

    tokens.append(Token(TokenKind.EOF, "", line, col))
    return tokens


# ================================================================
# 2.  AST
# ================================================================

class ASTNode:
    pass

class VarDecl(ASTNode):
    def __init__(self, names: List[str], line: int):
        self.names = names
        self.line = line

class Constraint(ASTNode):
    def __init__(self, expr: "Expr", line: int):
        self.expr = expr
        self.line = line

class SolveSatisfy(ASTNode):
    def __init__(self, line: int):
        self.line = line

# Expression nodes
class Expr(ASTNode):
    pass

class LitTrue(Expr):
    pass

class LitFalse(Expr):
    pass

class VarRef(Expr):
    def __init__(self, name: str):
        self.name = name

class NotExpr(Expr):
    def __init__(self, child: Expr):
        self.child = child

class AndExpr(Expr):
    def __init__(self, children: List[Expr]):
        self.children = children

class OrExpr(Expr):
    def __init__(self, children: List[Expr]):
        self.children = children

class ImplExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        self.lhs = lhs
        self.rhs = rhs

class IffExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        self.lhs = lhs
        self.rhs = rhs

class XorExpr(Expr):
    def __init__(self, a: Expr, b: Expr):
        self.a = a
        self.b = b

class AtMost(Expr):
    def __init__(self, k: int, variables: List[str]):
        self.k = k
        self.variables = variables

class AtLeast(Expr):
    def __init__(self, k: int, variables: List[str]):
        self.k = k
        self.variables = variables

class Exactly(Expr):
    def __init__(self, k: int, variables: List[str]):
        self.k = k
        self.variables = variables


# ================================================================
# 3.  PARSER
# ================================================================

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, kind: str) -> Token:
        t = self.advance()
        if t.kind != kind:
            raise SyntaxError(
                f"Expected {kind} but got {t.kind} ({t.value!r}) "
                f"at line {t.line} col {t.col}"
            )
        return t

    # ── Top level ──
    def parse(self) -> List[ASTNode]:
        stmts: List[ASTNode] = []
        while self.peek().kind != TokenKind.EOF:
            stmts.append(self._statement())
        return stmts

    def _statement(self) -> ASTNode:
        t = self.peek()
        if t.kind == TokenKind.KW_VAR:
            return self._var_decl()
        if t.kind == TokenKind.KW_CONSTRAINT:
            return self._constraint()
        if t.kind == TokenKind.KW_SOLVE:
            return self._solve()
        raise SyntaxError(
            f"Unexpected token {t.value!r} at line {t.line} col {t.col}. "
            f"Expected 'var', 'constraint', or 'solve'."
        )

    def _var_decl(self) -> VarDecl:
        t = self.expect(TokenKind.KW_VAR)
        self.expect(TokenKind.KW_BOOL)
        self.expect(TokenKind.COLON)
        names = [self.expect(TokenKind.IDENT).value]
        while self.peek().kind == TokenKind.COMMA:
            self.advance()
            names.append(self.expect(TokenKind.IDENT).value)
        self.expect(TokenKind.SEMI)
        return VarDecl(names, t.line)

    def _constraint(self) -> Constraint:
        t = self.expect(TokenKind.KW_CONSTRAINT)
        expr = self._expr()
        self.expect(TokenKind.SEMI)
        return Constraint(expr, t.line)

    def _solve(self) -> SolveSatisfy:
        t = self.expect(TokenKind.KW_SOLVE)
        self.expect(TokenKind.KW_SATISFY)
        self.expect(TokenKind.SEMI)
        return SolveSatisfy(t.line)

    # ── Expressions ──
    def _expr(self) -> Expr:
        return self._iff_expr()

    def _iff_expr(self) -> Expr:
        left = self._impl_expr()
        while self.peek().kind == TokenKind.IFF:
            self.advance()
            right = self._impl_expr()
            left = IffExpr(left, right)
        return left

    def _impl_expr(self) -> Expr:
        left = self._or_expr()
        while self.peek().kind == TokenKind.IMPL:
            self.advance()
            right = self._or_expr()
            left = ImplExpr(left, right)
        return left

    def _or_expr(self) -> Expr:
        children = [self._and_expr()]
        while self.peek().kind == TokenKind.OR:
            self.advance()
            children.append(self._and_expr())
        return children[0] if len(children) == 1 else OrExpr(children)

    def _and_expr(self) -> Expr:
        children = [self._not_expr()]
        while self.peek().kind == TokenKind.AND:
            self.advance()
            children.append(self._not_expr())
        return children[0] if len(children) == 1 else AndExpr(children)

    def _not_expr(self) -> Expr:
        if self.peek().kind == TokenKind.NOT:
            self.advance()
            return NotExpr(self._not_expr())
        return self._atom()

    def _atom(self) -> Expr:
        t = self.peek()

        if t.kind == TokenKind.KW_TRUE:
            self.advance()
            return LitTrue()
        if t.kind == TokenKind.KW_FALSE:
            self.advance()
            return LitFalse()

        if t.kind == TokenKind.LPAREN:
            self.advance()
            e = self._expr()
            self.expect(TokenKind.RPAREN)
            return e

        # Global constraints: xor(a, b), atmost(k, [vars]), etc.
        if t.kind == TokenKind.KW_XOR:
            return self._xor()
        if t.kind in (TokenKind.KW_ATMOST, TokenKind.KW_ATLEAST, TokenKind.KW_EXACTLY):
            return self._cardinality()

        if t.kind == TokenKind.IDENT:
            self.advance()
            # Check for -> or <-> right after ident
            if self.peek().kind == TokenKind.IMPL:
                self.advance()
                rhs = self._expr()
                return ImplExpr(VarRef(t.value), rhs)
            if self.peek().kind == TokenKind.IFF:
                self.advance()
                rhs = self._expr()
                return IffExpr(VarRef(t.value), rhs)
            return VarRef(t.value)

        raise SyntaxError(
            f"Unexpected token {t.value!r} at line {t.line} col {t.col}"
        )

    def _xor(self) -> XorExpr:
        self.expect(TokenKind.KW_XOR)
        self.expect(TokenKind.LPAREN)
        a = self._expr()
        self.expect(TokenKind.COMMA)
        b = self._expr()
        self.expect(TokenKind.RPAREN)
        return XorExpr(a, b)

    def _cardinality(self) -> Expr:
        kind = self.advance()  # atmost / atleast / exactly
        self.expect(TokenKind.LPAREN)
        k = int(self.expect(TokenKind.INT).value)
        self.expect(TokenKind.COMMA)
        self.expect(TokenKind.LBRACK)
        vars_list = [self.expect(TokenKind.IDENT).value]
        while self.peek().kind == TokenKind.COMMA:
            self.advance()
            vars_list.append(self.expect(TokenKind.IDENT).value)
        self.expect(TokenKind.RBRACK)
        self.expect(TokenKind.RPAREN)

        if kind.kind == TokenKind.KW_ATMOST:
            return AtMost(k, vars_list)
        if kind.kind == TokenKind.KW_ATLEAST:
            return AtLeast(k, vars_list)
        return Exactly(k, vars_list)


# ================================================================
# 4.  CNF COMPILER  (Tseitin-style translation)
# ================================================================

class CNFCompiler:
    """Converts AST constraints into DIMACS CNF clauses."""

    def __init__(self):
        self._var_map: Dict[str, int] = {}
        self._next_id = 1
        self._clauses: List[List[int]] = []

    def var_id(self, name: str) -> int:
        if name not in self._var_map:
            self._var_map[name] = self._next_id
            self._next_id += 1
        return self._var_map[name]

    def _aux(self) -> int:
        """Allocate an auxiliary Tseitin variable."""
        vid = self._next_id
        self._next_id += 1
        return vid

    def add_clause(self, lits: List[int]):
        self._clauses.append(lits)

    # ── Public API ──

    def compile(self, stmts: List[ASTNode]) -> Tuple[str, Dict[str, int]]:
        """Return (dimacs_string, variable_map)."""
        declared: set = set()
        for s in stmts:
            if isinstance(s, VarDecl):
                for name in s.names:
                    if name in declared:
                        raise ValueError(f"Variable '{name}' already declared (line {s.line})")
                    declared.add(name)
                    self.var_id(name)  # pre-allocate
            elif isinstance(s, Constraint):
                lit = self._encode(s.expr, declared)
                # The top-level constraint must be true
                self.add_clause([lit])
            elif isinstance(s, SolveSatisfy):
                pass  # no-op

        # Build DIMACS
        lines = [f"p cnf {self._next_id - 1} {len(self._clauses)}"]
        for cl in self._clauses:
            lines.append(" ".join(str(l) for l in cl) + " 0")
        return "\n".join(lines) + "\n", dict(self._var_map)

    # ── Expression encoding ──

    def _encode(self, expr: Expr, declared: set) -> int:
        """Encode an expression and return a literal that represents it."""

        if isinstance(expr, LitTrue):
            v = self._aux()
            self.add_clause([v])
            return v

        if isinstance(expr, LitFalse):
            v = self._aux()
            self.add_clause([-v])
            return -v  # always-false literal

        if isinstance(expr, VarRef):
            if expr.name not in declared:
                raise ValueError(f"Undeclared variable '{expr.name}'")
            return self.var_id(expr.name)

        if isinstance(expr, NotExpr):
            child = self._encode(expr.child, declared)
            return -child

        if isinstance(expr, AndExpr):
            child_lits = [self._encode(c, declared) for c in expr.children]
            # Tseitin: aux <-> (a /\ b /\ ...)
            aux = self._aux()
            # aux -> a, aux -> b, ...
            for cl in child_lits:
                self.add_clause([-aux, cl])
            # a /\ b /\ ... -> aux
            self.add_clause([aux] + [-cl for cl in child_lits])
            return aux

        if isinstance(expr, OrExpr):
            child_lits = [self._encode(c, declared) for c in expr.children]
            aux = self._aux()
            # aux -> (a \/ b \/ ...)
            self.add_clause([-aux] + child_lits)
            # each child -> aux
            for cl in child_lits:
                self.add_clause([aux, -cl])
            return aux

        if isinstance(expr, ImplExpr):
            # a -> b  ≡  ¬a ∨ b
            a = self._encode(expr.lhs, declared)
            b = self._encode(expr.rhs, declared)
            aux = self._aux()
            self.add_clause([-aux, -a, b])
            self.add_clause([aux, a])
            self.add_clause([aux, -b])
            return aux

        if isinstance(expr, IffExpr):
            a = self._encode(expr.lhs, declared)
            b = self._encode(expr.rhs, declared)
            aux = self._aux()
            # aux <-> (a <-> b)
            self.add_clause([-aux, -a, b])
            self.add_clause([-aux, a, -b])
            self.add_clause([aux, a, b])
            self.add_clause([aux, -a, -b])
            return aux

        if isinstance(expr, XorExpr):
            a = self._encode(expr.a, declared)
            b = self._encode(expr.b, declared)
            aux = self._aux()
            self.add_clause([-aux, a, b])
            self.add_clause([-aux, -a, -b])
            self.add_clause([aux, -a, b])
            self.add_clause([aux, a, -b])
            return aux

        # Cardinality constraints — sequential counter encoding
        if isinstance(expr, AtMost):
            return self._encode_atmost(expr.k, expr.variables, declared)

        if isinstance(expr, AtLeast):
            return self._encode_atleast(expr.k, expr.variables, declared)

        if isinstance(expr, Exactly):
            # exactly(k, vars) ≡ atmost(k, vars) /\ atleast(k, vars)
            a = self._encode_atmost(expr.k, expr.variables, declared)
            b = self._encode_atleast(expr.k, expr.variables, declared)
            aux = self._aux()
            self.add_clause([-aux, a])
            self.add_clause([-aux, b])
            self.add_clause([aux, -a, -b])
            return aux

        raise ValueError(f"Unknown expression type: {type(expr)}")

    # ── Cardinality encoding (pairwise for small, sequential counter for large) ──

    def _encode_atmost(self, k: int, var_names: List[str], declared: set) -> int:
        lits = []
        for v in var_names:
            if v not in declared:
                raise ValueError(f"Undeclared variable '{v}'")
            lits.append(self.var_id(v))

        if k >= len(lits):
            # Trivially true
            aux = self._aux()
            self.add_clause([aux])
            return aux

        if k == 0:
            # All must be false
            aux = self._aux()
            for l in lits:
                self.add_clause([-aux, -l])
            neg_all = [aux] + lits
            self.add_clause(neg_all)  # backward: if all false then aux
            return aux

        # Pairwise encoding for small sets, sequential counter for larger
        if len(lits) <= 10 or k == 1:
            return self._atmost_pairwise(k, lits)
        return self._atmost_sequential_counter(k, lits)

    def _atmost_pairwise(self, k: int, lits: List[int]) -> int:
        """At most k true: for every (k+1)-subset, at least one is false."""
        aux = self._aux()
        for combo in combinations(lits, k + 1):
            clause = [-aux] + [-l for l in combo]
            self.add_clause(clause)
        # backward implication (approximate)
        self.add_clause([aux] + lits)  # if none true then trivially ok
        return aux

    def _atmost_sequential_counter(self, k: int, lits: List[int]) -> int:
        n = len(lits)
        # Register[i][j] = "at least j+1 of lits[0..i] are true"
        R = [[self._aux() for _ in range(k)] for _ in range(n)]

        # First variable
        self.add_clause([-lits[0], R[0][0]])
        self.add_clause([lits[0], -R[0][0]])
        for j in range(1, k):
            self.add_clause([-R[0][j]])

        for i in range(1, n):
            # R[i][0] <-> (R[i-1][0] \/ lits[i])
            self.add_clause([-lits[i], R[i][0]])
            self.add_clause([-R[i - 1][0], R[i][0]])
            self.add_clause([lits[i], R[i - 1][0], -R[i][0]])

            for j in range(1, k):
                self.add_clause([-lits[i], -R[i - 1][j - 1], R[i][j]])
                self.add_clause([-R[i - 1][j], R[i][j]])
                self.add_clause([lits[i], R[i - 1][j], -R[i][j]])
                self.add_clause([R[i - 1][j - 1], -R[i][j]])

            # Forbid k+1 true
            self.add_clause([-lits[i], -R[i - 1][k - 1]])

        aux = self._aux()
        self.add_clause([aux])  # always true – constraint encoded directly
        return aux

    def _encode_atleast(self, k: int, var_names: List[str], declared: set) -> int:
        """at_least(k, vars) ≡ at_most(n-k, negated vars)."""
        lits = []
        for v in var_names:
            if v not in declared:
                raise ValueError(f"Undeclared variable '{v}'")
            lits.append(self.var_id(v))

        if k <= 0:
            aux = self._aux()
            self.add_clause([aux])
            return aux

        if k == len(lits):
            aux = self._aux()
            for l in lits:
                self.add_clause([-aux, l])
            self.add_clause([aux] + [-l for l in lits])
            return aux

        # Negate lits and use atmost(n-k)
        neg_names = []
        for v in var_names:
            neg_name = f"__neg_{v}"
            if neg_name not in self._var_map:
                neg_id = self._aux()
                self._var_map[neg_name] = neg_id
                orig = self.var_id(v)
                self.add_clause([neg_id, orig])
                self.add_clause([-neg_id, -orig])
            neg_names.append(neg_name)

        declared_ext = declared | set(neg_names)
        return self._encode_atmost(len(var_names) - k, neg_names, declared_ext)


# ================================================================
# 5.  SOLVER RUNNER (uses the project's real SAT solvers)
# ================================================================

def _find_ready_solvers() -> List[Dict[str, str]]:
    from app.api.solvers import PRE_CONFIGURED_SOLVERS
    ready = []
    for key, s in PRE_CONFIGURED_SOLVERS.items():
        exe = Path(s["executable_path"])
        if exe.exists() and os.access(str(exe), os.X_OK):
            ready.append({"key": key, "name": s["name"], "executable": str(exe)})
    return ready


async def _run_solver_on_cnf(executable: str, cnf_path: str, timeout: int = 30) -> Dict:
    """Run a SAT solver on a CNF file and return structured result."""
    result: Dict[str, Any] = {
        "result": "UNKNOWN",
        "time_seconds": 0,
        "output": "",
    }
    try:
        start = time.time()
        proc = await asyncio.create_subprocess_exec(
            executable, cnf_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            elapsed = time.time() - start
            out = stdout.decode("utf-8", errors="ignore")
            result["time_seconds"] = round(elapsed, 6)
            result["output"] = out[:5000]

            upper = out.upper()
            if proc.returncode == 20 or "UNSATISFIABLE" in upper:
                result["result"] = "UNSAT"
            elif proc.returncode == 10 or "SATISFIABLE" in upper:
                result["result"] = "SAT"
                # Extract assignment
                assignment = _parse_assignment(out)
                if assignment:
                    result["assignment_raw"] = assignment
        except asyncio.TimeoutError:
            proc.kill()
            result["result"] = "TIMEOUT"
            result["time_seconds"] = timeout
    except Exception as e:
        result["result"] = "ERROR"
        result["output"] = str(e)
    return result


def _parse_assignment(output: str) -> List[int]:
    """Parse 'v' lines from solver output into a list of literals."""
    lits: List[int] = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("v ") or line.startswith("V "):
            for tok in line[2:].split():
                try:
                    v = int(tok)
                    if v != 0:
                        lits.append(v)
                except ValueError:
                    pass
    return lits


def _decode_assignment(raw_lits: List[int], var_map: Dict[str, int]) -> Dict[str, bool]:
    """Map DIMACS literal assignment back to named variables."""
    inv = {v: k for k, v in var_map.items() if not k.startswith("__")}
    result: Dict[str, bool] = {}
    for lit in raw_lits:
        vid = abs(lit)
        if vid in inv:
            result[inv[vid]] = lit > 0
    return result


# ================================================================
# 6.  EXAMPLE MODELS
# ================================================================

EXAMPLE_MODELS = [
    {
        "id": "graph_coloring_3",
        "name": "Coloración de Grafo (3 colores, 4 nodos)",
        "description": "Asignar colores a 4 nodos de un grafo triangular + 1 nodo extra de forma que nodos adyacentes tengan colores distintos.",
        "code": """% Coloración de grafo: 4 nodos, 3 colores
% Nodo i, color c -> variable n{i}_c

var bool: n1_r, n1_g, n1_b;
var bool: n2_r, n2_g, n2_b;
var bool: n3_r, n3_g, n3_b;
var bool: n4_r, n4_g, n4_b;

% Cada nodo tiene exactamente 1 color
constraint exactly(1, [n1_r, n1_g, n1_b]);
constraint exactly(1, [n2_r, n2_g, n2_b]);
constraint exactly(1, [n3_r, n3_g, n3_b]);
constraint exactly(1, [n4_r, n4_g, n4_b]);

% Aristas: 1-2, 1-3, 2-3, 3-4
% Nodos adyacentes no comparten color
constraint not(n1_r /\\ n2_r);
constraint not(n1_g /\\ n2_g);
constraint not(n1_b /\\ n2_b);

constraint not(n1_r /\\ n3_r);
constraint not(n1_g /\\ n3_g);
constraint not(n1_b /\\ n3_b);

constraint not(n2_r /\\ n3_r);
constraint not(n2_g /\\ n3_g);
constraint not(n2_b /\\ n3_b);

constraint not(n3_r /\\ n4_r);
constraint not(n3_g /\\ n4_g);
constraint not(n3_b /\\ n4_b);

solve satisfy;
""",
    },
    {
        "id": "pigeonhole_3_2",
        "name": "Principio del Palomar (3 palomas, 2 agujeros)",
        "description": "¿Se pueden meter 3 palomas en 2 agujeros sin que dos palomas compartan agujero? (UNSAT)",
        "code": """% Pigeonhole: 3 palomas, 2 agujeros
% p{i}_{j} = paloma i en agujero j

var bool: p1_1, p1_2;
var bool: p2_1, p2_2;
var bool: p3_1, p3_2;

% Cada paloma en al menos un agujero
constraint p1_1 \\/ p1_2;
constraint p2_1 \\/ p2_2;
constraint p3_1 \\/ p3_2;

% Cada agujero tiene a lo sumo 1 paloma
constraint atmost(1, [p1_1, p2_1, p3_1]);
constraint atmost(1, [p1_2, p2_2, p3_2]);

solve satisfy;
""",
    },
    {
        "id": "simple_logic",
        "name": "Puzzle Lógico Simple",
        "description": "Un acertijo de lógica básica con implicaciones y disyunciones.",
        "code": """% Puzzle lógico
% Si llueve entonces llevo paraguas
% Si llevo paraguas o no llueve, estoy seco
% Llueve.

var bool: llueve, paraguas, seco;

constraint llueve;
constraint llueve -> paraguas;
constraint paraguas \\/ not(llueve) -> seco;
constraint seco;

solve satisfy;
""",
    },
    {
        "id": "n_queens_4",
        "name": "N-Reinas (4×4)",
        "description": "Colocar 4 reinas en un tablero 4×4 sin que se ataquen.",
        "code": """% N-Queens 4×4: q_{fila}_{columna} = reina en esa celda
var bool: q11, q12, q13, q14;
var bool: q21, q22, q23, q24;
var bool: q31, q32, q33, q34;
var bool: q41, q42, q43, q44;

% Exactamente 1 reina por fila
constraint exactly(1, [q11, q12, q13, q14]);
constraint exactly(1, [q21, q22, q23, q24]);
constraint exactly(1, [q31, q32, q33, q34]);
constraint exactly(1, [q41, q42, q43, q44]);

% Exactamente 1 reina por columna
constraint exactly(1, [q11, q21, q31, q41]);
constraint exactly(1, [q12, q22, q32, q42]);
constraint exactly(1, [q13, q23, q33, q43]);
constraint exactly(1, [q14, q24, q34, q44]);

% Diagonales: no dos reinas en la misma diagonal
constraint atmost(1, [q11, q22, q33, q44]);
constraint atmost(1, [q12, q23, q34]);
constraint atmost(1, [q13, q24]);
constraint atmost(1, [q21, q32, q43]);
constraint atmost(1, [q31, q42]);

constraint atmost(1, [q14, q23, q32, q41]);
constraint atmost(1, [q13, q22, q31]);
constraint atmost(1, [q12, q21]);
constraint atmost(1, [q24, q33, q42]);
constraint atmost(1, [q34, q43]);

solve satisfy;
""",
    },
]


# ================================================================
# 7.  PYDANTIC SCHEMAS
# ================================================================

class ParseRequest(BaseModel):
    code: str = Field(..., description="Source code in the SAT modeling language")

class CompileRequest(BaseModel):
    code: str = Field(..., description="Source code to compile to DIMACS CNF")

class SolveRequest(BaseModel):
    code: str = Field(..., description="Source code to compile and solve")
    solver: Optional[str] = Field(None, description="Solver key (e.g. 'kissat'). If omitted, uses first ready solver.")
    timeout: int = Field(30, ge=1, le=300, description="Timeout in seconds")

class SaveModelRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)
    code: str = Field(..., min_length=1)


# ================================================================
# 8.  API ENDPOINTS
# ================================================================

@router.get("/examples")
async def list_examples() -> List[Dict]:
    """Return built-in example models."""
    return EXAMPLE_MODELS


@router.post("/parse")
async def parse_model(req: ParseRequest) -> Dict:
    """Parse source code and return syntax validation result + variable list."""
    try:
        tokens = tokenize(req.code)
        stmts = Parser(tokens).parse()
        variables = []
        constraints_count = 0
        for s in stmts:
            if isinstance(s, VarDecl):
                variables.extend(s.names)
            elif isinstance(s, Constraint):
                constraints_count += 1
        return {
            "valid": True,
            "variables": variables,
            "constraints": constraints_count,
            "tokens": len(tokens) - 1,  # exclude EOF
        }
    except SyntaxError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        return {"valid": False, "error": f"Error: {e}"}


@router.post("/compile")
async def compile_model(req: CompileRequest) -> Dict:
    """Compile source code to DIMACS CNF."""
    try:
        tokens = tokenize(req.code)
        stmts = Parser(tokens).parse()
        compiler = CNFCompiler()
        dimacs, var_map = compiler.compile(stmts)

        # Count stats
        lines = dimacs.strip().split("\n")
        header = lines[0] if lines else ""

        return {
            "success": True,
            "dimacs": dimacs,
            "variable_map": var_map,
            "num_variables": compiler._next_id - 1,
            "num_clauses": len(compiler._clauses),
            "user_variables": len(var_map),
            "header": header,
        }
    except (SyntaxError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/solve")
async def solve_model(req: SolveRequest) -> Dict:
    """Compile source to CNF, write temp file, run solver, return result."""
    # 1. Compile
    try:
        tokens = tokenize(req.code)
        stmts = Parser(tokens).parse()
        compiler = CNFCompiler()
        dimacs, var_map = compiler.compile(stmts)
    except (SyntaxError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Compilation error: {e}")

    # 2. Find solver
    ready = _find_ready_solvers()
    if not ready:
        raise HTTPException(status_code=503, detail="No solvers available")

    solver_info = None
    if req.solver:
        solver_info = next((s for s in ready if s["key"] == req.solver), None)
        if not solver_info:
            raise HTTPException(status_code=404, detail=f"Solver '{req.solver}' not found or not ready")
    else:
        solver_info = ready[0]

    # 3. Write temp CNF
    cnf_path = CNF_DIR / f"model_{uuid.uuid4().hex[:12]}.cnf"
    cnf_path.write_text(dimacs)

    try:
        # 4. Run
        raw = await _run_solver_on_cnf(solver_info["executable"], str(cnf_path), req.timeout)

        # 5. Decode assignment
        assignment = None
        if raw["result"] == "SAT" and "assignment_raw" in raw:
            assignment = _decode_assignment(raw["assignment_raw"], var_map)

        return {
            "result": raw["result"],
            "solver": solver_info["name"],
            "time_seconds": raw["time_seconds"],
            "assignment": assignment,
            "dimacs_stats": {
                "variables": compiler._next_id - 1,
                "clauses": len(compiler._clauses),
                "user_variables": len(var_map),
            },
            "solver_output": raw.get("output", "")[:3000],
        }
    finally:
        # Cleanup
        try:
            cnf_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/solvers")
async def available_solvers() -> List[Dict]:
    """Return list of ready solvers for the modeler UI."""
    return _find_ready_solvers()


@router.get("/models")
async def list_saved_models() -> List[Dict]:
    """List user-saved models."""
    models = []
    for f in sorted(MODELS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            models.append(data)
        except Exception:
            continue
    return models


@router.post("/models")
async def save_model(req: SaveModelRequest) -> Dict:
    """Save a model to disk."""
    model_id = uuid.uuid4().hex[:12]
    model = {
        "id": model_id,
        "name": req.name,
        "description": req.description,
        "code": req.code,
        "created_at": datetime.now().isoformat(),
    }
    path = MODELS_DIR / f"{model_id}.json"
    path.write_text(json.dumps(model, indent=2))
    return model


@router.delete("/models/{model_id}")
async def delete_model(model_id: str) -> Dict:
    """Delete a saved model."""
    path = MODELS_DIR / f"{model_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Model not found")
    path.unlink()
    return {"deleted": True}


@router.get("/language-reference")
async def language_reference() -> Dict:
    """Return the language reference documentation."""
    return {
        "name": "SAT Modeling Language",
        "version": "1.0",
        "sections": [
            {
                "title": "Declaración de Variables",
                "syntax": "var bool: nombre1, nombre2, ...;",
                "description": "Declara variables booleanas que representan las decisiones del problema.",
                "example": "var bool: x, y, z;"
            },
            {
                "title": "Restricciones",
                "syntax": "constraint <expresión>;",
                "description": "Agrega una restricción que debe ser verdadera.",
                "example": "constraint x \\/ y;"
            },
            {
                "title": "Operadores Lógicos",
                "items": [
                    {"op": "/\\  o  and", "desc": "Conjunción (AND)"},
                    {"op": "\\/  o  or", "desc": "Disyunción (OR)"},
                    {"op": "not, ~, !", "desc": "Negación (NOT)"},
                    {"op": "->", "desc": "Implicación"},
                    {"op": "<->", "desc": "Equivalencia (si y solo si)"},
                    {"op": "xor(a, b)", "desc": "OR exclusivo"},
                ]
            },
            {
                "title": "Restricciones de Cardinalidad",
                "items": [
                    {"op": "atmost(k, [vars])", "desc": "A lo sumo k variables son verdaderas"},
                    {"op": "atleast(k, [vars])", "desc": "Al menos k variables son verdaderas"},
                    {"op": "exactly(k, [vars])", "desc": "Exactamente k variables son verdaderas"},
                ]
            },
            {
                "title": "Comentarios",
                "syntax": "% comentario  o  // comentario",
                "description": "Líneas que comienzan con % o // son ignoradas."
            },
            {
                "title": "Resolver",
                "syntax": "solve satisfy;",
                "description": "Indica al sistema que busque una asignación satisfactoria."
            },
        ]
    }
