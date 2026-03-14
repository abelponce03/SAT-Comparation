"""
Solvers API endpoints — backed by the dynamic YAML-based solver registry.

All solver metadata, installation, and comparison data are
generated automatically from ``solver_definitions.yaml``.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from pathlib import Path
import os
import logging

from app.solvers import solver_registry

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== COMPATIBILITY LAYER ======================================

def _build_compat_dict() -> Dict[str, Dict]:
    """Build a dict that looks like the old PRE_CONFIGURED_SOLVERS."""
    solvers = solver_registry.list_solvers()
    return {
        info.key: {
            "id": info.id,
            "name": info.name,
            "version": info.version,
            "description": info.description,
            "executable_path": info.executable_path,
            "run_command_template": "{executable} {input_file}",
            "status": info.status,
            "features": info.features,
            "website": info.website,
            "category": info.category,
        }
        for info in solvers
    }


class _LazyDict:
    """Backwards-compatible dict facade."""

    def values(self):
        return _build_compat_dict().values()

    def keys(self):
        return _build_compat_dict().keys()

    def items(self):
        return _build_compat_dict().items()

    def __contains__(self, key):
        return key in _build_compat_dict()

    def __getitem__(self, key):
        return _build_compat_dict()[key]

    def __iter__(self):
        return iter(_build_compat_dict())

    def __len__(self):
        return len(_build_compat_dict())

    def get(self, key, default=None):
        return _build_compat_dict().get(key, default)


PRE_CONFIGURED_SOLVERS = _LazyDict()


def get_solver_by_id(solver_id: int) -> Optional[Dict]:
    """Get a solver by its ID — compatible with old code."""
    info = solver_registry.get_solver_info(solver_id)
    if info is None:
        return None
    return {
        "id": info.id,
        "key": info.key,
        "name": info.name,
        "version": info.version,
        "description": info.description,
        "executable_path": info.executable_path,
        "run_command_template": "{executable} {input_file}",
        "status": info.status,
        "features": info.features,
        "website": info.website,
        "category": info.category,
    }


# ==================== SCHEMAS ====================

class InstallRequest(BaseModel):
    solver_key: str


# ==================== HELPER ====================

def _solver_info_to_dict(info, has_build_config: bool = True) -> Dict:
    """Convert a SolverInfo to a JSON-serialisable dict."""
    return {
        "id": info.id,
        "key": info.key,
        "name": info.name,
        "version": info.version,
        "description": info.description,
        "executable_path": info.executable_path,
        "status": info.status,
        "features": info.features,
        "website": info.website,
        "category": info.category,
        "solver_type": info.solver_type,
        "preprocessing": info.preprocessing,
        "inprocessing": info.inprocessing,
        "parallel": info.parallel,
        "incremental": info.incremental,
        "best_for": info.best_for,
        "performance_class": info.performance_class,
        "has_plugin": True,
        "has_build_config": has_build_config,
    }


# ==================== ENDPOINTS ====================

@router.get("/")
async def list_solvers(request: Request, status: Optional[str] = None) -> List[Dict]:
    """Get all registered solvers (those with plugins) with live status."""
    all_solvers = solver_registry.list_solvers()
    result = [_solver_info_to_dict(info) for info in all_solvers]

    if status and status != "all":
        result = [s for s in result if s["status"] == status]

    return result


@router.get("/count")
async def get_solver_count() -> Dict:
    """Get count of available solvers."""
    all_solvers = solver_registry.list_solvers()
    ready = sum(1 for s in all_solvers if s.status == "ready")

    catalog_count = 0
    for info in all_solvers:
        plugin = solver_registry.get_plugin(info.key)
        if not getattr(plugin, "has_build_config", True):
            catalog_count += 1

    installable = len(all_solvers) - catalog_count
    return {
        "total": len(all_solvers),
        "ready": ready,
        "not_installed": installable - ready,
        "catalog_only": catalog_count,
        "total_known": len(all_solvers),
    }


@router.get("/library")
async def get_solver_library() -> Dict:
    """
    Get the complete solver library: installed, available (has build config),
    and catalog-only (informational, no build instructions).

    This is the main endpoint for the Solvers module UI.
    """
    all_solvers = solver_registry.list_solvers()

    installed = []
    available = []
    catalog = []

    for info in all_solvers:
        plugin = solver_registry.get_plugin(info.key)
        has_build = getattr(plugin, "has_build_config", True)
        d = _solver_info_to_dict(info, has_build_config=has_build)

        if info.status == "ready":
            installed.append(d)
        elif has_build:
            available.append(d)
        else:
            d["status"] = "catalog"
            catalog.append(d)

    return {
        "installed": installed,
        "available": available,
        "catalog": catalog,
        "stats": {
            "installed_count": len(installed),
            "available_count": len(available),
            "catalog_count": len(catalog),
            "total_known": len(installed) + len(available) + len(catalog),
        },
    }


@router.get("/comparison-matrix")
async def get_comparison_matrix() -> Dict:
    """Get solver comparison matrix — auto-generated from plugins."""
    return solver_registry.get_comparison_matrix()


@router.get("/ready")
async def get_ready_solvers() -> List[Dict]:
    """Get only the solvers that are ready to use."""
    return [_solver_info_to_dict(info) for info in solver_registry.get_ready_solvers()]


@router.get("/templates/list")
async def get_solver_templates() -> Dict:
    """Get information about supported solver formats."""
    all_solvers = solver_registry.list_solvers()
    return {
        "supported_solvers": [s.key for s in all_solvers],
        "info": (
            "Solvers are defined declaratively in solver_definitions.yaml. "
            "To add a new solver, add an entry with name, repository, and "
            "build steps — no Python code required."
        ),
        "solvers": {
            s.key: {"name": s.name, "version": s.version, "category": s.category}
            for s in all_solvers
        },
    }


@router.get("/{solver_id}")
async def get_solver(solver_id: int, request: Request) -> Dict:
    """Get a specific solver by numeric ID."""
    info = solver_registry.get_solver_info(solver_id)
    if not info:
        raise HTTPException(status_code=404, detail="Solver not found")
    return _solver_info_to_dict(info)


@router.get("/by-name/{solver_name}")
async def get_solver_by_name(solver_name: str) -> Dict:
    """Get a solver by its key name."""
    info = solver_registry.get_solver_info_by_key(solver_name.lower())
    if not info:
        raise HTTPException(status_code=404, detail=f"Solver '{solver_name}' not found")
    return _solver_info_to_dict(info)


@router.post("/{solver_id}/test")
async def test_solver(solver_id: int, request: Request) -> Dict:
    """Test if a solver binary is working correctly."""
    plugin = solver_registry.get_by_id(solver_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Solver not found")

    result = {
        "success": False,
        "solver_name": plugin.name,
        "version_output": None,
        "error": None,
        "is_executable": False,
        "path_exists": False,
    }

    exe = plugin.executable_path
    if not exe.exists():
        result["error"] = f"Executable not found at {exe}"
        return result

    result["path_exists"] = True

    if not os.access(str(exe), os.X_OK):
        result["error"] = "File exists but is not executable"
        return result

    result["is_executable"] = True

    import subprocess
    flags_to_try = list(plugin.version_flags) + ["--help", "-h"]
    for flag in flags_to_try:
        try:
            cmd = [str(exe)] + ([flag] if flag else [])
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            output = proc.stdout or proc.stderr
            if output:
                result["success"] = True
                result["version_output"] = output[:500]
                return result
        except Exception:
            continue

    try:
        proc = subprocess.run([str(exe)], capture_output=True, text=True, timeout=5)
        output = proc.stdout or proc.stderr
        if output or proc.returncode == 0:
            result["success"] = True
            result["version_output"] = output[:500] if output else "Solver executed successfully"
            return result
    except Exception as e:
        result["error"] = str(e)
        return result

    result["error"] = "Solver did not produce any output"
    return result


@router.post("/install")
async def install_solver(req: InstallRequest) -> Dict:
    """Install a solver by key (clone + compile from source)."""
    key = req.solver_key.lower()
    logger.info("Install request for solver: %s", key)

    result = await solver_registry.install(key)
    if not result.success:
        return {
            "success": False,
            "message": result.message,
            "error": result.error,
            "log": result.log,
        }

    return {
        "success": True,
        "message": result.message,
        "version": result.version,
    }


@router.post("/uninstall/{solver_key}")
async def uninstall_solver(solver_key: str) -> Dict:
    """Uninstall (remove) a solver by key."""
    key = solver_key.lower()
    ok = await solver_registry.uninstall(key)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Could not uninstall '{key}'")
    return {"message": f"Solver '{key}' uninstalled successfully"}
