"""
Experiments API endpoints
"""

from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks, WebSocket
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import asyncio
import subprocess
import psutil
import time
import os
import json
import logging

from .solvers import PRE_CONFIGURED_SOLVERS, get_solver_by_id
from app.solvers import solver_registry

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SCHEMAS ====================

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    timeout_seconds: int = 5000
    memory_limit_mb: int = 8192
    parallel_jobs: int = 1
    solver_ids: List[int]
    benchmark_ids: List[int]


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    timeout_seconds: Optional[int] = None
    memory_limit_mb: Optional[int] = None
    status: Optional[str] = None


# ==================== ACTIVE EXPERIMENTS TRACKING ====================

active_experiments: Dict[int, Dict] = {}


# ==================== ENDPOINTS ====================

@router.get("/")
@router.get("")
async def list_experiments(
    request: Request,
    status: Optional[str] = None
) -> List[Dict]:
    """Get all experiments"""
    db = request.app.state.db
    return db.get_experiments(status=status)


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: int, request: Request) -> Dict:
    """Get a specific experiment with details"""
    db = request.app.state.db
    experiment = db.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Add run statistics
    runs = db.get_runs(experiment_id=experiment_id)
    
    result_counts = {}
    for run in runs:
        result = run.get('result', 'UNKNOWN')
        result_counts[result] = result_counts.get(result, 0) + 1
    
    experiment['result_distribution'] = result_counts
    experiment['runs_count'] = len(runs)
    
    return experiment


@router.post("/")
async def create_experiment(exp: ExperimentCreate, request: Request) -> Dict:
    """Create a new experiment"""
    db = request.app.state.db
    
    # Validate solvers exist in pre-configured solvers
    for solver_id in exp.solver_ids:
        solver = get_solver_by_id(solver_id)
        if not solver:
            raise HTTPException(status_code=400, detail=f"Solver {solver_id} not found in pre-configured solvers")
    
    # Validate benchmarks exist
    for benchmark_id in exp.benchmark_ids:
        if not db.get_benchmark(benchmark_id):
            raise HTTPException(status_code=400, detail=f"Benchmark {benchmark_id} not found")
    
    total_runs = len(exp.solver_ids) * len(exp.benchmark_ids)
    
    experiment_id = db.create_experiment(
        name=exp.name,
        description=exp.description,
        timeout_seconds=exp.timeout_seconds,
        memory_limit_mb=exp.memory_limit_mb,
        parallel_jobs=exp.parallel_jobs,
        metadata={
            'solver_ids': exp.solver_ids,
            'benchmark_ids': exp.benchmark_ids,
            'total_runs': total_runs
        }
    )
    
    # Update total runs
    db.update_experiment(experiment_id, total_runs=total_runs)
    
    return {
        "id": experiment_id,
        "message": f"Experiment '{exp.name}' created successfully",
        "total_runs": total_runs,
        "estimated_time_hours": (total_runs * exp.timeout_seconds) / 3600
    }


