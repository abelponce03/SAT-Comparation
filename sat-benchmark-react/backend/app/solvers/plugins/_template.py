"""
Custom Solver Plugin Override (ADVANCED — usually NOT needed)
=============================================================

**Most solvers should be added via ``solver_definitions.yaml``** — no
Python code required.  Just add a YAML block with the solver's name,
repository URL, build commands, and metadata; restart the backend.

This .py plugin mechanism is only needed when a solver requires truly
custom logic that cannot be expressed as YAML build steps, such as:
  - Custom output parsing beyond regex
  - Dynamic library linking or runtime environment setup
  - Multi-phase build orchestration with conditional logic

How to use (advanced override):
  1. cp _template.py  my_solver.py
  2. Edit the class — the ``key`` must match the YAML entry's key
  3. Place it in ``app/solvers/plugins/`` and restart the backend
  4. The .py plugin will automatically override the YAML definition

The YAML approach (recommended — no Python):
  1. Open ``app/solvers/solver_definitions.yaml``
  2. Add a new entry under ``solvers:``
  3. Restart the backend — done!
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
