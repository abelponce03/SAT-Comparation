"""
CryptoMiniSat SAT Solver Plugin
================================
CryptoMiniSat — Advanced SAT solver with XOR reasoning by Mate Soos.
Excels on cryptographic and structured instances with Gaussian elimination.

Repository: https://github.com/msoos/cryptominisat
Build: cmake + make
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ..base import SolverPlugin, SolverInstallResult


class CryptominisatPlugin(SolverPlugin):

    # ── metadata ────────────────────────────────────────

    @property
    def key(self) -> str:
        return "cryptominisat"

    @property
    def name(self) -> str:
        return "CryptoMiniSat"

    @property
    def default_version(self) -> str:
        return "5.11.21"

    @property
    def description(self) -> str:
        return (
            "CryptoMiniSat — Advanced SAT solver with XOR reasoning by Mate Soos. "
            "Excels on cryptographic and structured instances with Gaussian elimination. "
            "Supports parallel solving and SQL logging for analysis."
        )

    @property
    def website(self) -> str:
        return "https://github.com/msoos/cryptominisat"

    @property
    def features(self) -> List[str]:
        return [
            "CDCL", "XOR reasoning", "Gaussian elimination",
            "Component caching", "SQL logging",
            "Bounded variable elimination", "Probing",
        ]

    @property
    def category(self) -> str:
        return "competition"

    # Comparison matrix
    @property
    def solver_type(self) -> str:
        return "CDCL + XOR"

    @property
    def preprocessing(self) -> bool:
        return True

    @property
    def inprocessing(self) -> bool:
        return True

    @property
    def parallel(self) -> bool:
        return True

    @property
    def incremental(self) -> bool:
        return True

    @property
    def best_for(self) -> List[str]:
        return ["Cryptographic", "XOR-heavy", "Structured"]

    @property
    def performance_class(self) -> str:
        return "Specialized"

    # ── paths ───────────────────────────────────────────

    @property
    def executable_path(self) -> Path:
        return self.solver_dir / "build" / "cryptominisat5"

    # ── installation ────────────────────────────────────

    async def install(self) -> SolverInstallResult:
        log_lines: list[str] = []

        # CryptoMiniSat needs cmake
        ok, missing = self._check_system_deps(["git", "cmake", "make", "g++"])
        if not ok:
            return SolverInstallResult(
                success=False,
                message=f"Missing system dependencies: {', '.join(missing)}",
                error=f"Install: {', '.join(missing)}. On Debian/Ubuntu: "
                      "sudo apt-get install build-essential cmake git zlib1g-dev",
            )

        if not self.solver_dir.exists():
            rc, out, err = await self._run_shell(
                f"git clone https://github.com/msoos/cryptominisat.git {self.solver_dir}",
                timeout=120,
            )
            log_lines.append(f"[clone] rc={rc}\n{out}\n{err}")
            if rc != 0:
                return SolverInstallResult(
                    success=False, message="git clone failed",
                    error=err, log="\n".join(log_lines),
                )

        # Checkout a known-good release that does NOT require cadiback / cadical
        rc, out, err = await self._run_shell(
            "git checkout 5.11.21",
            cwd=self.solver_dir, timeout=30,
        )
        log_lines.append(f"[checkout] rc={rc}\n{out}\n{err}")

        # Init submodules (CMS uses some)
        rc, out, err = await self._run_shell(
            "git submodule update --init",
            cwd=self.solver_dir, timeout=60,
        )
        log_lines.append(f"[submodule] rc={rc}\n{out}\n{err}")

        # Create build directory
        build_dir = self.solver_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)

        # CMake configure
        rc, out, err = await self._run_shell(
            "cmake -DCMAKE_BUILD_TYPE=Release ..",
            cwd=build_dir, timeout=120,
        )
        log_lines.append(f"[cmake] rc={rc}\n{out}\n{err}")
        if rc != 0:
            # Try without optional deps
            rc, out, err = await self._run_shell(
                "cmake -DCMAKE_BUILD_TYPE=Release "
                "-DNOM4RI=ON -DSTATS=OFF -DENABLE_TESTING=OFF ..",
                cwd=build_dir, timeout=120,
            )
            log_lines.append(f"[cmake fallback] rc={rc}\n{out}\n{err}")
            if rc != 0:
                return SolverInstallResult(
                    success=False, message="cmake configure failed",
                    error=err, log="\n".join(log_lines),
                )

        # Build
        rc, out, err = await self._run_shell(
            "make -j$(nproc)", cwd=build_dir, timeout=600,
        )
        log_lines.append(f"[make] rc={rc}\n{out}\n{err}")
        if rc != 0:
            return SolverInstallResult(
                success=False, message="Compilation failed",
                error=err, log="\n".join(log_lines),
            )

        if not self.is_installed():
            # Binary might be at a different location
            import glob
            candidates = glob.glob(str(self.solver_dir / "build" / "**" / "cryptominisat5*"), recursive=True)
            if candidates:
                return SolverInstallResult(
                    success=False,
                    message=f"Binary found at non-standard path: {candidates[0]}",
                    error=f"Expected at {self.executable_path}",
                    log="\n".join(log_lines),
                )
            return SolverInstallResult(
                success=False,
                message="Build completed but binary not found",
                error=f"Expected at {self.executable_path}",
                log="\n".join(log_lines),
            )

        ver = self.detect_version()
        return SolverInstallResult(
            success=True,
            message=f"CryptoMiniSat {ver} installed successfully",
            version=ver,
            log="\n".join(log_lines),
        )

    # ── output parsing (CryptoMiniSat-specific) ─────────

    def parse_stats(self, output: str) -> Dict[str, Any]:
        stats = super().parse_stats(output)

        extra_patterns = {
            "xor_clauses": r"xor\s*clauses\s*[:\s]+(\d+)",
            "gauss_called": r"gauss.*called\s*[:\s]+(\d+)",
            "gauss_useful": r"gauss.*useful\s*[:\s]+(\d+)",
            "binary_clauses": r"binary\s*clauses\s*[:\s]+(\d+)",
            "tri_clauses": r"(?:tri|ternary)\s*clauses\s*[:\s]+(\d+)",
            "long_clauses": r"long\s*clauses\s*[:\s]+(\d+)",
        }
        for key, pat in extra_patterns.items():
            m = re.search(pat, output, re.IGNORECASE)
            if m:
                try:
                    stats[key] = int(m.group(1))
                except ValueError:
                    pass

        return stats


plugin = CryptominisatPlugin()
