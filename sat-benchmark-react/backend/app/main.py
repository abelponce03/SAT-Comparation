"""
SAT Benchmark Suite - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.api import solvers, benchmarks, experiments, analysis, dashboard, sat_modeler, rigorous_analysis
from app.core.database import DatabaseManager
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting SAT Benchmark Suite API...")
    
    # Initialize database
    db = DatabaseManager(settings.DATABASE_PATH)
    app.state.db = db
    
    # Create necessary directories
    for path in [settings.SOLVERS_PATH, settings.BENCHMARKS_PATH, 
                 settings.RESULTS_PATH, settings.TEMP_PATH]:
        Path(path).mkdir(parents=True, exist_ok=True)
    
    logger.info("Database and directories initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SAT Benchmark Suite API...")


# Create FastAPI application
app = FastAPI(
    title="SAT Benchmark Suite API",
    description="""
    API para el sistema de benchmarking de SAT Solvers.
    
    ## Funcionalidades
    
    * **Solvers**: Gestión de solucionadores SAT (agregar, compilar, eliminar)
    * **Benchmarks**: Importación y clasificación de instancias CNF
    * **Experiments**: Creación y ejecución de experimentos
    * **Analysis**: Análisis estadístico (PAR-2, VBS, comparaciones)
    * **Visualization**: Datos para gráficos (Cactus, Scatter, Heatmap)
    """,
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(solvers.router, prefix="/api/solvers", tags=["Solvers"])
app.include_router(benchmarks.router, prefix="/api/benchmarks", tags=["Benchmarks"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["Experiments"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(rigorous_analysis.router, prefix="/api/rigorous", tags=["Rigorous Analysis"])
app.include_router(sat_modeler.router, prefix="/api/modeler", tags=["SAT Modeler"])


@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "SAT Benchmark Suite API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
