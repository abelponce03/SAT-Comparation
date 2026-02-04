"""
Database Manager for SAT Benchmark Suite
Handles SQLite operations with proper schema and migrations
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database for experiments, solvers, benchmarks, and runs"""
    
    def __init__(self, db_path: str = "results/experiments.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Solvers Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solvers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                version TEXT,
                executable_path TEXT NOT NULL,
                source_path TEXT,
                compile_command TEXT,
                run_command_template TEXT,
                last_compiled TIMESTAMP,
                status TEXT DEFAULT 'ready',
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Benchmarks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                filepath TEXT NOT NULL,
                family TEXT,
                size_kb INTEGER,
                num_variables INTEGER,
                num_clauses INTEGER,
                clause_variable_ratio REAL,
                difficulty TEXT,
                tags TEXT,
                checksum TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Experiments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                timeout_seconds INTEGER DEFAULT 5000,
                memory_limit_mb INTEGER DEFAULT 8192,
                parallel_jobs INTEGER DEFAULT 1,
                total_runs INTEGER DEFAULT 0,
                completed_runs INTEGER DEFAULT 0,
                failed_runs INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Runs Table (Main Results)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                solver_id INTEGER NOT NULL,
                benchmark_id INTEGER NOT NULL,
                
                -- Results
                result TEXT,
                exit_code INTEGER,
                verified BOOLEAN DEFAULT 0,
                
                -- Timing
                cpu_time_seconds REAL,
                wall_time_seconds REAL,
                user_time_seconds REAL,
                system_time_seconds REAL,
                
                -- Memory
                max_memory_kb INTEGER,
                avg_memory_kb INTEGER,
                
                -- System Stats
                page_faults INTEGER,
                context_switches_voluntary INTEGER,
                context_switches_involuntary INTEGER,
                cpu_percentage REAL,
                
                -- SAT Solver Statistics
                conflicts INTEGER,
                decisions INTEGER,
                propagations INTEGER,
                restarts INTEGER,
                learnt_literals INTEGER,
                deleted_literals INTEGER,
                learnt_clauses INTEGER,
                deleted_clauses INTEGER,
                
                -- Additional Metrics
                max_learnt_clauses INTEGER,
                avg_learnt_clause_length REAL,
                decision_height_avg REAL,
                decision_height_max INTEGER,
                
                -- Metadata
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hostname TEXT,
                solver_output TEXT,
                error_message TEXT,
                
                -- Performance Metrics (calculated)
                par2_score REAL,
                
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE,
                FOREIGN KEY (solver_id) REFERENCES solvers(id) ON DELETE CASCADE,
                FOREIGN KEY (benchmark_id) REFERENCES benchmarks(id) ON DELETE CASCADE,
                
                UNIQUE(experiment_id, solver_id, benchmark_id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_experiment 
            ON runs(experiment_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_solver 
            ON runs(solver_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_benchmark 
            ON runs(benchmark_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_result 
            ON runs(result)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_benchmarks_family 
            ON benchmarks(family)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    # ==================== SOLVERS ====================
    
    def add_solver(self, name: str, executable_path: str, **kwargs) -> int:
        """Add a new solver to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        metadata = kwargs.pop('metadata', {})
        
        try:
            cursor.execute("""
                INSERT INTO solvers 
                (name, version, executable_path, source_path, compile_command, 
                 run_command_template, last_compiled, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                kwargs.get('version'),
                executable_path,
                kwargs.get('source_path'),
                kwargs.get('compile_command'),
                kwargs.get('run_command_template'),
                kwargs.get('last_compiled'),
                kwargs.get('status', 'ready'),
                json.dumps(metadata)
            ))
            
            solver_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added solver: {name} (ID: {solver_id})")
            return solver_id
            
        except sqlite3.IntegrityError:
            logger.warning(f"Solver {name} already exists")
            cursor.execute("SELECT id FROM solvers WHERE name = ?", (name,))
            return cursor.fetchone()['id']
        finally:
            conn.close()
    
    def get_solvers(self, status: Optional[str] = None) -> List[Dict]:
        """Get all solvers, optionally filtered by status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("SELECT * FROM solvers WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT * FROM solvers")
        
        solvers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Parse metadata JSON
        for solver in solvers:
            if solver['metadata']:
                solver['metadata'] = json.loads(solver['metadata'])
        
        return solvers
    
    def update_solver_status(self, solver_id: int, status: str, **kwargs):
        """Update solver status and optional fields"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = ["status = ?"]
        values = [status]
        
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        values.append(solver_id)
        
        cursor.execute(f"""
            UPDATE solvers 
            SET {', '.join(updates)}
            WHERE id = ?
        """, values)
        
        conn.commit()
        conn.close()
    
    # ==================== BENCHMARKS ====================
    
    def add_benchmark(self, filename: str, filepath: str, **kwargs) -> int:
        """Add a new benchmark to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        tags = kwargs.pop('tags', [])
        if isinstance(tags, list):
            tags = json.dumps(tags)
        
        try:
            cursor.execute("""
                INSERT INTO benchmarks 
                (filename, filepath, family, size_kb, num_variables, num_clauses,
                 clause_variable_ratio, difficulty, tags, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                filename,
                filepath,
                kwargs.get('family'),
                kwargs.get('size_kb'),
                kwargs.get('num_variables'),
                kwargs.get('num_clauses'),
                kwargs.get('clause_variable_ratio'),
                kwargs.get('difficulty'),
                tags,
                kwargs.get('checksum')
            ))
            
            benchmark_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added benchmark: {filename} (ID: {benchmark_id})")
            return benchmark_id
            
        except sqlite3.IntegrityError:
            logger.warning(f"Benchmark {filename} already exists")
            cursor.execute("SELECT id FROM benchmarks WHERE filename = ?", (filename,))
            return cursor.fetchone()['id']
        finally:
            conn.close()
    
    def get_benchmarks(self, family: Optional[str] = None, 
                       difficulty: Optional[str] = None) -> List[Dict]:
        """Get benchmarks with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM benchmarks WHERE 1=1"
        params = []
        
        if family:
            query += " AND family = ?"
            params.append(family)
        
        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty)
        
        cursor.execute(query, params)
        benchmarks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Parse tags JSON
        for bench in benchmarks:
            if bench['tags']:
                bench['tags'] = json.loads(bench['tags'])
        
        return benchmarks
    
    # ==================== EXPERIMENTS ====================
    
    def create_experiment(self, name: str, description: str = "", **kwargs) -> int:
        """Create a new experiment"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        metadata = kwargs.pop('metadata', {})
        
        try:
            cursor.execute("""
                INSERT INTO experiments 
                (name, description, timeout_seconds, memory_limit_mb, 
                 parallel_jobs, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                description,
                kwargs.get('timeout_seconds', 5000),
                kwargs.get('memory_limit_mb', 8192),
                kwargs.get('parallel_jobs', 1),
                json.dumps(metadata)
            ))
            
            experiment_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Created experiment: {name} (ID: {experiment_id})")
            return experiment_id
            
        except sqlite3.IntegrityError:
            logger.error(f"Experiment {name} already exists")
            raise
        finally:
            conn.close()
    
    def get_experiments(self) -> List[Dict]:
        """Get all experiments"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM experiments ORDER BY created_at DESC")
        experiments = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        for exp in experiments:
            if exp['metadata']:
                exp['metadata'] = json.loads(exp['metadata'])
        
        return experiments
    
    def update_experiment_status(self, experiment_id: int, status: str, **kwargs):
        """Update experiment status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = ["status = ?"]
        values = [status]
        
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        values.append(experiment_id)
        
        cursor.execute(f"""
            UPDATE experiments 
            SET {', '.join(updates)}
            WHERE id = ?
        """, values)
        
        conn.commit()
        conn.close()
    
    # ==================== RUNS ====================
    
    def add_run(self, experiment_id: int, solver_id: int, 
                benchmark_id: int, **kwargs) -> int:
        """Add a run result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Calculate PAR-2 score if not provided
        if 'par2_score' not in kwargs:
            timeout = kwargs.get('timeout_seconds', 5000)
            cpu_time = kwargs.get('cpu_time_seconds', 0)
            result = kwargs.get('result', 'UNKNOWN')
            
            if result in ['TIMEOUT', 'MEMOUT', 'ERROR']:
                kwargs['par2_score'] = 2 * timeout
            else:
                kwargs['par2_score'] = cpu_time
        
        try:
            # Prepare all fields with defaults
            fields = {
                'experiment_id': experiment_id,
                'solver_id': solver_id,
                'benchmark_id': benchmark_id,
                
                # Results
                'result': kwargs.get('result', 'UNKNOWN'),
                'exit_code': kwargs.get('exit_code', -1),
                'verified': kwargs.get('verified', False),
                
                # Timing
                'cpu_time_seconds': kwargs.get('cpu_time_seconds', 0.0),
                'wall_time_seconds': kwargs.get('wall_time_seconds', 0.0),
                'user_time_seconds': kwargs.get('user_time_seconds', 0.0),
                'system_time_seconds': kwargs.get('system_time_seconds', 0.0),
                
                # Memory
                'max_memory_kb': kwargs.get('max_memory_kb', 0),
                'avg_memory_kb': kwargs.get('avg_memory_kb', 0),
                
                # System Stats
                'page_faults': kwargs.get('page_faults', 0),
                'context_switches_voluntary': kwargs.get('context_switches_voluntary', 0),
                'context_switches_involuntary': kwargs.get('context_switches_involuntary', 0),
                'cpu_percentage': kwargs.get('cpu_percentage', 0.0),
                
                # SAT Solver Statistics
                'conflicts': kwargs.get('conflicts'),
                'decisions': kwargs.get('decisions'),
                'propagations': kwargs.get('propagations'),
                'restarts': kwargs.get('restarts'),
                'learnt_literals': kwargs.get('learnt_literals'),
                'deleted_literals': kwargs.get('deleted_literals'),
                'learnt_clauses': kwargs.get('learnt_clauses'),
                'deleted_clauses': kwargs.get('deleted_clauses'),
                
                # Additional Metrics
                'max_learnt_clauses': kwargs.get('max_learnt_clauses'),
                'avg_learnt_clause_length': kwargs.get('avg_learnt_clause_length'),
                'decision_height_avg': kwargs.get('decision_height_avg'),
                'decision_height_max': kwargs.get('decision_height_max'),
                
                # Metadata
                'timestamp': kwargs.get('timestamp', datetime.now()),
                'hostname': kwargs.get('hostname'),
                'solver_output': kwargs.get('solver_output', ''),
                'error_message': kwargs.get('error_message', ''),
                
                # Performance
                'par2_score': kwargs.get('par2_score', 0.0)
            }
            
            # Build INSERT query dynamically
            columns = ', '.join(fields.keys())
            placeholders = ', '.join(['?'] * len(fields))
            
            query = f"""
                INSERT INTO runs ({columns})
                VALUES ({placeholders})
            """
            
            cursor.execute(query, list(fields.values()))
            
            run_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Added run {run_id} for experiment {experiment_id}")
            
            return run_id
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Run already exists or integrity error: {e}")
            conn.rollback()
            
            # Try to get existing run ID
            cursor.execute("""
                SELECT id FROM runs 
                WHERE experiment_id = ? AND solver_id = ? AND benchmark_id = ?
            """, (experiment_id, solver_id, benchmark_id))
            
            existing = cursor.fetchone()
            return existing['id'] if existing else None
            
        except Exception as e:
            logger.error(f"Error adding run: {e}")
            conn.rollback()
            raise
            
        finally:
            conn.close()
    
    def get_runs(self, experiment_id: Optional[int] = None,
                 solver_id: Optional[int] = None,
                 benchmark_id: Optional[int] = None) -> List[Dict]:
        """Get runs with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT r.*, s.name as solver_name, b.filename as benchmark_name
            FROM runs r
            JOIN solvers s ON r.solver_id = s.id
            JOIN benchmarks b ON r.benchmark_id = b.id
            WHERE 1=1
        """
        params = []
        
        if experiment_id:
            query += " AND r.experiment_id = ?"
            params.append(experiment_id)
        
        if solver_id:
            query += " AND r.solver_id = ?"
            params.append(solver_id)
        
        if benchmark_id:
            query += " AND r.benchmark_id = ?"
            params.append(benchmark_id)
        
        cursor.execute(query, params)
        runs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return runs
    
    def get_experiment_summary(self, experiment_id: int) -> Dict[str, Any]:
        """Get summary statistics for an experiment"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_runs,
                SUM(CASE WHEN result = 'SAT' THEN 1 ELSE 0 END) as sat_count,
                SUM(CASE WHEN result = 'UNSAT' THEN 1 ELSE 0 END) as unsat_count,
                SUM(CASE WHEN result = 'TIMEOUT' THEN 1 ELSE 0 END) as timeout_count,
                SUM(CASE WHEN result = 'MEMOUT' THEN 1 ELSE 0 END) as memout_count,
                SUM(CASE WHEN result = 'ERROR' THEN 1 ELSE 0 END) as error_count,
                AVG(cpu_time_seconds) as avg_cpu_time,
                AVG(max_memory_kb) as avg_memory,
                AVG(par2_score) as avg_par2
            FROM runs
            WHERE experiment_id = ?
        """, (experiment_id,))
        
        summary = dict(cursor.fetchone())
        conn.close()
        
        return summary
    
    # ==================== UTILITY METHODS ====================
    
    def has_data(self) -> bool:
        """Check if database has any runs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM runs")
        count = cursor.fetchone()['count']
        
        conn.close()
        return count > 0
    
    def get_all_runs(self) -> 'pd.DataFrame':
        """
        Get all runs as a pandas DataFrame with joined information
        Returns DataFrame with columns:
        - solver: solver name
        - benchmark: benchmark filename
        - family: benchmark family
        - result: SAT/UNSAT/TIMEOUT/ERROR
        - wall_time_seconds: wall clock time
        - cpu_time_seconds: CPU time
        - max_memory_kb: max memory usage
        - conflicts, decisions, propagations: solver statistics
        """
        import pandas as pd
        
        conn = self.get_connection()
        
        query = """
            SELECT 
                s.name as solver,
                b.filename as benchmark,
                b.family as family,
                b.size_kb as benchmark_size_kb,
                b.num_variables,
                b.num_clauses,
                r.result,
                r.exit_code,
                r.cpu_time_seconds,
                r.wall_time_seconds,
                r.user_time_seconds,
                r.system_time_seconds,
                r.max_memory_kb,
                r.avg_memory_kb,
                r.cpu_percentage,
                r.conflicts,
                r.decisions,
                r.propagations,
                r.restarts,
                r.learnt_literals,
                r.deleted_literals,
                r.learnt_clauses,
                r.deleted_clauses,
                r.par2_score,
                r.timestamp,
                r.hostname,
                e.name as experiment_name,
                e.timeout_seconds
            FROM runs r
            JOIN solvers s ON r.solver_id = s.id
            JOIN benchmarks b ON r.benchmark_id = b.id
            JOIN experiments e ON r.experiment_id = e.id
            ORDER BY r.timestamp DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_solver_id_by_name(self, solver_name: str) -> Optional[int]:
        """Get solver ID by name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM solvers WHERE name = ?", (solver_name,))
        result = cursor.fetchone()
        
        conn.close()
        return result['id'] if result else None
    
    def get_benchmark_id_by_filename(self, filename: str) -> Optional[int]:
        """Get benchmark ID by filename"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM benchmarks WHERE filename = ?", (filename,))
        result = cursor.fetchone()
        
        conn.close()
        return result['id'] if result else None
    
    def get_experiment_id_by_name(self, name: str) -> Optional[int]:
        """Get experiment ID by name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM experiments WHERE name = ?", (name,))
        result = cursor.fetchone()
        
        conn.close()
        return result['id'] if result else None
    
    def delete_experiment(self, experiment_id: int):
        """Delete an experiment and all its runs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM runs WHERE experiment_id = ?", (experiment_id,))
            cursor.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
            conn.commit()
            logger.info(f"Deleted experiment ID {experiment_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting experiment: {e}")
            raise
        finally:
            conn.close()
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Count tables
        for table in ['solvers', 'benchmarks', 'experiments', 'runs']:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[f'{table}_count'] = cursor.fetchone()['count']
        
        # Database size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        stats['db_size_bytes'] = cursor.fetchone()['size']
        stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024 * 1024), 2)
        
        conn.close()
        return stats
    
    def export_to_csv(self, output_path: str, experiment_id: Optional[int] = None):
        """Export runs to CSV file"""
        import pandas as pd
        
        df = self.get_all_runs()
        
        if experiment_id:
            df = df[df['experiment_name'] == experiment_id]
        
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} runs to {output_path}")
        
        return output_path
    
    # ==================== CLEANUP METHODS ====================
    
    def find_duplicate_benchmarks(self) -> List[Dict]:
        """Find duplicate benchmarks by filename"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filename, COUNT(*) as count, 
                   GROUP_CONCAT(id) as ids,
                   GROUP_CONCAT(COALESCE(num_variables, 'NULL')) as variables,
                   GROUP_CONCAT(COALESCE(num_clauses, 'NULL')) as clauses,
                   GROUP_CONCAT(COALESCE(family, 'NULL')) as families
            FROM benchmarks
            GROUP BY filename
            HAVING count > 1
            ORDER BY count DESC
        """)
        
        duplicates = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            row_dict['ids'] = [int(x) for x in row_dict['ids'].split(',')]
            duplicates.append(row_dict)
        
        conn.close()
        return duplicates
    
    def find_invalid_benchmarks(self) -> List[Dict]:
        """Find benchmarks with NULL or unknown values"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, family, difficulty, num_variables, num_clauses
            FROM benchmarks
            WHERE num_variables IS NULL 
               OR num_clauses IS NULL
               OR family = 'unknown'
               OR difficulty = 'unknown'
            ORDER BY filename
        """)
        
        invalid = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return invalid
    
    def delete_benchmarks_batch(self, benchmark_ids: List[int]) -> Dict[str, int]:
        """
        Delete multiple benchmarks at once
        
        Args:
            benchmark_ids: List of benchmark IDs to delete
        
        Returns:
            Dict with 'deleted', 'failed', 'has_runs' counts
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {
            'deleted': 0,
            'failed': 0,
            'has_runs': 0,
            'errors': []
        }
        
        for bench_id in benchmark_ids:
            try:
                # Check if benchmark has runs
                cursor.execute(
                    "SELECT COUNT(*) as count FROM runs WHERE benchmark_id = ?", 
                    (bench_id,)
                )
                run_count = cursor.fetchone()['count']
                
                if run_count > 0:
                    stats['has_runs'] += 1
                    
                    # Get benchmark name for error message
                    cursor.execute("SELECT filename FROM benchmarks WHERE id = ?", (bench_id,))
                    bench_name = cursor.fetchone()
                    filename = bench_name['filename'] if bench_name else f"ID {bench_id}"
                    
                    stats['errors'].append({
                        'id': bench_id,
                        'error': f'Has {run_count} existing runs - cannot delete',
                        'filename': filename
                    })
                    logger.warning(f"Cannot delete benchmark {bench_id} - has {run_count} runs")
                    continue
                
                # Delete benchmark
                cursor.execute("DELETE FROM benchmarks WHERE id = ?", (bench_id,))
                stats['deleted'] += 1
                logger.info(f"Deleted benchmark ID {bench_id}")
                
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append({
                    'id': bench_id,
                    'error': str(e)
                })
                logger.error(f"Error deleting benchmark {bench_id}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Batch delete completed: {stats['deleted']} deleted, {stats['failed']} failed, {stats['has_runs']} with runs")
        return stats
    
    def keep_best_duplicate(self, filename: str) -> int:
        """
        Keep only the best version of a duplicate benchmark
        Priority: most complete data (non-null values)
        
        Returns:
            Number of duplicates deleted
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all versions of this benchmark
        cursor.execute("""
            SELECT id, num_variables, num_clauses, family, difficulty, 
                   size_kb, checksum,
                   (CASE WHEN num_variables IS NOT NULL THEN 1 ELSE 0 END) +
                   (CASE WHEN num_clauses IS NOT NULL THEN 1 ELSE 0 END) +
                   (CASE WHEN family IS NOT NULL AND family != 'unknown' THEN 1 ELSE 0 END) +
                   (CASE WHEN difficulty IS NOT NULL AND difficulty != 'unknown' THEN 1 ELSE 0 END) +
                   (CASE WHEN checksum IS NOT NULL AND checksum != '' THEN 1 ELSE 0 END)
                   as completeness_score
            FROM benchmarks
            WHERE filename = ?
            ORDER BY completeness_score DESC, id ASC
        """, (filename,))
        
        versions = [dict(row) for row in cursor.fetchall()]
        
        if len(versions) <= 1:
            conn.close()
            return 0
        
        # Keep the first (best) version
        keep_id = versions[0]['id']
        delete_ids = [v['id'] for v in versions[1:]]
        
        # Delete duplicates
        for del_id in delete_ids:
            cursor.execute("DELETE FROM benchmarks WHERE id = ?", (del_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Kept benchmark ID {keep_id}, deleted {len(delete_ids)} duplicates")
        return len(delete_ids)
    
    def cleanup_all_duplicates(self) -> Dict[str, int]:
        """
        Automatically clean all duplicate benchmarks
        Keeps the most complete version of each
        """
        duplicates = self.find_duplicate_benchmarks()
        
        stats = {
            'total_duplicates': len(duplicates),
            'benchmarks_cleaned': 0,
            'versions_deleted': 0
        }
        
        for dup in duplicates:
            deleted = self.keep_best_duplicate(dup['filename'])
            if deleted > 0:
                stats['benchmarks_cleaned'] += 1
                stats['versions_deleted'] += deleted
        
        logger.info(f"Cleanup completed: {stats['versions_deleted']} duplicates removed")
        return stats
    
    def get_benchmark_completeness(self) -> Dict:
        """Get statistics about benchmark data completeness"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN num_variables IS NULL THEN 1 ELSE 0 END) as missing_variables,
                SUM(CASE WHEN num_clauses IS NULL THEN 1 ELSE 0 END) as missing_clauses,
                SUM(CASE WHEN family IS NULL OR family = 'unknown' THEN 1 ELSE 0 END) as unknown_family,
                SUM(CASE WHEN difficulty IS NULL OR difficulty = 'unknown' THEN 1 ELSE 0 END) as unknown_difficulty,
                SUM(CASE WHEN checksum IS NULL OR checksum = '' THEN 1 ELSE 0 END) as missing_checksum
            FROM benchmarks
        """)
        
        stats = dict(cursor.fetchone())
        conn.close()
        
        return stats
