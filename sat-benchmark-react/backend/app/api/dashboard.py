"""
Dashboard API endpoints
"""

from fastapi import APIRouter, Depends, Request
from typing import Dict

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(request: Request) -> Dict:
    """Get dashboard statistics"""
    db = request.app.state.db
    return db.get_dashboard_stats()


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
