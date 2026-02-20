"""
Template for adding a new SAT Solver Plugin
============================================

Copy this file, rename it to ``your_solver.py``, and fill in the
properties and methods.  Place it in ``app/solvers/plugins/`` and
it will be auto-discovered on startup.

Steps:
  1. cp _template.py  my_solver.py
  2. Edit all properties marked with TODO
  3. Implement the install() method
  4. Optionally override parse_stats() for solver-specific metrics
  5. Restart the backend — the solver appears automatically

No other files need to be changed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..base import SolverPlugin, SolverInstallResult


class MySolverPlugin(SolverPlugin):  # TODO: rename class

    # ── TODO: fill in metadata ──────────────────────────

    @property
    def key(self) -> str:
        return "my_solver"  # unique lowercase key (no spaces)

    @property
    def name(self) -> str:
        return "My Solver"  # human-readable name

    @property
    def default_version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Short description of the solver."

    @property
    def website(self) -> str:
        return "https://github.com/author/my_solver"

    @property
    def features(self) -> List[str]:
        return ["CDCL", "Feature1", "Feature2"]

    @property
    def category(self) -> str:
        # "competition" | "educational" | "specialized"
        return "competition"

    # ── Comparison matrix (override as needed) ──────────
    # @property
    # def solver_type(self) -> str: return "CDCL"
    # @property
    # def preprocessing(self) -> bool: return False
    # @property
    # def inprocessing(self) -> bool: return False
    # @property
    # def parallel(self) -> bool: return False
    # @property
    # def incremental(self) -> bool: return False
    # @property
    # def best_for(self) -> List[str]: return ["Category"]
    # @property
    # def performance_class(self) -> str: return "Unknown"

    # ── TODO: path to the binary ────────────────────────

    @property
    def executable_path(self) -> Path:
        return self.solver_dir / "build" / "my_solver"

    # ── TODO: implement installation ────────────────────

    async def install(self) -> SolverInstallResult:
        log_lines: list[str] = []

        # Example: clone + build
        if not self.solver_dir.exists():
            rc, out, err = await self._run_shell(
                f"git clone https://github.com/author/my_solver.git {self.solver_dir}",
                timeout=120,
            )
            log_lines.append(f"[clone] rc={rc}")
            if rc != 0:
                return SolverInstallResult(
                    success=False, message="Clone failed",
                    error=err, log="\n".join(log_lines),
                )

        rc, out, err = await self._run_shell(
            "./configure && make -j$(nproc)",
            cwd=self.solver_dir, timeout=300,
        )
        log_lines.append(f"[build] rc={rc}")
        if rc != 0:
            return SolverInstallResult(
                success=False, message="Build failed",
                error=err, log="\n".join(log_lines),
            )

        if not self.is_installed():
            return SolverInstallResult(
                success=False,
                message="Binary not found after build",
                error=f"Expected at {self.executable_path}",
                log="\n".join(log_lines),
            )

        ver = self.detect_version()
        return SolverInstallResult(
            success=True,
            message=f"My Solver {ver} installed",
            version=ver, log="\n".join(log_lines),
        )

    # ── (Optional) solver-specific output parsing ───────

    # def parse_stats(self, output: str) -> Dict[str, Any]:
    #     stats = super().parse_stats(output)
    #     # Add custom parsing here ...
    #     return stats


# IMPORTANT: expose an instance for auto-discovery
# plugin = MySolverPlugin()
