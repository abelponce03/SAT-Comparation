"""
Benchmark Manager - Handles scanning, importing, and managing CNF benchmarks
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import yaml
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.database import DatabaseManager
from app.utils.cnf_parser import parse_benchmark_metadata

logger = logging.getLogger(__name__)


class BenchmarkManager:
    """Manages benchmark files and database operations"""
    
    def __init__(self, config_path: str = "config/app_config.yaml"):
        self.config = self._load_config(config_path)
        self.db = DatabaseManager()
        self.benchmark_dir = Path(self.config['paths']['benchmarks'])
        self.family_patterns = {
            name: info['pattern'] 
            for name, info in self.config['benchmark_families'].items()
        }
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def scan_benchmark_directory(self, directory: Optional[str] = None) -> List[str]:
        """
        Scan directory for CNF files
        
        Returns:
            List of CNF file paths
        """
        if directory is None:
            directory = self.benchmark_dir
        else:
            directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"Benchmark directory does not exist: {directory}")
            return []
        
        cnf_files = []
        
        # Search for .cnf files recursively
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.cnf'):
                    filepath = Path(root) / file
                    cnf_files.append(str(filepath))
        
        logger.info(f"Found {len(cnf_files)} CNF files in {directory}")
        return cnf_files
    
    def import_benchmark(self, filepath: str, 
                        auto_classify: bool = True) -> Optional[int]:
        """
        Import a single benchmark into database
        
        Args:
            filepath: Path to CNF file
            auto_classify: Auto-detect family and difficulty
        
        Returns:
            Benchmark ID or None if failed
        """
        try:
            # Parse metadata
            metadata = parse_benchmark_metadata(filepath, self.family_patterns)
            
            # Add to database
            benchmark_id = self.db.add_benchmark(**metadata)
            
            logger.info(f"Imported benchmark: {metadata['filename']} (ID: {benchmark_id})")
            return benchmark_id
            
        except Exception as e:
            logger.error(f"Error importing benchmark {filepath}: {e}")
            return None
    
    def import_benchmarks_batch(self, filepaths: List[str], 
                               max_workers: int = 4,
                               progress_callback=None) -> Dict[str, int]:
        """
        Import multiple benchmarks in parallel
        
        Args:
            filepaths: List of CNF file paths
            max_workers: Number of parallel workers
            progress_callback: Optional callback(completed, total, filename)
        
        Returns:
            Dict with 'success', 'failed', 'skipped' counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        total = len(filepaths)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.import_benchmark, fp): fp 
                for fp in filepaths
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                filepath = futures[future]
                filename = Path(filepath).name
                
                try:
                    benchmark_id = future.result()
                    
                    if benchmark_id is not None:
                        results['success'] += 1
                    else:
                        results['skipped'] += 1
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': filename,
                        'error': str(e)
                    })
                    logger.error(f"Failed to import {filename}: {e}")
                
                # Progress callback
                if progress_callback:
                    progress_callback(i, total, filename)
        
        return results
    
    def get_benchmarks_dataframe(self, family: Optional[str] = None,
                                difficulty: Optional[str] = None) -> pd.DataFrame:
        """Get benchmarks as pandas DataFrame"""
        benchmarks = self.db.get_benchmarks(family=family, difficulty=difficulty)
        return pd.DataFrame(benchmarks)
    
    def get_family_statistics(self) -> pd.DataFrame:
        """Get statistics by family"""
        benchmarks = self.db.get_benchmarks()
        df = pd.DataFrame(benchmarks)
        
        if df.empty:
            return pd.DataFrame()
        
        stats = df.groupby('family').agg({
            'filename': 'count',
            'size_kb': 'sum',
            'num_variables': 'mean',
            'num_clauses': 'mean',
            'clause_variable_ratio': 'mean'
        }).round(2)
        
        stats.columns = ['Count', 'Total Size (KB)', 'Avg Variables', 
                        'Avg Clauses', 'Avg C/V Ratio']
        
        return stats.sort_values('Count', ascending=False)
    
    def get_difficulty_distribution(self) -> Dict[str, int]:
        """Get distribution of difficulties"""
        benchmarks = self.db.get_benchmarks()
        df = pd.DataFrame(benchmarks)
        
        if df.empty:
            return {}
        
        return df['difficulty'].value_counts().to_dict()
    
    def delete_benchmark(self, benchmark_id: int):
        """Delete a benchmark from database"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if benchmark has runs
            cursor.execute("SELECT COUNT(*) as count FROM runs WHERE benchmark_id = ?", 
                          (benchmark_id,))
            run_count = cursor.fetchone()['count']
            
            if run_count > 0:
                raise ValueError(f"Cannot delete benchmark with {run_count} existing runs")
            
            cursor.execute("DELETE FROM benchmarks WHERE id = ?", (benchmark_id,))
            conn.commit()
            logger.info(f"Deleted benchmark ID {benchmark_id}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting benchmark: {e}")
            raise
        finally:
            conn.close()
    
    def update_benchmark_classification(self, benchmark_id: int,
                                       family: Optional[str] = None,
                                       difficulty: Optional[str] = None,
                                       tags: Optional[List[str]] = None):
        """Update benchmark classification"""
        import json
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if family:
            updates.append("family = ?")
            values.append(family)
        
        if difficulty:
            updates.append("difficulty = ?")
            values.append(difficulty)
        
        if tags is not None:
            updates.append("tags = ?")
            values.append(json.dumps(tags))
        
        if not updates:
            return
        
        values.append(benchmark_id)
        
        cursor.execute(f"""
            UPDATE benchmarks 
            SET {', '.join(updates)}
            WHERE id = ?
        """, values)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated benchmark {benchmark_id}")
    
    def search_benchmarks(self, query: str) -> List[Dict]:
        """Search benchmarks by filename"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM benchmarks 
            WHERE filename LIKE ?
            ORDER BY filename
        """, (f"%{query}%",))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_benchmark_details(self, benchmark_id: int) -> Optional[Dict]:
        """Get detailed information about a benchmark"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM benchmarks WHERE id = ?", (benchmark_id,))
        result = cursor.fetchone()
        
        if not result:
            return None
        
        benchmark = dict(result)
        
        # Get run statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_runs,
                COUNT(DISTINCT solver_id) as unique_solvers,
                AVG(cpu_time_seconds) as avg_time,
                MIN(cpu_time_seconds) as best_time,
                MAX(cpu_time_seconds) as worst_time
            FROM runs
            WHERE benchmark_id = ?
        """, (benchmark_id,))
        
        stats = dict(cursor.fetchone())
        benchmark['run_stats'] = stats
        
        conn.close()
        return benchmark