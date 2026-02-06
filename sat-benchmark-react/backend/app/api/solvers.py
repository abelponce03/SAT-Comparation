"""
Pre-configured Solvers API endpoints
This module uses pre-compiled solvers instead of user-managed ones.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from pathlib import Path
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== PRE-CONFIGURED SOLVERS ====================

# Define pre-compiled solvers with their paths
# These are relative to the main project directory
PRE_CONFIGURED_SOLVERS = {
    "kissat": {
        "id": 1,
        "name": "Kissat",
        "version": "4.0.4",
        "description": "Kissat SAT Solver - Powerful CDCL solver that won multiple SAT competitions (2020, 2021, 2022). Known for excellent performance on industrial and crafted instances.",
        "executable_path": "/app/solvers/kissat/build/kissat",
        "run_command_template": "{executable} {input_file}",
        "status": "ready",
        "features": ["CDCL", "Preprocessing", "Inprocessing", "Learned clause minimization", "Vivification", "Lucky phases"],
        "website": "https://github.com/arminbiere/kissat",
        "category": "competition"
    },
    "minisat": {
        "id": 2,
        "name": "MiniSat",
        "version": "2.2.0",
        "description": "MiniSat - Minimalistic, open-source SAT solver. The reference implementation for CDCL algorithm with two-watched literals. Widely used in academia and as a base for many derived solvers.",
        "executable_path": "/app/solvers/minisat/core/minisat",
        "run_command_template": "{executable} {input_file} {output_file}",
        "status": "ready",
        "features": ["CDCL", "Conflict clause learning", "Variable activity (VSIDS)", "Two-watched literals", "Phase saving"],
        "website": "http://minisat.se/",
        "category": "educational"
    },
    "cadical": {
        "id": 3,
        "name": "CaDiCaL",
        "version": "2.1.3",
        "description": "CaDiCaL - Conflict-Driven Clause Learning SAT Solver by Armin Biere. "
                       "Advanced CDCL with chronological backtracking and extensive inprocessing. "
                       "Multiple SAT Competition wins. Also the backbone of the CaDiCaL-based portfolio.",
        "executable_path": "/app/solvers/cadical/build/cadical",
        "run_command_template": "{executable} {input_file}",
        "status": "not_installed",
        "features": ["CDCL", "Chronological backtracking", "Inprocessing", "Vivification", "Lucky phases", "Bounded variable elimination"],
        "website": "https://github.com/arminbiere/cadical",
        "category": "competition"
    },
    "cryptominisat": {
        "id": 4,
        "name": "CryptoMiniSat",
        "version": "5.11.22",
        "description": "CryptoMiniSat - Advanced SAT solver with XOR reasoning by Mate Soos. "
                       "Excels on cryptographic and structured instances with Gaussian elimination.",
        "executable_path": "/app/solvers/cryptominisat/build/cryptominisat5",
        "run_command_template": "{executable} {input_file}",
        "status": "not_installed",
        "features": ["CDCL", "XOR reasoning", "Gaussian elimination", "Component caching", "SQL logging"],
        "website": "https://github.com/msoos/cryptominisat",
        "category": "competition"
    }
}


# ==================== HELPER FUNCTIONS ====================

# Cache detected versions so we only probe once per process lifetime
_detected_versions: Dict[str, str] = {}

def _detect_solver_version(solver_key: str, solver: Dict) -> Optional[str]:
    """Try to detect the real version of a solver binary at runtime."""
    if solver_key in _detected_versions:
        return _detected_versions[solver_key]

    exe = Path(solver["executable_path"])
    if not exe.exists() or not os.access(str(exe), os.X_OK):
        return None

    # Each solver has its own way to report version
    version_flags = {
        "kissat": ["--version"],
        "minisat": ["--help"],   # MiniSat prints version in first line
        "cadical": ["--version"],
        "cryptominisat": ["--version"],
    }

    flags = version_flags.get(solver_key, ["--version"])
    try:
        result = subprocess.run(
            [str(exe)] + flags,
            capture_output=True, text=True, timeout=5
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            return None

        # Parse version from output
        import re
        if solver_key == "minisat":
            # MiniSat prints something like "This is MiniSat 2.2.0"
            m = re.search(r"MiniSat\s+([\d.]+)", output, re.IGNORECASE)
            if m:
                ver = m.group(1)
                _detected_versions[solver_key] = ver
                return ver
        else:
            # For kissat / cadical / cms the first line usually is just the version
            first = output.splitlines()[0].strip()
            m = re.search(r"([\d]+\.[\d]+\.[\d]+)", first)
            if m:
                ver = m.group(1)
                _detected_versions[solver_key] = ver
                return ver
    except Exception as exc:
        logger.debug("Version detection failed for %s: %s", solver_key, exc)

    return None


def get_solver_by_id(solver_id: int) -> Optional[Dict]:
    """Get a solver by its ID from pre-configured solvers"""
    for solver in PRE_CONFIGURED_SOLVERS.values():
        if solver['id'] == solver_id:
            return solver
    return None


# ==================== SCHEMAS ====================

class SolverResponse(BaseModel):
    id: int
    name: str
    version: str
    description: str
    executable_path: str
    status: str
    features: List[str]
    website: str
    category: str


class SolverTestResult(BaseModel):
    success: bool
    solver_name: str
    version_output: Optional[str] = None
    error: Optional[str] = None
    is_executable: bool
    path_exists: bool


# ==================== ENDPOINTS ====================

@router.get("/")
async def list_solvers(request: Request, status: Optional[str] = None) -> List[Dict]:
    """Get all pre-configured solvers"""
    import copy
    solvers = [copy.deepcopy(s) for s in PRE_CONFIGURED_SOLVERS.values()]
    
    # Check actual status and detect real version for each solver
    for key, solver in zip(PRE_CONFIGURED_SOLVERS.keys(), solvers):
        exe_path = Path(solver['executable_path'])
        if exe_path.exists() and os.access(str(exe_path), os.X_OK):
            solver['status'] = 'ready'
            # Try dynamic version detection (cached after first call)
            detected = _detect_solver_version(key, solver)
            if detected:
                solver['version'] = detected
        else:
            solver['status'] = 'unavailable'
    
    # Filter by status if provided
    if status and status != 'all':
        solvers = [s for s in solvers if s['status'] == status]
    
    return solvers


@router.get("/count")
async def get_solver_count() -> Dict:
    """Get count of available solvers"""
    total = len(PRE_CONFIGURED_SOLVERS)
    ready = sum(1 for s in PRE_CONFIGURED_SOLVERS.values() 
                if Path(s['executable_path']).exists() and 
                os.access(s['executable_path'], os.X_OK))
    
    return {
        "total": total,
        "ready": ready,
        "unavailable": total - ready
    }


@router.get("/comparison-matrix")
async def get_comparison_matrix() -> Dict:
    """Get solver comparison matrix for UI display"""
    comparison_data = {
        "solvers": [
            {
                "name": "Kissat",
                "type": "CDCL",
                "preprocessing": True,
                "inprocessing": True,
                "parallel": False,
                "incremental": False,
                "best_for": ["Industrial", "Crafted", "Competition"],
                "performance_class": "State-of-the-art"
            },
            {
                "name": "MiniSat",
                "type": "CDCL",
                "preprocessing": False,
                "inprocessing": False,
                "parallel": False,
                "incremental": True,
                "best_for": ["Educational", "Research", "Small instances"],
                "performance_class": "Reference implementation"
            },
            {
                "name": "CaDiCaL",
                "type": "CDCL",
                "preprocessing": True,
                "inprocessing": True,
                "parallel": False,
                "incremental": True,
                "best_for": ["Industrial", "Verification", "Competition"],
                "performance_class": "State-of-the-art"
            },
            {
                "name": "CryptoMiniSat",
                "type": "CDCL + XOR",
                "preprocessing": True,
                "inprocessing": True,
                "parallel": True,
                "incremental": True,
                "best_for": ["Cryptographic", "XOR-heavy", "Structured"],
                "performance_class": "Specialized"
            }
        ],
        "features_comparison": {
            "Kissat": {
                "cdcl": True,
                "vsids": True,
                "learned_clause_minimization": True,
                "restarts": True,
                "preprocessing": True,
                "inprocessing": True,
                "bounded_variable_elimination": True,
                "blocked_clause_elimination": True,
                "vivification": True,
                "probe": True
            },
            "MiniSat": {
                "cdcl": True,
                "vsids": True,
                "learned_clause_minimization": True,
                "restarts": True,
                "preprocessing": False,
                "inprocessing": False,
                "bounded_variable_elimination": False,
                "blocked_clause_elimination": False,
                "vivification": False,
                "probe": False
            },
            "CaDiCaL": {
                "cdcl": True,
                "vsids": True,
                "learned_clause_minimization": True,
                "restarts": True,
                "preprocessing": True,
                "inprocessing": True,
                "bounded_variable_elimination": True,
                "blocked_clause_elimination": True,
                "vivification": True,
                "probe": True
            },
            "CryptoMiniSat": {
                "cdcl": True,
                "vsids": True,
                "learned_clause_minimization": True,
                "restarts": True,
                "preprocessing": True,
                "inprocessing": True,
                "bounded_variable_elimination": True,
                "blocked_clause_elimination": False,
                "vivification": False,
                "probe": True
            }
        },
        "legend": {
            "CDCL": "Conflict-Driven Clause Learning",
            "CDCL + XOR": "CDCL with native XOR / Gaussian reasoning",
            "preprocessing": "Simplification before solving",
            "inprocessing": "Simplification during solving",
            "parallel": "Multi-threaded solving",
            "incremental": "Supports adding clauses incrementally"
        }
    }
    return comparison_data


@router.get("/{solver_id}")
async def get_solver(solver_id: int, request: Request) -> Dict:
    """Get a specific solver by ID"""
    for solver in PRE_CONFIGURED_SOLVERS.values():
        if solver['id'] == solver_id:
            # Update status
            exe_path = Path(solver['executable_path'])
            solver_copy = solver.copy()
            if exe_path.exists() and os.access(str(exe_path), os.X_OK):
                solver_copy['status'] = 'ready'
            else:
                solver_copy['status'] = 'unavailable'
            return solver_copy
    
    raise HTTPException(status_code=404, detail="Solver not found")


@router.get("/by-name/{solver_name}")
async def get_solver_by_name(solver_name: str) -> Dict:
    """Get a solver by its key name"""
    solver_key = solver_name.lower()
    if solver_key in PRE_CONFIGURED_SOLVERS:
        solver = PRE_CONFIGURED_SOLVERS[solver_key].copy()
        exe_path = Path(solver['executable_path'])
        if exe_path.exists() and os.access(str(exe_path), os.X_OK):
            solver['status'] = 'ready'
        else:
            solver['status'] = 'unavailable'
        return solver
    
    raise HTTPException(status_code=404, detail=f"Solver '{solver_name}' not found")


@router.post("/{solver_id}/test")
async def test_solver(solver_id: int, request: Request) -> Dict:
    """Test if a solver is working correctly"""
    solver = None
    for s in PRE_CONFIGURED_SOLVERS.values():
        if s['id'] == solver_id:
            solver = s
            break
    
    if not solver:
        raise HTTPException(status_code=404, detail="Solver not found")
    
    exe_path = Path(solver['executable_path'])
    
    result = {
        "success": False,
        "solver_name": solver['name'],
        "version_output": None,
        "error": None,
        "is_executable": False,
        "path_exists": False
    }
    
    # Check if path exists
    if not exe_path.exists():
        result["error"] = f"Executable not found at {exe_path}"
        return result
    
    result["path_exists"] = True
    
    # Check if executable
    if not os.access(str(exe_path), os.X_OK):
        result["error"] = "File exists but is not executable"
        return result
    
    result["is_executable"] = True
    
    try:
        # Try to run with --help or --version
        # Different solvers have different flags
        for flag in ["--version", "-V", "--help", "-h"]:
            try:
                proc = subprocess.run(
                    [str(exe_path), flag],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                output = proc.stdout or proc.stderr
                if output:
                    result["success"] = True
                    result["version_output"] = output[:500]  # Limit output
                    return result
            except:
                continue
        
        # If no flag worked, just try running it (it might exit with usage)
        proc = subprocess.run(
            [str(exe_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = proc.stdout or proc.stderr
        if output or proc.returncode == 0:
            result["success"] = True
            result["version_output"] = output[:500] if output else "Solver executed successfully"
        else:
            result["error"] = "Solver did not produce any output"
            
    except subprocess.TimeoutExpired:
        result["error"] = "Timeout while testing solver"
    except Exception as e:
        result["error"] = str(e)
    
    return result


@router.get("/templates/list")
async def get_solver_templates() -> Dict:
    """Get information about supported solver formats"""
    return {
        "supported_solvers": list(PRE_CONFIGURED_SOLVERS.keys()),
        "info": "This installation uses pre-compiled solvers. Contact administrator to add new solvers.",
        "solvers": {
            key: {
                "name": s["name"],
                "version": s["version"],
                "category": s["category"]
            }
            for key, s in PRE_CONFIGURED_SOLVERS.items()
        }
    }


@router.get("/ready")
async def get_ready_solvers() -> List[Dict]:
    """Get only the solvers that are ready to use"""
    ready_solvers = []
    
    for solver in PRE_CONFIGURED_SOLVERS.values():
        exe_path = Path(solver['executable_path'])
        if exe_path.exists() and os.access(str(exe_path), os.X_OK):
            solver_copy = solver.copy()
            solver_copy['status'] = 'ready'
            ready_solvers.append(solver_copy)
    
    return ready_solvers