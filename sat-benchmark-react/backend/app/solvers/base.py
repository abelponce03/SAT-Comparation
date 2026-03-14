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
import shutil
import subprocess
import tempfile
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
    user_time_seconds: float = 0.0
    system_time_seconds: float = 0.0
    max_memory_kb: int = 0
    solver_output: str = ""
    error_message: str = ""
    # Solver statistics
    conflicts: Optional[int] = None
    decisions: Optional[int] = None
    propagations: Optional[int] = None
    restarts: Optional[int] = None
    learnt_clauses: Optional[int] = None
    deleted_clauses: Optional[int] = None
    # Resource metrics from /usr/bin/time -v
    page_faults_minor: Optional[int] = None
    page_faults_major: Optional[int] = None
    context_switches_voluntary: Optional[int] = None
    context_switches_involuntary: Optional[int] = None
    filesystem_inputs: Optional[int] = None
    filesystem_outputs: Optional[int] = None
    # All additional solver-specific metrics
    extra_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "result": self.result,
            "exit_code": self.exit_code,
            "wall_time_seconds": self.wall_time_seconds,
            "cpu_time_seconds": self.cpu_time_seconds,
            "user_time_seconds": self.user_time_seconds,
            "system_time_seconds": self.system_time_seconds,
            "max_memory_kb": self.max_memory_kb,
            "solver_output": self.solver_output,
            "error_message": self.error_message,
            "conflicts": self.conflicts,
            "decisions": self.decisions,
            "propagations": self.propagations,
            "restarts": self.restarts,
            "learnt_clauses": self.learnt_clauses,
            "deleted_clauses": self.deleted_clauses,
        }
        # Merge resource & extra stats
        if self.page_faults_minor is not None:
            d["page_faults_minor"] = self.page_faults_minor
        if self.page_faults_major is not None:
            d["page_faults_major"] = self.page_faults_major
        if self.context_switches_voluntary is not None:
            d["context_switches_voluntary"] = self.context_switches_voluntary
        if self.context_switches_involuntary is not None:
            d["context_switches_involuntary"] = self.context_switches_involuntary
        if self.filesystem_inputs is not None:
            d["filesystem_inputs"] = self.filesystem_inputs
        if self.filesystem_outputs is not None:
            d["filesystem_outputs"] = self.filesystem_outputs
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
        """Run the solver on *cnf_path* with resource tracking.

        When GNU time (``/usr/bin/time``) is available, it wraps the solver
        invocation to collect accurate user/system CPU time, peak RSS,
        page faults, and context switches — metrics essential for
        scientific benchmarking.
        """
        result = SolverRunResult()

        if not self.is_installed():
            result.result = "ERROR"
            result.error_message = f"Solver {self.name} is not installed"
            return result

        cmd = self.build_command(cnf_path)

        # ---------- /usr/bin/time wrapper ----------
        time_binary = shutil.which("time")
        # shutil.which may return bash built-in; we need GNU time
        if time_binary and "/usr/bin" not in time_binary:
            # Double-check explicit path
            if os.path.isfile("/usr/bin/time"):
                time_binary = "/usr/bin/time"
            else:
                time_binary = None
        elif not time_binary and os.path.isfile("/usr/bin/time"):
            time_binary = "/usr/bin/time"

        time_output_file = None
        if time_binary:
            time_output_file = tempfile.mktemp(suffix=".time", prefix="sat_")
            cmd = [time_binary, "-v", "-o", time_output_file] + cmd

        try:
            start = time.perf_counter()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                wall = time.perf_counter() - start

                # GNU time uses WIFSIGNALED-style codes; the solver's real
                # exit code is forwarded by /usr/bin/time.
                result.exit_code = process.returncode or 0
                result.wall_time_seconds = wall
                result.solver_output = stdout_bytes.decode("utf-8", errors="ignore")[:50_000]
                error_out = stderr_bytes.decode("utf-8", errors="ignore")[:10_000]
                if error_out:
                    result.error_message = error_out

                # Combine stdout + stderr for stat parsing (some solvers
                # print stats to stderr, e.g. MiniSat-family)
                full_output = result.solver_output + "\n" + error_out

                # Determine SAT/UNSAT from exit code & output
                result.result = self.parse_result(result.exit_code, full_output)

                # Extract solver statistics
                stats = self.parse_stats(full_output)
                result.conflicts = stats.get("conflicts")
                result.decisions = stats.get("decisions")
                result.propagations = stats.get("propagations")
                result.restarts = stats.get("restarts")
                result.learnt_clauses = stats.get("learnt_clauses")
                result.deleted_clauses = stats.get("deleted_clauses")
                result.cpu_time_seconds = stats.get("cpu_time_seconds", 0.0)
                if stats.get("max_memory_kb"):
                    result.max_memory_kb = stats["max_memory_kb"]
                # Everything else goes into extra_stats
                for k, v in stats.items():
                    if k not in ("conflicts", "decisions", "propagations",
                                 "restarts", "learnt_clauses", "deleted_clauses",
                                 "cpu_time_seconds", "max_memory_kb"):
                        result.extra_stats[k] = v

                # ---------- Parse GNU time output ----------
                if time_output_file and os.path.isfile(time_output_file):
                    resource_stats = self._parse_gnu_time(time_output_file)
                    # User/system CPU time (use GNU time values as ground truth)
                    if "user_time" in resource_stats:
                        result.user_time_seconds = resource_stats["user_time"]
                    if "system_time" in resource_stats:
                        result.system_time_seconds = resource_stats["system_time"]
                    if result.user_time_seconds or result.system_time_seconds:
                        result.cpu_time_seconds = (
                            result.user_time_seconds + result.system_time_seconds
                        )
                    # Peak memory (use GNU time if solver didn't report)
                    if resource_stats.get("max_rss_kb"):
                        result.max_memory_kb = max(
                            result.max_memory_kb,
                            resource_stats["max_rss_kb"],
                        )
                    # Resource counters
                    result.page_faults_minor = resource_stats.get("page_faults_minor")
                    result.page_faults_major = resource_stats.get("page_faults_major")
                    result.context_switches_voluntary = resource_stats.get(
                        "voluntary_context_switches"
                    )
                    result.context_switches_involuntary = resource_stats.get(
                        "involuntary_context_switches"
                    )
                    result.filesystem_inputs = resource_stats.get("fs_inputs")
                    result.filesystem_outputs = resource_stats.get("fs_outputs")

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
        finally:
            # Clean up temp file
            if time_output_file:
                try:
                    os.unlink(time_output_file)
                except OSError:
                    pass

        return result

    # ── GNU time output parser ───────────────────────

    @staticmethod
    def _parse_gnu_time(filepath: str) -> Dict[str, Any]:
        """Parse the output of ``/usr/bin/time -v`` from a file.

        Returns a dict with:
          user_time, system_time, max_rss_kb, page_faults_minor,
          page_faults_major, voluntary_context_switches,
          involuntary_context_switches, fs_inputs, fs_outputs,
          wall_clock, percent_cpu, exit_status
        """
        stats: Dict[str, Any] = {}
        try:
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if ":" not in line:
                        continue
                    key_part, _, value = line.rpartition(":")
                    value = value.strip()
                    key_lower = key_part.strip().lower()

                    if "user time" in key_lower:
                        stats["user_time"] = float(value)
                    elif "system time" in key_lower:
                        stats["system_time"] = float(value)
                    elif "maximum resident set size" in key_lower:
                        stats["max_rss_kb"] = int(value)
                    elif "minor" in key_lower and "page fault" in key_lower:
                        stats["page_faults_minor"] = int(value)
                    elif "major" in key_lower and "page fault" in key_lower:
                        stats["page_faults_major"] = int(value)
                    elif "voluntary context switch" in key_lower:
                        if "involuntary" in key_lower:
                            stats["involuntary_context_switches"] = int(value)
                        else:
                            stats["voluntary_context_switches"] = int(value)
                    elif "file system input" in key_lower:
                        stats["fs_inputs"] = int(value)
                    elif "file system output" in key_lower:
                        stats["fs_outputs"] = int(value)
                    elif "wall clock" in key_lower:
                        # Format can be h:mm:ss or m:ss.ss
                        parts = value.split(":")
                        try:
                            if len(parts) == 3:
                                stats["wall_clock"] = (
                                    int(parts[0]) * 3600
                                    + int(parts[1]) * 60
                                    + float(parts[2])
                                )
                            elif len(parts) == 2:
                                stats["wall_clock"] = (
                                    int(parts[0]) * 60 + float(parts[1])
                                )
                        except (ValueError, IndexError):
                            pass
                    elif "percent of cpu" in key_lower:
                        m = re.search(r'(\d+)', value)
                        if m:
                            stats["percent_cpu"] = int(m.group(1))
                    elif "exit status" in key_lower:
                        try:
                            stats["exit_status"] = int(value)
                        except ValueError:
                            pass
        except Exception as exc:
            logger.debug("Failed to parse GNU time output %s: %s", filepath, exc)

        return stats

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
        The default implementation covers the most common patterns
        across all CDCL solvers.
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

        # CPU time (solver-reported)
        m = re.search(r"(?:CPU|process)[- ]time[:\s]+(\d+\.?\d*)\s*(?:s|seconds)", output, re.IGNORECASE)
        if m:
            stats["cpu_time_seconds"] = float(m.group(1))

        # Memory: bytes → KB
        m = re.search(r"maximum-resident-set-size:\s+(\d+)\s*bytes", output, re.IGNORECASE)
        if m:
            stats["max_memory_kb"] = int(m.group(1)) // 1024

        # Memory: MB → KB
        if "max_memory_kb" not in stats:
            m = re.search(r"(?:Memory used|Mem used|memory)\s*[:\s]+([\d.]+)\s*MB", output, re.IGNORECASE)
            if m:
                stats["max_memory_kb"] = int(float(m.group(1)) * 1024)

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
