"""
Generic SAT Solver Plugin — instantiated from YAML definitions.

This module provides a single class that can represent ANY SAT solver
based on a declarative configuration dict (loaded from solver_definitions.yaml).
No per-solver Python code is necessary.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import SolverPlugin, SolverInstallResult

logger = logging.getLogger(__name__)


class GenericSolverPlugin(SolverPlugin):
    """
    A solver plugin driven entirely by a configuration dictionary.

    This replaces the need for individual .py files per solver.
    The config dict comes from ``solver_definitions.yaml`` and contains
    all metadata, build instructions, and parsing patterns.
    """

    def __init__(self, solver_key: str, config: Dict[str, Any]) -> None:
        self._key = solver_key
        self._config = config
        self._build = config.get("build", {})

    # ── metadata ────────────────────────────────────────

    @property
    def key(self) -> str:
        return self._key

    @property
    def name(self) -> str:
        return self._config["name"]

    @property
    def default_version(self) -> str:
        return str(self._config.get("version", "unknown"))

    @property
    def description(self) -> str:
        return self._config.get("description", "")

    @property
    def website(self) -> str:
        return self._config.get("website", "")

    @property
    def features(self) -> List[str]:
        return self._config.get("features", [])

    @property
    def category(self) -> str:
        return self._config.get("category", "competition")

    @property
    def solver_type(self) -> str:
        return self._config.get("solver_type", "CDCL")

    @property
    def preprocessing(self) -> bool:
        return bool(self._config.get("preprocessing", False))

    @property
    def inprocessing(self) -> bool:
        return bool(self._config.get("inprocessing", False))

    @property
    def parallel(self) -> bool:
        return bool(self._config.get("parallel", False))

    @property
    def incremental(self) -> bool:
        return bool(self._config.get("incremental", False))

    @property
    def best_for(self) -> List[str]:
        return self._config.get("best_for", [])

    @property
    def performance_class(self) -> str:
        return self._config.get("performance_class", "Unknown")

    # ── paths & detection ────────────────────────────────

    @property
    def executable_path(self) -> Path:
        """Find the solver executable.

        Search order:
          1. Compiled binary in solver_dir (from build instructions)
          2. System PATH (apt install, manual install, etc.)
          3. Fallback to first candidate path (even if missing)
        """
        # 1. Check compiled binaries in solver_dir
        candidates = self._build.get("executable_candidates", [])
        for candidate in candidates:
            p = self.solver_dir / candidate
            if p.is_file():
                return p

        # 2. Check system PATH
        sys_path = self._find_system_binary()
        if sys_path:
            return sys_path

        # 3. Fallback: return expected path (for install / status display)
        if candidates:
            return self.solver_dir / candidates[0]
        return self.solver_dir / self._key

    def _find_system_binary(self) -> Optional[Path]:
        """Search system PATH for any known binary name of this solver."""
        names = self._config.get("system_binary_names", [])
        for name in names:
            found = shutil.which(name)
            if found:
                return Path(found)
        return None

    def is_installed(self) -> bool:
        """Check if the solver is available (compiled OR system-installed)."""
        # Check compiled binary in solver_dir first
        candidates = self._build.get("executable_candidates", [])
        for candidate in candidates:
            p = self.solver_dir / candidate
            if p.is_file() and os.access(str(p), os.X_OK):
                return True
        # Check system PATH
        return self._find_system_binary() is not None

    @property
    def has_build_config(self) -> bool:
        """Whether this solver has build instructions (installable vs catalog-only)."""
        return bool(self._build and self._build.get("repository"))

    # ── execution ───────────────────────────────────────

    def build_command(self, cnf_path: str) -> List[str]:
        """Build command with run_flags for maximum statistics output."""
        run_flags = self._config.get("run_flags", [])
        return [str(self.executable_path)] + run_flags + [cnf_path]

    # ── version detection ───────────────────────────────

    @property
    def version_flags(self) -> List[str]:
        return self._config.get("version_flags", ["--version"])

    def _parse_version(self, output: str) -> Optional[str]:
        """Use custom version_pattern from YAML if provided, else default."""
        pattern = self._config.get("version_pattern")
        if pattern:
            m = re.search(pattern, output, re.IGNORECASE)
            return m.group(1) if m else None
        return super()._parse_version(output)

    # ── installation ────────────────────────────────────

    async def install(self) -> SolverInstallResult:
        """Clone and build using the YAML-defined steps."""
        if not self.has_build_config:
            return SolverInstallResult(
                success=False,
                message=(
                    f"No hay instrucciones de build para '{self._key}'. "
                    "Agrega una sección 'build:' en solver_definitions.yaml "
                    "con repository, deps, steps y executable_candidates."
                ),
            )

        log_lines: List[str] = []

        def log(msg: str) -> None:
            logger.info("[%s] %s", self._key, msg)
            log_lines.append(msg)

        # 1. Check system deps
        deps = self._build.get("deps", [])
        if deps:
            all_found, missing = self._check_system_deps(deps)
            if not all_found:
                return SolverInstallResult(
                    success=False,
                    message=f"Dependencias faltantes: {', '.join(missing)}",
                    error=f"Missing system deps: {missing}",
                    log="\n".join(log_lines),
                )
            log(f"Dependencies OK: {deps}")

        # 2. Clone the repository if solver dir doesn't exist
        if not self.solver_dir.exists():
            repos = self._build.get("repository", "")
            if isinstance(repos, str):
                repos = [repos]

            cloned = False
            for repo_url in repos:
                clone_cmd = f"git clone {repo_url} {self.solver_dir}"
                log(f"Cloning: {clone_cmd}")
                rc, stdout, stderr = await self._run_shell(clone_cmd, timeout=300)
                if rc == 0:
                    log("Clone successful")
                    cloned = True
                    break
                else:
                    log(f"Clone failed (rc={rc}): {stderr[:200]}")

            if not cloned:
                return SolverInstallResult(
                    success=False,
                    message=f"No se pudo clonar el repositorio de {self.name}",
                    error="git clone failed for all URLs",
                    log="\n".join(log_lines),
                )

        # 3. Checkout specific tag if requested
        tag = self._build.get("checkout_tag")
        if tag:
            log(f"Checking out tag: {tag}")
            rc, _, stderr = await self._run_shell(
                f"git checkout {tag}", cwd=self.solver_dir, timeout=30
            )
            if rc != 0:
                log(f"Warning: checkout {tag} failed: {stderr[:200]}")

        # 4. Run post-clone commands (e.g. submodule init)
        for cmd in self._build.get("post_clone", []):
            log(f"Post-clone: {cmd}")
            rc, _, stderr = await self._run_shell(
                cmd, cwd=self.solver_dir, timeout=120
            )
            if rc != 0:
                log(f"Warning: post-clone command failed: {stderr[:200]}")

        # 5. Run build steps
        steps = self._build.get("steps", [])
        build_ok = True
        for step in steps:
            log(f"Build step: {step}")
            rc, stdout, stderr = await self._run_shell(
                step, cwd=self.solver_dir, timeout=600
            )
            if rc != 0:
                log(f"Step failed (rc={rc}): {stderr[:300]}")
                build_ok = False
                break
            else:
                log("Step OK")

        # 6. If primary steps failed, try fallback steps
        if not build_ok:
            fallback = self._build.get("fallback_steps", [])
            if fallback:
                log("Primary build failed — trying fallback steps")
                build_ok = True
                for step in fallback:
                    log(f"Fallback step: {step}")
                    rc, stdout, stderr = await self._run_shell(
                        step, cwd=self.solver_dir, timeout=600
                    )
                    if rc != 0:
                        log(f"Fallback step failed (rc={rc}): {stderr[:300]}")
                        # Don't stop on fallback failures — some use || true
                    else:
                        log("Step OK")

        # 7. Check if the executable exists now
        if self.is_installed():
            version = self.detect_version()
            log(f"Installation successful! Version: {version}")
            return SolverInstallResult(
                success=True,
                message=f"{self.name} v{version} instalado correctamente",
                version=version,
                log="\n".join(log_lines),
            )

        # Last resort: try to find any executable in the solver dir
        log("Primary executable not found. Searching for alternatives...")
        for candidate in self._build.get("executable_candidates", []):
            p = self.solver_dir / candidate
            if p.is_file():
                if not os.access(str(p), os.X_OK):
                    os.chmod(str(p), 0o755)
                    log(f"Made executable: {p}")
                if p.is_file() and os.access(str(p), os.X_OK):
                    version = self.detect_version()
                    log(f"Found executable at: {p}")
                    return SolverInstallResult(
                        success=True,
                        message=f"{self.name} v{version} instalado correctamente",
                        version=version,
                        log="\n".join(log_lines),
                    )

        return SolverInstallResult(
            success=False,
            message=f"Build completado pero no se encontró el ejecutable de {self.name}",
            error="Executable not found after build",
            log="\n".join(log_lines),
        )

    # ── output parsing ──────────────────────────────────

    def parse_stats(self, output: str) -> Dict[str, Any]:
        """Base class parsing + extra_stats patterns from YAML."""
        stats = super().parse_stats(output)

        extra = self._config.get("extra_stats", {})
        for stat_key, pattern in extra.items():
            m = re.search(pattern, output, re.IGNORECASE)
            if m:
                raw = m.group(1)
                try:
                    # Try int first, then float
                    if "." in raw:
                        stats[stat_key] = float(raw)
                    else:
                        stats[stat_key] = int(raw)
                except ValueError:
                    stats[stat_key] = raw

        return stats

    def __repr__(self) -> str:
        return f"<GenericSolverPlugin key={self._key} name={self.name}>"
