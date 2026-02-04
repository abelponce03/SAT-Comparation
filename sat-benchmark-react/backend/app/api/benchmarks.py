"""
Benchmarks API endpoints
"""

from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from pathlib import Path
import shutil
import hashlib
import re
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SCHEMAS ====================

class BenchmarkCreate(BaseModel):
    filename: str
    filepath: str
    family: Optional[str] = None
    difficulty: Optional[str] = None
    expected_result: Optional[str] = None
    tags: Optional[str] = None


class BenchmarkFilter(BaseModel):
    family: Optional[str] = None
    difficulty: Optional[str] = None
    min_variables: Optional[int] = None
    max_variables: Optional[int] = None


# ==================== HELPER FUNCTIONS ====================

def parse_cnf_header(filepath: str) -> Dict:
    """Parse CNF file header to extract metadata"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('p cnf'):
                    parts = line.split()
                    if len(parts) >= 4:
                        num_vars = int(parts[2])
                        num_clauses = int(parts[3])
                        ratio = num_clauses / num_vars if num_vars > 0 else 0
                        return {
                            'num_variables': num_vars,
                            'num_clauses': num_clauses,
                            'clause_variable_ratio': round(ratio, 2)
                        }
        return {'num_variables': None, 'num_clauses': None, 'clause_variable_ratio': None}
    except Exception as e:
        logger.error(f"Error parsing CNF {filepath}: {e}")
        return {'num_variables': None, 'num_clauses': None, 'clause_variable_ratio': None}


def classify_family(filename: str) -> str:
    """Classify benchmark family based on filename patterns"""
    patterns = {
        'circuit': r'(circuit|lec|mult|add|barrel)',
        'crypto': r'(crypto|aes|des|md5|sha|hash)',
        'planning': r'(planning|block|gripper|hanoi)',
        'graph': r'(graph|color|clique|ramsey)',
        'scheduling': r'(schedule|job|task|timetable)',
        'random': r'(random|rnd|uniform)',
        'crafted': r'(pigeon|php|parity|queen)',
        'industrial': r'(bmcbonus|velev|ibm|intel)',
        'verification': r'(verify|bmc|safety|reach)'
    }
    
    filename_lower = filename.lower()
    for family, pattern in patterns.items():
        if re.search(pattern, filename_lower):
            return family
    return 'other'


def estimate_difficulty(num_variables: int, num_clauses: int, ratio: float) -> str:
    """Estimate benchmark difficulty"""
    if num_variables is None:
        return 'unknown'
    
    if num_variables < 1000 or (ratio and ratio < 3.0):
        return 'easy'
    elif num_variables < 10000 or (ratio and ratio < 5.0):
        return 'medium'
    else:
        return 'hard'


def get_file_checksum(filepath: str) -> str:
    """Calculate MD5 checksum of file"""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


# ==================== ENDPOINTS ====================

@router.get("/")
async def list_benchmarks(
    request: Request,
    family: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict]:
    """Get all benchmarks with optional filters"""
    db = request.app.state.db
    return db.get_benchmarks(family=family, difficulty=difficulty, limit=limit)


@router.get("/families")
async def get_families(request: Request) -> List[Dict]:
    """Get benchmark families with statistics"""
    db = request.app.state.db
    return db.get_benchmark_families()


@router.get("/stats")
async def get_benchmark_stats(request: Request) -> Dict:
    """Get benchmark statistics"""
    db = request.app.state.db
    benchmarks = db.get_benchmarks()
    families = db.get_benchmark_families()
    
    if not benchmarks:
        return {
            "total": 0,
            "families": [],
            "difficulty_distribution": {},
            "avg_variables": 0,
            "avg_clauses": 0
        }
    
    # Calculate stats
    total_vars = sum(b.get('num_variables') or 0 for b in benchmarks)
    total_clauses = sum(b.get('num_clauses') or 0 for b in benchmarks)
    
    difficulty_counts = {}
    for b in benchmarks:
        diff = b.get('difficulty', 'unknown')
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
    
    return {
        "total": len(benchmarks),
        "families": families,
        "difficulty_distribution": difficulty_counts,
        "avg_variables": total_vars / len(benchmarks) if benchmarks else 0,
        "avg_clauses": total_clauses / len(benchmarks) if benchmarks else 0
    }


@router.get("/{benchmark_id}")
async def get_benchmark(benchmark_id: int, request: Request) -> Dict:
    """Get a specific benchmark by ID"""
    db = request.app.state.db
    benchmark = db.get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return benchmark


@router.get("/{benchmark_id}/preview")
async def preview_benchmark(benchmark_id: int, request: Request, lines: int = 50) -> Dict:
    """Preview first lines of a CNF file"""
    db = request.app.state.db
    benchmark = db.get_benchmark(benchmark_id)
    
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    
    filepath = Path(benchmark['filepath'])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Benchmark file not found")
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content_lines = []
            for i, line in enumerate(f):
                if i >= lines:
                    break
                content_lines.append(line.rstrip())
        
        return {
            "filename": benchmark['filename'],
            "lines": content_lines,
            "total_lines": lines,
            "truncated": len(content_lines) == lines
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.delete("/{benchmark_id}")
async def delete_benchmark(benchmark_id: int, request: Request) -> Dict:
    """Delete a benchmark"""
    db = request.app.state.db
    success = db.delete_benchmark(benchmark_id)
    if not success:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return {"message": "Benchmark deleted successfully"}


@router.post("/upload")
async def upload_benchmarks(
    files: List[UploadFile] = File(...),
    request: Request = None
) -> Dict:
    """Upload CNF benchmark files"""
    from app.core.config import settings
    
    db = request.app.state.db
    benchmarks_dir = Path(settings.BENCHMARKS_PATH)
    benchmarks_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }
    
    for file in files:
        if not file.filename.endswith('.cnf'):
            results["failed"].append({
                "filename": file.filename,
                "error": "Not a CNF file"
            })
            continue
        
        try:
            # Save file
            filepath = benchmarks_dir / file.filename
            with open(filepath, 'wb') as f:
                content = await file.read()
                f.write(content)
            
            # Parse metadata
            metadata = parse_cnf_header(str(filepath))
            family = classify_family(file.filename)
            difficulty = estimate_difficulty(
                metadata.get('num_variables'),
                metadata.get('num_clauses'),
                metadata.get('clause_variable_ratio')
            )
            checksum = get_file_checksum(str(filepath))
            
            # Add to database
            benchmark_id = db.add_benchmark(
                filename=file.filename,
                filepath=str(filepath),
                family=family,
                size_bytes=os.path.getsize(filepath),
                num_variables=metadata.get('num_variables'),
                num_clauses=metadata.get('num_clauses'),
                clause_variable_ratio=metadata.get('clause_variable_ratio'),
                difficulty=difficulty,
                checksum=checksum
            )
            
            if benchmark_id:
                results["success"].append({
                    "id": benchmark_id,
                    "filename": file.filename,
                    "family": family,
                    "difficulty": difficulty,
                    "variables": metadata.get('num_variables'),
                    "clauses": metadata.get('num_clauses')
                })
            else:
                results["skipped"].append({
                    "filename": file.filename,
                    "reason": "Already exists"
                })
                
        except Exception as e:
            results["failed"].append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return results


@router.post("/scan")
async def scan_directory(
    request: Request,
    directory: Optional[str] = None,
    background_tasks: BackgroundTasks = None
) -> Dict:
    """Scan a directory for CNF files and import them"""
    from app.core.config import settings
    
    db = request.app.state.db
    scan_dir = Path(directory) if directory else Path(settings.BENCHMARKS_PATH)
    
    if not scan_dir.exists():
        raise HTTPException(status_code=400, detail="Directory does not exist")
    
    # Find all CNF files
    cnf_files = list(scan_dir.rglob('*.cnf'))
    
    if not cnf_files:
        return {
            "message": "No CNF files found",
            "directory": str(scan_dir),
            "imported": 0
        }
    
    # Import files
    imported = 0
    for filepath in cnf_files:
        try:
            metadata = parse_cnf_header(str(filepath))
            family = classify_family(filepath.name)
            difficulty = estimate_difficulty(
                metadata.get('num_variables'),
                metadata.get('num_clauses'),
                metadata.get('clause_variable_ratio')
            )
            
            benchmark_id = db.add_benchmark(
                filename=filepath.name,
                filepath=str(filepath),
                family=family,
                size_bytes=filepath.stat().st_size,
                num_variables=metadata.get('num_variables'),
                num_clauses=metadata.get('num_clauses'),
                clause_variable_ratio=metadata.get('clause_variable_ratio'),
                difficulty=difficulty,
                checksum=get_file_checksum(str(filepath))
            )
            
            if benchmark_id:
                imported += 1
                
        except Exception as e:
            logger.error(f"Error importing {filepath}: {e}")
    
    return {
        "message": f"Imported {imported} benchmarks",
        "directory": str(scan_dir),
        "found": len(cnf_files),
        "imported": imported,
        "skipped": len(cnf_files) - imported
    }
