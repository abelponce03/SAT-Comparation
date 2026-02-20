"""
Base classes for the SAT Solver plugin system.

Every solver is described by a `SolverPlugin` subclass that knows:
  - metadata (name, version, features, ...)
  - how to detect whether it is installed
  - how to install / compile from source
  - how to run on a CNF file
  - how to parse its output
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────
# Data classes
# ────────────────────────────────────────────────────────

class SolverStatus(str, Enum):
    READY = "ready"
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class SolverInfo:
    """Serialisable snapshot of a solver's state — returned by the API."""
    id: int
    key: str
    name: str
    version: str
    description: str
    executable_path: str
    status: str
    features: List[str]
    website: str
    category: str  # "competition" | "educational" | "specialized"
    # Comparison-matrix extras
    solver_type: str = "CDCL"
    preprocessing: bool = False
    inprocessing: bool = False
    parallel: bool = False
    incremental: bool = False
    best_for: List[str] = field(default_factory=list)
    performance_class: str = "Unknown"


@dataclass
class SolverInstallResult:
    success: bool
    message: str
    version: Optional[str] = None
    error: Optional[str] = None
    log: str = ""


@dataclass
class SolverRunResult:
    """Result of running a solver on a single CNF file."""
    result: str = "UNKNOWN"          # SAT | UNSAT | TIMEOUT | MEMOUT | ERROR | UNKNOWN
    exit_code: int = -1
    wall_time_seconds: float = 0.0
    cpu_time_seconds: float = 0.0
    max_memory_kb: int = 0
    solver_output: str = ""
    error_message: str = ""
    # Solver statistics
    conflicts: Optional[int] = None
    decisions: Optional[int] = None
    propagations: Optional[int] = None
    restarts: Optional[int] = None
    extra_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "result": self.result,
            "exit_code": self.exit_code,
            "wall_time_seconds": self.wall_time_seconds,
            "cpu_time_seconds": self.cpu_time_seconds,
            "max_memory_kb": self.max_memory_kb,
            "solver_output": self.solver_output,
            "error_message": self.error_message,
            "conflicts": self.conflicts,
            "decisions": self.decisions,
            "propagations": self.propagations,
            "restarts": self.restarts,
        }
        # Merge extra stats (learnt_clauses, deleted_clauses, etc.)
        d.update(self.extra_stats)
        return d


# ────────────────────────────────────────────────────────
# Abstract base plugin
# ────────────────────────────────────────────────────────

