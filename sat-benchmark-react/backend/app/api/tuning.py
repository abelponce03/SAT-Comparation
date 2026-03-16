from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from app.analysis.tuning import AlgorithmTuner

router = APIRouter(
    tags=["Algorithm Configuration"]
)

class TuningRequest(BaseModel):
    solver_name: str
    instances: List[str]
    timeout_per_run: float = 300.0
    max_evaluations: int = 50

class AblationRequest(BaseModel):
    solver_name: str
    instances: List[str]
    incumbent_config: Dict[str, Any]
    timeout_per_run: float = 300.0

# Store results in-memory for prototype (should be DB in production)
TUNING_JOBS = {}
ABLATION_JOBS = {}

def execute_tuning_task(job_id: str, req: TuningRequest):
    try:
        TUNING_JOBS[job_id]["status"] = "running"
        tuner = AlgorithmTuner(
            solver_name=req.solver_name,
            instances=req.instances,
            timeout_per_run=req.timeout_per_run,
            max_evaluations=req.max_evaluations
        )
        incumbent = tuner.run_tuning()
        
        TUNING_JOBS[job_id]["status"] = "completed"
        TUNING_JOBS[job_id]["incumbent"] = incumbent.get_dictionary()
    except Exception as e:
        TUNING_JOBS[job_id]["status"] = "error"
        TUNING_JOBS[job_id]["error"] = str(e)


@router.post("/start")
async def start_tuning(req: TuningRequest, background_tasks: BackgroundTasks):
    """
    Inicia el proceso de Tuning (Algoritm Configuration) de SMAC3 en background.
    """
    job_id = f"tune_{req.solver_name}_{len(req.instances)}inst"
    
    if job_id in TUNING_JOBS and TUNING_JOBS[job_id]["status"] == "running":
        return {"message": "Job ya está en ejecución", "job_id": job_id}
        
    TUNING_JOBS[job_id] = {"status": "pending", "request": req.dict()}
    
    background_tasks.add_task(execute_tuning_task, job_id, req)
    
    return {"message": "Tuning iniciado", "job_id": job_id}


@router.get("/status/{job_id}")
async def get_tuning_status(job_id: str):
    """
    Obtiene el estado de un job de tuning
    """
    if job_id not in TUNING_JOBS:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return TUNING_JOBS[job_id]


async def execute_ablation_task(job_id: str, req: AblationRequest):
    try:
        ABLATION_JOBS[job_id]["status"] = "running"
        from app.analysis.tuning import AblationAnalyzer
        
        analyzer = AblationAnalyzer(
            solver_name=req.solver_name,
            instances=req.instances,
            timeout_per_run=req.timeout_per_run
        )
        
        results = await analyzer.analyze_ablation(req.incumbent_config)
        
        ABLATION_JOBS[job_id]["status"] = "completed"
        ABLATION_JOBS[job_id]["results"] = results
    except Exception as e:
        ABLATION_JOBS[job_id]["status"] = "error"
        ABLATION_JOBS[job_id]["error"] = str(e)


@router.post("/ablation/start")
async def start_ablation(req: AblationRequest, background_tasks: BackgroundTasks):
    """
    Inicia Análisis de Ablación en background
    """
    job_id = f"ablate_{req.solver_name}_{len(req.instances)}inst"
    
    if job_id in ABLATION_JOBS and ABLATION_JOBS[job_id]["status"] == "running":
        return {"message": "Job de Ablación ya en ejecución", "job_id": job_id}
        
    ABLATION_JOBS[job_id] = {"status": "pending", "request": req.dict()}
    
    background_tasks.add_task(execute_ablation_task, job_id, req)
    
    return {"message": "Ablation iniciada", "job_id": job_id}

@router.get("/ablation/status/{job_id}")
async def get_ablation_status(job_id: str):
    """
    Obtiene el estado de un job de ablación
    """
    if job_id not in ABLATION_JOBS:
        raise HTTPException(status_code=404, detail="Job de Ablación no encontrado")
    return ABLATION_JOBS[job_id]
