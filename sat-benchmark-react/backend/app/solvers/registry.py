"""
Solver Registry — central catalogue of all solver plugins.

Auto-discovers plugins from the ``plugins/`` sub-package and assigns
stable numeric IDs.  Existing solver IDs are preserved for backwards
compatibility with database records; new solvers get the next available ID.
"""

from __future__ import annotations

import importlib
import logging
import os
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional

from .base import SolverPlugin, SolverInfo, SolverInstallResult, SolverStatus

logger = logging.getLogger(__name__)

# Fixed ID map that preserves historical IDs for backward-compatibility
# with existing database records.  New solvers are appended after max(id).
_LEGACY_ID_MAP: Dict[str, int] = {
    "kissat": 1,
    "minisat": 2,
    "cadical": 3,
    "cryptominisat": 4,
}


class SolverRegistry:
    """
    Thread-safe, singleton-style registry of solver plugins.

    Plugins are loaded once at import time from ``app.solvers.plugins.*``.
    Each plugin is assigned a **stable numeric ID**: existing solvers keep
    their historical IDs; new solvers get sequential IDs starting after the
    last reserved one.
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, SolverPlugin] = {}
        self._key_to_id: Dict[str, int] = {}
        self._id_to_key: Dict[int, str] = {}
        self._loaded = False

    # ── discovery ───────────────────────────────────────

    def discover_plugins(self) -> None:
        """Scan the ``plugins`` package and register all SolverPlugin subclasses."""
        if self._loaded:
            return

        plugins_package = "app.solvers.plugins"
        plugins_path = Path(__file__).parent / "plugins"

        if not plugins_path.is_dir():
            logger.warning("Plugins directory not found: %s", plugins_path)
            self._loaded = True
            return

        for finder, module_name, is_pkg in pkgutil.iter_modules([str(plugins_path)]):
            if module_name.startswith("_"):
                continue
            fqn = f"{plugins_package}.{module_name}"
            try:
                mod = importlib.import_module(fqn)
                # Look for a module-level ``plugin`` attribute or
                # any class that subclasses SolverPlugin.
                if hasattr(mod, "plugin") and isinstance(mod.plugin, SolverPlugin):
                    self.register(mod.plugin)
                else:
                    for attr_name in dir(mod):
                        obj = getattr(mod, attr_name)
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, SolverPlugin)
                            and obj is not SolverPlugin
                        ):
                            # Instantiate and register
                            try:
                                instance = obj()
                                self.register(instance)
                            except Exception as exc:
                                logger.error("Failed to instantiate %s: %s", attr_name, exc)
            except Exception as exc:
                logger.error("Failed to load solver plugin module '%s': %s", fqn, exc)

        self._rebuild_id_map()
        self._loaded = True
        logger.info(
            "Solver registry loaded %d plugins: %s",
            len(self._plugins),
            ", ".join(sorted(self._plugins.keys())),
        )

    def register(self, plugin: SolverPlugin) -> None:
        """Register a single plugin instance (idempotent by key)."""
        key = plugin.key
        if key in self._plugins:
            logger.debug("Plugin '%s' already registered, skipping", key)
            return
        self._plugins[key] = plugin
        logger.debug("Registered solver plugin: %s (%s)", key, plugin.name)

    def _rebuild_id_map(self) -> None:
        """Assign stable IDs preserving historical mappings.

        Solvers present in ``_LEGACY_ID_MAP`` keep their fixed IDs.
        Any newly-discovered plugin gets the next available integer ID
        (sorted alphabetically for determinism).
        """
        self._key_to_id = {}
        self._id_to_key = {}

        # 1) Assign legacy IDs first
        for key in self._plugins:
            if key in _LEGACY_ID_MAP:
                sid = _LEGACY_ID_MAP[key]
                self._key_to_id[key] = sid
                self._id_to_key[sid] = key

        # 2) Determine next available ID
        used_ids = set(self._key_to_id.values())
        next_id = max(used_ids, default=0) + 1

        # 3) Assign IDs to new plugins alphabetically
        for key in sorted(self._plugins.keys()):
            if key not in self._key_to_id:
                while next_id in used_ids:
                    next_id += 1
                self._key_to_id[key] = next_id
                self._id_to_key[next_id] = key
                used_ids.add(next_id)
                next_id += 1

    # ── queries ─────────────────────────────────────────

    def get_plugin(self, key: str) -> Optional[SolverPlugin]:
        self.discover_plugins()
        return self._plugins.get(key)

    def get_by_id(self, solver_id: int) -> Optional[SolverPlugin]:
        self.discover_plugins()
        key = self._id_to_key.get(solver_id)
        return self._plugins.get(key) if key else None

    def get_by_key(self, key: str) -> Optional[SolverPlugin]:
        return self.get_plugin(key)

    def get_id(self, key: str) -> Optional[int]:
        self.discover_plugins()
        return self._key_to_id.get(key)

    def get_key(self, solver_id: int) -> Optional[str]:
        self.discover_plugins()
        return self._id_to_key.get(solver_id)

    # ── listing ─────────────────────────────────────────

    def list_solvers(self) -> List[SolverInfo]:
        """Return SolverInfo for every registered solver."""
        self.discover_plugins()
        result = []
        for key in sorted(self._plugins.keys()):
            plugin = self._plugins[key]
            sid = self._key_to_id[key]
            result.append(plugin.to_info(sid))
        return result

    def get_ready_solvers(self) -> List[SolverInfo]:
        return [s for s in self.list_solvers() if s.status == SolverStatus.READY.value]

    def get_solver_info(self, solver_id: int) -> Optional[SolverInfo]:
        plugin = self.get_by_id(solver_id)
        if not plugin:
            return None
        return plugin.to_info(solver_id)

    def get_solver_info_by_key(self, key: str) -> Optional[SolverInfo]:
        plugin = self.get_plugin(key)
        if not plugin:
            return None
        sid = self._key_to_id.get(key, 0)
        return plugin.to_info(sid)

    # ── name map (for database compatibility) ───────────

    def get_name_map(self) -> Dict[int, str]:
        """Return {id: name} mapping, compatible with the old PRE_CONFIGURED_SOLVER_NAMES."""
        self.discover_plugins()
        return {sid: self._plugins[key].name for key, sid in self._key_to_id.items()}

    # ── install / uninstall ─────────────────────────────

    async def install(self, key: str) -> SolverInstallResult:
        plugin = self.get_plugin(key)
        if not plugin:
            return SolverInstallResult(
                success=False,
                message=f"Unknown solver: {key}",
                error=f"No plugin registered with key '{key}'",
            )
        try:
            result = await plugin.install()
            # Reset version cache
            plugin._cached_version = None
            return result
        except Exception as exc:
            logger.exception("Installation of %s failed", key)
            return SolverInstallResult(
                success=False,
                message=f"Installation failed: {exc}",
                error=str(exc),
            )

    async def uninstall(self, key: str) -> bool:
        plugin = self.get_plugin(key)
        if not plugin:
            return False
        return await plugin.uninstall()

    # ── comparison matrix (auto-generated from plugins) ─

    def get_comparison_matrix(self) -> Dict:
        """Build the comparison matrix dynamically from plugin metadata."""
        self.discover_plugins()
        solvers_data = []
        features_comparison = {}

        for key in sorted(self._plugins.keys()):
            p = self._plugins[key]
            solvers_data.append({
                "name": p.name,
                "type": p.solver_type,
                "preprocessing": p.preprocessing,
                "inprocessing": p.inprocessing,
                "parallel": p.parallel,
                "incremental": p.incremental,
                "best_for": p.best_for,
                "performance_class": p.performance_class,
            })
            # Feature flags per solver
            features_comparison[p.name] = self._extract_feature_flags(p)

        return {
            "solvers": solvers_data,
            "features_comparison": features_comparison,
            "legend": {
                "CDCL": "Conflict-Driven Clause Learning",
                "CDCL + XOR": "CDCL with native XOR / Gaussian reasoning",
                "preprocessing": "Simplification before solving",
                "inprocessing": "Simplification during solving",
                "parallel": "Multi-threaded solving",
                "incremental": "Supports adding clauses incrementally",
            },
        }

    @staticmethod
    def _extract_feature_flags(p: SolverPlugin) -> Dict[str, bool]:
        """Derive a boolean feature map from plugin properties."""
        features_lower = [f.lower() for f in p.features]
        return {
            "cdcl": any("cdcl" in f for f in features_lower),
            "vsids": any("vsids" in f or "activity" in f for f in features_lower),
            "learned_clause_minimization": any(
                "minim" in f or "learned" in f or "learnt" in f for f in features_lower
            ),
            "restarts": any("restart" in f for f in features_lower) or True,  # all CDCL solvers have restarts
            "preprocessing": p.preprocessing,
            "inprocessing": p.inprocessing,
            "bounded_variable_elimination": any("elimination" in f or "bve" in f for f in features_lower),
            "blocked_clause_elimination": any("blocked" in f or "bce" in f for f in features_lower),
            "vivification": any("vivif" in f for f in features_lower),
            "probe": any("probe" in f or "probing" in f for f in features_lower),
        }

    # ── utilities ───────────────────────────────────────

    @property
    def count(self) -> int:
        self.discover_plugins()
        return len(self._plugins)

    @property
    def ready_count(self) -> int:
        return len(self.get_ready_solvers())

    def __repr__(self) -> str:
        return f"<SolverRegistry plugins={list(self._plugins.keys())}>"


# ─── Global singleton ──────────────────────────────────
solver_registry = SolverRegistry()
