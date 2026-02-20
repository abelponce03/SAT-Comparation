"""
SAT Solver Plugin System
========================
Dynamic solver registry with auto-discovery, installation, and management.

Usage:
    from app.solvers import solver_registry
    
    # Get all registered solvers
    all_solvers = solver_registry.list_solvers()
    
    # Get only ready solvers
    ready = solver_registry.get_ready_solvers()
    
    # Get a solver by id or key
    solver = solver_registry.get_by_id(1)
    solver = solver_registry.get_by_key("kissat")
    
    # Install a solver
    result = await solver_registry.install("cadical")
"""

from .registry import SolverRegistry, solver_registry
from .base import SolverPlugin, SolverInfo, SolverInstallResult

__all__ = [
    "SolverRegistry",
    "solver_registry",
    "SolverPlugin",
    "SolverInfo",
    "SolverInstallResult",
]