class SolverPlugin(ABC):
    """
    Abstract base class for a SAT solver plugin.

    Subclass this and implement the abstract methods to add a
    new solver to the benchmark suite.  Place the file under
    ``app/solvers/plugins/`` and it will be auto-discovered.
    """

    # ── metadata (must override) ────────────────────────

    @property
    @abstractmethod
    def key(self) -> str:
        """Unique lowercase identifier, e.g. 'kissat'."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name, e.g. 'Kissat'."""
        ...

    @property
    @abstractmethod
    def default_version(self) -> str:
        """Fallback version string when detection fails."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def website(self) -> str:
        ...

    @property
    @abstractmethod
    def features(self) -> List[str]:
        ...

    @property
    def category(self) -> str:
        return "competition"

    # Comparison-matrix fields (override as needed)
    @property
    def solver_type(self) -> str:
        return "CDCL"

    @property
    def preprocessing(self) -> bool:
        return False

    @property
    def inprocessing(self) -> bool:
        return False

    @property
    def parallel(self) -> bool:
        return False

    @property
    def incremental(self) -> bool:
        return False

    @property
    def best_for(self) -> List[str]:
        return []

    @property
    def performance_class(self) -> str:
        return "Unknown"

    # ── paths ───────────────────────────────────────────

    @property
    def solvers_base(self) -> Path:
        """Root directory where solvers are stored."""
        return Path(os.getenv("SOLVERS_DIR", "/app/solvers"))

    @property
    def solver_dir(self) -> Path:
        """This solver's directory (e.g. /app/solvers/kissat)."""
        return self.solvers_base / self.key

    @property
    @abstractmethod
    def executable_path(self) -> Path:
        """Absolute path to the solver binary."""
        ...

    # ── status ──────────────────────────────────────────

    def is_installed(self) -> bool:
        """Check if the solver binary exists and is executable."""
        exe = self.executable_path
        return exe.is_file() and os.access(str(exe), os.X_OK)

    def get_status(self) -> SolverStatus:
        if self.is_installed():
            return SolverStatus.READY
        if self.solver_dir.exists():
            return SolverStatus.ERROR  # source exists but binary missing
        return SolverStatus.NOT_INSTALLED

    # ── version detection ───────────────────────────────

    _cached_version: Optional[str] = None

    @property
    def version_flags(self) -> List[str]:
        """Command-line flags to get version output."""
        return ["--version"]

    def _parse_version(self, output: str) -> Optional[str]:
        """
        Parse version from command output.  Override for solvers
        with non-standard version output.
        """
        m = re.search(r"(\d+\.\d+(?:\.\d+)?)", output)
        return m.group(1) if m else None

    def detect_version(self) -> str:
        """Detect real version of the installed binary (cached)."""
        if self._cached_version is not None:
            return self._cached_version

        if not self.is_installed():
            return self.default_version

        for flag in (self.version_flags if self.version_flags else ["--version"]):
            try:
                proc = subprocess.run(
                    [str(self.executable_path), flag],
                    capture_output=True, text=True, timeout=10,
                )
                output = (proc.stdout + proc.stderr).strip()
                if output:
                    ver = self._parse_version(output)
                    if ver:
                        self._cached_version = ver
                        return ver
            except Exception as exc:
                logger.debug("Version detection (%s %s): %s", self.key, flag, exc)

        return self.default_version

    # ── installation ────────────────────────────────────

    @abstractmethod
    async def install(self) -> SolverInstallResult:
        """
        Download / compile the solver.  Return a SolverInstallResult.
        Must be safe to call multiple times (idempotent).
        """
        ...

    async def uninstall(self) -> bool:
        """Remove the solver directory.  Override for custom cleanup."""
        import shutil
        try:
            if self.solver_dir.exists():
                shutil.rmtree(self.solver_dir)
            self._cached_version = None
            return True
        except Exception as exc:
            logger.error("Uninstall %s failed: %s", self.key, exc)
            return False

    # ── execution ───────────────────────────────────────

    def build_command(self, cnf_path: str) -> List[str]:
        """
        Build the command to run the solver on a CNF file.
        Override for solvers that need additional arguments.
        """
        return [str(self.executable_path), cnf_path]

    async def run(
        self,
        cnf_path: str,
        timeout: int = 5000,
        memory_limit_mb: int = 8192,
    ) -> SolverRunResult:
        """Run the solver on *cnf_path* and return structured results."""
        result = SolverRunResult()

        if not self.is_installed():
            result.result = "ERROR"
            result.error_message = f"Solver {self.name} is not installed"
            return result

        cmd = self.build_command(cnf_path)

        try:
            start = time.time()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                wall = time.time() - start

                result.exit_code = process.returncode or 0
                result.wall_time_seconds = wall
                result.solver_output = stdout_bytes.decode("utf-8", errors="ignore")[:10_000]
                error_out = stderr_bytes.decode("utf-8", errors="ignore")[:5_000]
                if error_out:
                    result.error_message = error_out

                # Determine SAT/UNSAT from exit code & output
                result.result = self.parse_result(result.exit_code, result.solver_output)

                # Extract solver statistics
                stats = self.parse_stats(result.solver_output)
                result.conflicts = stats.get("conflicts")
                result.decisions = stats.get("decisions")
                result.propagations = stats.get("propagations")
                result.restarts = stats.get("restarts")
                result.cpu_time_seconds = stats.get("cpu_time_seconds", 0.0)
                result.max_memory_kb = stats.get("max_memory_kb", 0)
                # Everything else goes into extra_stats
                for k, v in stats.items():
                    if k not in ("conflicts", "decisions", "propagations",
                                 "restarts", "cpu_time_seconds", "max_memory_kb"):
                        result.extra_stats[k] = v

            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass
                result.result = "TIMEOUT"
                result.wall_time_seconds = float(timeout)
                result.error_message = f"Timeout ({timeout}s) exceeded"

        except FileNotFoundError:
            result.result = "ERROR"
            result.error_message = f"Executable not found: {cmd[0]}"
        except PermissionError:
            result.result = "ERROR"
            result.error_message = f"Permission denied: {cmd[0]}"
        except Exception as exc:
            result.result = "ERROR"
            result.error_message = str(exc)

        return result

    # ── output parsing ──────────────────────────────────

    def parse_result(self, exit_code: int, output: str) -> str:
        """
        Determine SAT / UNSAT / UNKNOWN from exit code and output text.
        Standard convention: exit 10 → SAT, exit 20 → UNSAT.
        """
        upper = output.upper()
        if exit_code == 10 or "SATISFIABLE" in upper:
            if "UNSATISFIABLE" in upper:
                return "UNSAT"
            return "SAT"
        if exit_code == 20 or "UNSATISFIABLE" in upper:
            return "UNSAT"
        return "UNKNOWN"

    def parse_stats(self, output: str) -> Dict[str, Any]:
        """
        Extract solver statistics from textual output.
        Override in subclass for solver-specific parsing.
        The default implementation covers the most common patterns.
        """
        stats: Dict[str, Any] = {}
        patterns = {
            "conflicts": r"conflicts\s*[:\s]+(\d+)",
            "decisions": r"decisions\s*[:\s]+(\d+)",
            "propagations": r"propagations\s*[:\s]+(\d+)",
            "restarts": r"restarts\s*[:\s]+(\d+)",
            "learnt_clauses": r"(?:learnt|learned)\s*(?:clauses|literals)?\s*[:\s]+(\d+)",
            "deleted_clauses": r"(?:deleted|removed)\s*(?:clauses)?\s*[:\s]+(\d+)",
        }
        for key, pat in patterns.items():
            m = re.search(pat, output, re.IGNORECASE)
            if m:
                try:
                    stats[key] = int(m.group(1))
                except ValueError:
                    pass

        # CPU time
        m = re.search(r"(?:CPU|process)[- ]time[:\s]+(\d+\.?\d*)\s*(?:s|seconds)", output, re.IGNORECASE)
        if m:
            stats["cpu_time_seconds"] = float(m.group(1))

        # Memory in bytes → KB
        m = re.search(r"maximum-resident-set-size:\s+(\d+)\s*bytes", output, re.IGNORECASE)
        if m:
            stats["max_memory_kb"] = int(m.group(1)) // 1024

        return stats

    # ── serialisation ───────────────────────────────────

    def to_info(self, solver_id: int) -> SolverInfo:
        """Build a SolverInfo snapshot for the API."""
        return SolverInfo(
            id=solver_id,
            key=self.key,
            name=self.name,
            version=self.detect_version(),
            description=self.description,
            executable_path=str(self.executable_path),
            status=self.get_status().value,
            features=self.features,
            website=self.website,
            category=self.category,
            solver_type=self.solver_type,
            preprocessing=self.preprocessing,
            inprocessing=self.inprocessing,
            parallel=self.parallel,
            incremental=self.incremental,
            best_for=self.best_for,
            performance_class=self.performance_class,
        )

    # ── helpers for install scripts ─────────────────────

    @staticmethod
    async def _run_shell(
        cmd: str,
        cwd: Optional[Path] = None,
        timeout: int = 600,
    ) -> Tuple[int, str, str]:
        """
        Run a shell command asynchronously.
        Returns (return_code, stdout, stderr).
        """
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return -1, "", f"Command timed out after {timeout}s: {cmd}"

        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="ignore"),
            stderr.decode("utf-8", errors="ignore"),
        )

    @staticmethod
    def _check_system_deps(packages: List[str]) -> Tuple[bool, List[str]]:
        """
        Check which system packages/commands are available.
        Returns (all_found, list_of_missing).
        """
        missing = []
        for pkg in packages:
            if subprocess.run(
                ["which", pkg], capture_output=True
            ).returncode != 0:
                missing.append(pkg)
        return len(missing) == 0, missing
