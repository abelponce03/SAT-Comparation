"""
Dashboard API endpoints
"""

from fastapi import APIRouter, Depends, Request
from typing import Dict
from app.solvers import solver_registry
from pathlib import Path
import os

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(request: Request) -> Dict:
    """Get dashboard statistics"""
    db = request.app.state.db
    stats = db.get_dashboard_stats()
    
    # Override solver counts with plugin registry data
    stats['total_solvers'] = solver_registry.count
    stats['ready_solvers'] = solver_registry.ready_count
    
    return stats


@router.get("/recent-activity")
async def get_recent_activity(request: Request, limit: int = 10) -> Dict:
    """Get recent experiments and runs"""
    db = request.app.state.db
    
    experiments = db.get_experiments()[:limit]
    
    return {
        "recent_experiments": experiments,
        "total_experiments": len(db.get_experiments()),
        "total_runs": len(db.get_all_runs()) if db.has_data() else 0
    }
