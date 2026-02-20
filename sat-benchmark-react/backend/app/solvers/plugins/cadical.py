"""
CaDiCaL SAT Solver Plugin
==========================
CaDiCaL — Conflict-Driven Clause Learning SAT Solver by Armin Biere.
Advanced CDCL with chronological backtracking and extensive inprocessing.

Repository: https://github.com/arminbiere/cadical
Build: ./configure && make
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ..base import SolverPlugin, SolverInstallResult


class CadicalPlugin(SolverPlugin):

    # ── metadata ────────────────────────────────────────

    @property
    def key(self) -> str:
        return "cadical"

    @property
    def name(self) -> str:
        return "CaDiCaL"

    @property
    def default_version(self) -> str:
        return "2.1.3"

    @property
    def description(self) -> str:
        return (
            "CaDiCaL — Conflict-Driven Clause Learning SAT Solver by Armin Biere. "
            "Advanced CDCL with chronological backtracking and extensive inprocessing. "
            "Multiple SAT Competition wins. Also the backbone of the CaDiCaL-based portfolio."
        )

    @property
    def website(self) -> str:
        return "https://github.com/arminbiere/cadical"

    @property
    def features(self) -> List[str]:
        return [
            "CDCL", "Chronological backtracking", "Inprocessing",
            "Vivification", "Lucky phases",
            "Bounded variable elimination", "Probing",
        ]

    @property
    def category(self) -> str:
        return "competition"

    # Comparison matrix
    @property
    def preprocessing(self) -> bool:
        return True

    @property
    def inprocessing(self) -> bool:
        return True

    @property
    def incremental(self) -> bool:
        return True

    @property
    def best_for(self) -> List[str]:
        return ["Industrial", "Verification", "Competition"]

    @property
    def performance_class(self) -> str:
        return "State-of-the-art"

    # ── paths ───────────────────────────────────────────

    @property
    def executable_path(self) -> Path:
        return self.solver_dir / "build" / "cadical"

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
                f"git clone https://github.com/arminbiere/cadical.git {self.solver_dir}",
                timeout=120,
            )
            log_lines.append(f"[clone] rc={rc}\n{out}\n{err}")
            if rc != 0:
                return SolverInstallResult(
                    success=False, message="git clone failed",
                    error=err, log="\n".join(log_lines),
                )

        # Configure
        rc, out, err = await self._run_shell(
            "./configure", cwd=self.solver_dir, timeout=60,
        )
        log_lines.append(f"[configure] rc={rc}\n{out}\n{err}")
        if rc != 0:
            return SolverInstallResult(
                success=False, message="configure failed",
                error=err, log="\n".join(log_lines),
            )

        # Build
        rc, out, err = await self._run_shell(
            "make -j$(nproc)", cwd=self.solver_dir, timeout=300,
        )
        log_lines.append(f"[make] rc={rc}\n{out}\n{err}")
        if rc != 0:
            return SolverInstallResult(
                success=False, message="Compilation failed",
                error=err, log="\n".join(log_lines),
            )

        if not self.is_installed():
            return SolverInstallResult(
                success=False,
                message="Build completed but binary not found",
                error=f"Expected at {self.executable_path}",
                log="\n".join(log_lines),
            )

        ver = self.detect_version()
        return SolverInstallResult(
            success=True,
            message=f"CaDiCaL {ver} installed successfully",
            version=ver,
            log="\n".join(log_lines),
        )

    # ── output parsing (CaDiCaL-specific) ───────────────

    def parse_stats(self, output: str) -> Dict[str, Any]:
        stats = super().parse_stats(output)

        extra_patterns = {
            "chronological": r"chronological:\s+(\d+)",
            "vivified": r"vivified:\s+(\d+)",
            "reductions": r"reductions:\s+(\d+)",
            "stabilized": r"stabilized:\s+(\d+)",
            "subsumed": r"subsumed:\s+(\d+)",
            "strengthened": r"strengthened:\s+(\d+)",
            "deduplicated": r"deduplicated:\s+(\d+)",
        }
        for key, pat in extra_patterns.items():
            m = re.search(pat, output, re.IGNORECASE)
            if m:
                try:
                    stats[key] = int(m.group(1))
                except ValueError:
                    pass

        return stats


plugin = CadicalPlugin()
