"""
Dashboard API endpoints
"""

from fastapi import APIRouter, Depends, Request
from typing import Dict
from app.api.solvers import PRE_CONFIGURED_SOLVERS
from pathlib import Path
import os

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(request: Request) -> Dict:
    """Get dashboard statistics"""
    db = request.app.state.db
    stats = db.get_dashboard_stats()
    
    # Override solver counts with pre-configured solvers
    total_solvers = len(PRE_CONFIGURED_SOLVERS)
    ready_solvers = sum(1 for s in PRE_CONFIGURED_SOLVERS.values() 
                        if Path(s['executable_path']).exists() and 
                        os.access(s['executable_path'], os.X_OK))
    
    stats['total_solvers'] = total_solvers
    stats['ready_solvers'] = ready_solvers
    
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