@router.put("/{experiment_id}")
async def update_experiment(
    experiment_id: int,
    exp: ExperimentUpdate,
    request: Request
) -> Dict:
    """Update an experiment"""
    db = request.app.state.db
    
    update_data = exp.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    success = db.update_experiment(experiment_id, **update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return {"message": "Experiment updated successfully"}


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: int, request: Request) -> Dict:
    """Delete an experiment and all its runs"""
    db = request.app.state.db
    
    # Stop if running
    if experiment_id in active_experiments:
        active_experiments[experiment_id]['stop'] = True
    
    success = db.delete_experiment(experiment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return {"message": "Experiment deleted successfully"}


@router.post("/{experiment_id}/start")
async def start_experiment(
    experiment_id: int,
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict:
    """Start running an experiment"""
    db = request.app.state.db
    experiment = db.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    if experiment['status'] == 'running':
        raise HTTPException(status_code=400, detail="Experiment already running")
    
    # Parse metadata
    metadata = json.loads(experiment['metadata']) if experiment['metadata'] else {}
    solver_ids = metadata.get('solver_ids', [])
    benchmark_ids = metadata.get('benchmark_ids', [])
    
    if not solver_ids or not benchmark_ids:
        raise HTTPException(status_code=400, detail="No solvers or benchmarks configured")
    
    # Initialize tracking
    active_experiments[experiment_id] = {
        'stop': False,
        'progress': 0,
        'current_solver': None,
        'current_benchmark': None,
        'started_at': datetime.now().isoformat()
    }
    
    # Update status
    db.update_experiment(
        experiment_id,
        status='running',
        started_at=datetime.now().isoformat()
    )
    
    # Start background execution
    background_tasks.add_task(
        run_experiment_task,
        db,
        experiment_id,
        solver_ids,
        benchmark_ids,
        experiment['timeout_seconds'],
        experiment['memory_limit_mb']
    )
    
    return {
        "message": "Experiment started",
        "experiment_id": experiment_id,
        "total_runs": len(solver_ids) * len(benchmark_ids)
    }


@router.post("/{experiment_id}/stop")
async def stop_experiment(experiment_id: int, request: Request) -> Dict:
    """Stop a running experiment"""
    db = request.app.state.db
    
    if experiment_id not in active_experiments:
        raise HTTPException(status_code=400, detail="Experiment not running")
    
    active_experiments[experiment_id]['stop'] = True
    db.update_experiment(experiment_id, status='stopped')
    
    return {"message": "Experiment stop requested"}


@router.get("/{experiment_id}/progress")
async def get_experiment_progress(experiment_id: int, request: Request) -> Dict:
    """Get real-time progress of experiment"""
    db = request.app.state.db
    experiment = db.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    progress_data = active_experiments.get(experiment_id, {})
    
    return {
        "experiment_id": experiment_id,
        "status": experiment['status'],
        "total_runs": experiment['total_runs'],
        "completed_runs": experiment['completed_runs'],
        "failed_runs": experiment['failed_runs'],
        "progress_percent": (experiment['completed_runs'] / experiment['total_runs'] * 100) if experiment['total_runs'] > 0 else 0,
        "current_solver": progress_data.get('current_solver'),
        "current_benchmark": progress_data.get('current_benchmark'),
        "started_at": experiment.get('started_at'),
        "is_active": experiment_id in active_experiments
    }


@router.get("/{experiment_id}/runs")
async def get_experiment_runs(experiment_id: int, request: Request) -> List[Dict]:
    """Get all runs for an experiment"""
    db = request.app.state.db
    return db.get_runs(experiment_id=experiment_id)


# ==================== BACKGROUND TASK ====================

async def run_experiment_task(
    db,
    experiment_id: int,
    solver_ids: List[int],
    benchmark_ids: List[int],
    timeout: int,
    memory_limit: int
):
    """Background task to run experiment"""
    completed = 0
    failed = 0
    
    logger.info(f"Starting experiment {experiment_id} with solvers {solver_ids} and benchmarks {benchmark_ids}")
    
    try:
        for solver_id in solver_ids:
            # Use plugin registry to get the solver
            plugin = solver_registry.get_by_id(solver_id)
            solver = get_solver_by_id(solver_id)
            logger.info(f"Processing solver_id={solver_id}, found={solver is not None}")
            
            if not solver or solver['status'] != 'ready':
                logger.warning(f"Solver {solver_id} not found or not ready, skipping")
                continue
            
            # Verify executable exists
            if not plugin or not plugin.is_installed():
                logger.warning(f"Solver executable not found for {solver.get('name', solver_id)}, skipping")
                continue
            
            logger.info(f"Running solver {solver['name']} on {len(benchmark_ids)} benchmarks")
            
            for benchmark_id in benchmark_ids:
                # Check stop signal
                if active_experiments.get(experiment_id, {}).get('stop'):
                    logger.info(f"Experiment {experiment_id} stopped by user")
                    break
                
                benchmark = db.get_benchmark(benchmark_id)
                if not benchmark:
                    continue
                
                # Update progress tracking
                if experiment_id in active_experiments:
                    active_experiments[experiment_id]['current_solver'] = solver['name']
                    active_experiments[experiment_id]['current_benchmark'] = benchmark['filename']
                
                # Run solver via plugin system
                run_result = await plugin.run(
                    benchmark['filepath'],
                    timeout=timeout,
                    memory_limit_mb=memory_limit,
                )
                result = run_result.to_dict()
                
                logger.info(f"Solver {solver['name']} on {benchmark['filename']}: {result['result']} in {result['wall_time_seconds']:.2f}s")
                
                # Save result
                try:
                    db.add_run(
                        experiment_id=experiment_id,
                        solver_id=solver_id,
                        benchmark_id=benchmark_id,
                        **result
                    )
                    logger.info(f"Run saved successfully for exp={experiment_id}, solver={solver_id}, benchmark={benchmark_id}")
                except Exception as save_error:
                    logger.error(f"Failed to save run: {save_error}")
                
                if result['result'] in ['SAT', 'UNSAT']:
                    completed += 1
                else:
                    failed += 1
                
                # Update experiment progress
                db.update_experiment(
                    experiment_id,
                    completed_runs=completed,
                    failed_runs=failed
                )
            
            if active_experiments.get(experiment_id, {}).get('stop'):
                break
        
        # Mark complete
        db.update_experiment(
            experiment_id,
            status='completed',
            completed_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Experiment {experiment_id} error: {e}")
        db.update_experiment(experiment_id, status='error')
    
    finally:
        # Clean up tracking
        if experiment_id in active_experiments:
            del active_experiments[experiment_id]


# ==================== WEBSOCKET FOR REAL-TIME UPDATES ====================

@router.websocket("/{experiment_id}/ws")
async def experiment_websocket(websocket: WebSocket, experiment_id: int):
    """WebSocket for real-time experiment updates"""
    await websocket.accept()
    
    try:
        while True:
            if experiment_id not in active_experiments:
                await websocket.send_json({
                    "status": "not_running",
                    "message": "Experiment not currently running"
                })
                break
            
            progress = active_experiments[experiment_id]
            await websocket.send_json({
                "status": "running",
                "current_solver": progress.get('current_solver'),
                "current_benchmark": progress.get('current_benchmark'),
                "progress": progress.get('progress', 0)
            })
            
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()
