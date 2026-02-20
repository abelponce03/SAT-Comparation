"""
MiniSat SAT Solver Plugin
==========================
MiniSat — The reference CDCL implementation.

Repository: https://github.com/niklasso/minisat
Build: make -C core (or make -C simp for the simplifier version)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import SolverPlugin, SolverInstallResult


class MinisatPlugin(SolverPlugin):

    # ── metadata ────────────────────────────────────────

    @property
    def key(self) -> str:
        return "minisat"

    @property
    def name(self) -> str:
        return "MiniSat"

    @property
    def default_version(self) -> str:
        return "2.2.0"

    @property
    def description(self) -> str:
        return (
            "MiniSat — Minimalistic, open-source SAT solver. The reference "
            "implementation for the CDCL algorithm with two-watched literals. "
            "Widely used in academia and as a base for many derived solvers."
        )

    @property
    def website(self) -> str:
        return "http://minisat.se/"

    @property
    def features(self) -> List[str]:
        return [
            "CDCL", "Conflict clause learning",
            "Variable activity (VSIDS)", "Two-watched literals",
            "Phase saving",
        ]

    @property
    def category(self) -> str:
        return "educational"

    # Comparison matrix
    @property
    def incremental(self) -> bool:
        return True

    @property
    def best_for(self) -> List[str]:
        return ["Educational", "Research", "Small instances"]

    @property
    def performance_class(self) -> str:
        return "Reference implementation"

    # ── paths ───────────────────────────────────────────

    @property
    def executable_path(self) -> Path:
        # Prefer the core build; fall back to simp
        core = self.solver_dir / "core" / "minisat"
        if core.is_file():
            return core
        simp = self.solver_dir / "simp" / "minisat"
        if simp.is_file():
            return simp
        # Default expected path
        return self.solver_dir / "core" / "minisat"

    # ── version ─────────────────────────────────────────

    @property
    def version_flags(self) -> List[str]:
        return ["--help"]

    def _parse_version(self, output: str) -> Optional[str]:
        m = re.search(r"MiniSat\s+([\d.]+)", output, re.IGNORECASE)
        if m:
            return m.group(1)
        return super()._parse_version(output)

    # ── execution (MiniSat needs an output file arg) ────

    def build_command(self, cnf_path: str) -> List[str]:
        # MiniSat accepts: minisat <input.cnf> [<output>]
        # Without output file it still works and prints result to stdout
        return [str(self.executable_path), cnf_path]

    # ── installation ────────────────────────────────────

    async def install(self) -> SolverInstallResult:
        log_lines: list[str] = []

        ok, missing = self._check_system_deps(["git", "make", "g++"])
        if not ok:
            return SolverInstallResult(
                success=False,
                message=f"Missing system dependencies: {', '.join(missing)}",
                error="Install build-essential, git, g++, make",
            )

        if not self.solver_dir.exists():
            rc, out, err = await self._run_shell(
                f"git clone https://github.com/niklasso/minisat.git {self.solver_dir}",
                timeout=120,
            )
            log_lines.append(f"[clone] rc={rc}\n{out}\n{err}")
            if rc != 0:
                return SolverInstallResult(
                    success=False, message="git clone failed",
                    error=err, log="\n".join(log_lines),
                )

        # MiniSat needs a small patch for modern compilers
        # (missing <climits> or <cstdlib> include)
        rc, out, err = await self._run_shell(
            "make -C core rs",
            cwd=self.solver_dir, timeout=120,
        )
        log_lines.append(f"[make core] rc={rc}\n{out}\n{err}")

        # If the release build failed, try debug build
        if rc != 0:
            rc, out, err = await self._run_shell(
                "make -C core",
                cwd=self.solver_dir, timeout=120,
            )
            log_lines.append(f"[make core fallback] rc={rc}\n{out}\n{err}")

        if not self.is_installed():
            # Try simp version
            rc2, out2, err2 = await self._run_shell(
                "make -C simp rs",
                cwd=self.solver_dir, timeout=120,
            )
            log_lines.append(f"[make simp] rc={rc2}\n{out2}\n{err2}")

        if not self.is_installed():
            return SolverInstallResult(
                success=False,
                message="Compilation failed — try installing zlib1g-dev",
                error=(err or err2 if 'err2' in dir() else err),
                log="\n".join(log_lines),
            )

        ver = self.detect_version()
        return SolverInstallResult(
            success=True,
            message=f"MiniSat {ver} installed successfully",
            version=ver,
            log="\n".join(log_lines),
        )

    # ── output parsing (MiniSat-specific) ───────────────

    def parse_stats(self, output: str) -> Dict[str, Any]:
        stats = super().parse_stats(output)

        # MiniSat-specific
        m = re.search(r"conflict\s*literals\s*[:\s]+(\d+)", output, re.IGNORECASE)
        if m:
            stats["conflict_literals"] = int(m.group(1))

        m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*deleted", output, re.IGNORECASE)
        if m:
            stats["literals_deleted_pct"] = float(m.group(1))

        return stats


plugin = MinisatPlugin()
