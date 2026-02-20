"""
Kissat SAT Solver Plugin
========================
Kissat — Powerful CDCL solver by Armin Biere.
Multiple SAT Competition wins (2020, 2021, 2022).

Repository: https://github.com/arminbiere/kissat
Build: ./configure && make
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ..base import SolverPlugin, SolverInstallResult


class KissatPlugin(SolverPlugin):

    # ── metadata ────────────────────────────────────────

    @property
    def key(self) -> str:
        return "kissat"

    @property
    def name(self) -> str:
        return "Kissat"

    @property
    def default_version(self) -> str:
        return "4.0.4"

    @property
    def description(self) -> str:
        return (
            "Kissat SAT Solver — Powerful CDCL solver that won multiple SAT "
            "competitions (2020, 2021, 2022). Known for excellent performance "
            "on industrial and crafted instances."
        )

    @property
    def website(self) -> str:
        return "https://github.com/arminbiere/kissat"

    @property
    def features(self) -> List[str]:
        return [
            "CDCL", "Preprocessing", "Inprocessing",
            "Learned clause minimization", "Vivification",
            "Lucky phases", "Bounded variable elimination",
        ]

    @property
    def category(self) -> str:
        return "competition"

    # Comparison matrix
    @property
    def solver_type(self) -> str:
        return "CDCL"

    @property
    def preprocessing(self) -> bool:
        return True

    @property
    def inprocessing(self) -> bool:
        return True

    @property
    def best_for(self) -> List[str]:
        return ["Industrial", "Crafted", "Competition"]

    @property
    def performance_class(self) -> str:
        return "State-of-the-art"

    # ── paths ───────────────────────────────────────────

    @property
    def executable_path(self) -> Path:
        return self.solver_dir / "build" / "kissat"

    # ── version ─────────────────────────────────────────

    @property
    def version_flags(self) -> List[str]:
        return ["--version"]

    # ── installation ────────────────────────────────────

    async def install(self) -> SolverInstallResult:
        log_lines: list[str] = []

        # Check dependencies
        ok, missing = self._check_system_deps(["git", "make", "gcc"])
        if not ok:
            return SolverInstallResult(
                success=False,
                message=f"Missing system dependencies: {', '.join(missing)}",
                error="Install build-essential, git, gcc, make",
            )

        # Clone if not present
        if not self.solver_dir.exists():
            rc, out, err = await self._run_shell(
                f"git clone https://github.com/arminbiere/kissat.git {self.solver_dir}",
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
            message=f"Kissat {ver} installed successfully",
            version=ver,
            log="\n".join(log_lines),
        )

    # ── output parsing (Kissat-specific) ────────────────

    def parse_stats(self, output: str) -> Dict[str, Any]:
        stats = super().parse_stats(output)

        # Kissat-specific extra metrics
        extra_patterns = {
            "chronological": r"chronological:\s+(\d+)",
            "vivified": r"vivified:\s+(\d+)",
            "substituted": r"substituted:\s+(\d+)",
            "congruent": r"congruent:\s+(\d+)",
            "factored": r"factored:\s+(\d+)",
            "iterations": r"iterations:\s+(\d+)",
            "switched": r"switched:\s+(\d+)",
            "walks": r"walks:\s+(\d+)",
            "reductions": r"reductions:\s+(\d+)",
            "rephased": r"rephased:\s+(\d+)",
        }
        for key, pat in extra_patterns.items():
            m = re.search(pat, output, re.IGNORECASE)
            if m:
                try:
                    stats[key] = int(m.group(1))
                except ValueError:
                    pass

        return stats


# Module-level instance for auto-discovery
plugin = KissatPlugin()
