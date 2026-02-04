"""
Application Configuration
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List
import yaml


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # Paths
    BASE_PATH: str = str(Path(__file__).parent.parent.parent)
    DATABASE_PATH: str = "data/experiments.db"
    SOLVERS_PATH: str = "data/solvers"
    BENCHMARKS_PATH: str = "data/benchmarks"
    RESULTS_PATH: str = "data/results"
    TEMP_PATH: str = "data/temp"
    CONFIG_PATH: str = "config"
    
    # Defaults
    DEFAULT_TIMEOUT: int = 5000
    DEFAULT_MEMORY_LIMIT: int = 8192
    DEFAULT_PARALLEL_JOBS: int = 4
    
    # Benchmark families
    BENCHMARK_FAMILIES: dict = {
        "circuit": {
            "pattern": "(circuit|lec|mult|add|barrel)",
            "description": "Hardware verification and circuit problems",
            "color": "#FF6B6B"
        },
        "crypto": {
            "pattern": "(crypto|aes|des|md5|sha|hash)",
            "description": "Cryptographic problems",
            "color": "#4ECDC4"
        },
        "planning": {
            "pattern": "(planning|block|gripper|hanoi)",
            "description": "AI Planning problems",
            "color": "#45B7D1"
        },
        "graph": {
            "pattern": "(graph|color|clique|ramsey)",
            "description": "Graph theory problems",
            "color": "#96CEB4"
        },
        "scheduling": {
            "pattern": "(schedule|job|task|timetable)",
            "description": "Scheduling and resource allocation",
            "color": "#FFEAA7"
        },
        "random": {
            "pattern": "(random|rnd|uniform)",
            "description": "Randomly generated instances",
            "color": "#DFE6E9"
        },
        "crafted": {
            "pattern": "(pigeon|php|parity|queen)",
            "description": "Crafted/hard instances",
            "color": "#FD79A8"
        },
        "industrial": {
            "pattern": "(bmcbonus|velev|ibm|intel)",
            "description": "Industrial verification problems",
            "color": "#A29BFE"
        },
        "verification": {
            "pattern": "(verify|bmc|safety|reach)",
            "description": "Software/hardware verification",
            "color": "#74B9FF"
        }
    }
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
