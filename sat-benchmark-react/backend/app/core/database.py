"""
Database Manager for SAT Benchmark Suite
SQLite operations with SQLAlchemy support
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

logger = logging.getLogger(__name__)


def _get_solver_names() -> dict:
    """Dynamically get solver name mappings from the plugin registry."""
    try:
        from app.solvers import solver_registry
        return solver_registry.get_name_map()
    except Exception:
        # Fallback during early init or if registry is not available
        return {}


# Backwards-compatible alias
PRE_CONFIGURED_SOLVER_NAMES = None  # will use _get_solver_names() dynamically


class DatabaseManager:
    """Manages SQLite database for experiments, solvers, benchmarks, and runs"""
    
    def __init__(self, db_path: str = "data/experiments.db"):
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
                description TEXT,
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
                size_bytes INTEGER,
                num_variables INTEGER,
                num_clauses INTEGER,
                clause_variable_ratio REAL,
                difficulty TEXT,
                expected_result TEXT,
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
                
                -- SAT Solver Statistics
                conflicts INTEGER,
                decisions INTEGER,
                propagations INTEGER,
                restarts INTEGER,
                learnt_clauses INTEGER,
                deleted_clauses INTEGER,
                
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
        
        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_solver ON runs(solver_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_benchmark ON runs(benchmark_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_benchmarks_family ON benchmarks(family)")
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    # ==================== SOLVER OPERATIONS ====================
    
    def add_solver(self, name: str, executable_path: str, 
                   version: str = None, source_path: str = None,
                   compile_command: str = None, run_command_template: str = None,
                   description: str = None, status: str = 'ready',
                   metadata: dict = None) -> int:
        """Add a new solver to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO solvers (name, version, executable_path, source_path,
                                   compile_command, run_command_template, description,
                                   status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, version, executable_path, source_path, compile_command,
                  run_command_template, description, status,
                  json.dumps(metadata) if metadata else None))
            
            conn.commit()
            solver_id = cursor.lastrowid
            logger.info(f"Added solver: {name} (ID: {solver_id})")
            return solver_id
            
        except sqlite3.IntegrityError:
            logger.warning(f"Solver '{name}' already exists")
            # Return existing solver ID
            cursor.execute("SELECT id FROM solvers WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row['id'] if row else None
        finally:
            conn.close()
    
    def get_solvers(self, status: str = None) -> List[Dict]:
        """Get all solvers, optionally filtered by status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("SELECT * FROM solvers WHERE status = ? ORDER BY name", (status,))
        else:
            cursor.execute("SELECT * FROM solvers ORDER BY name")
        
        solvers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return solvers
    
    def get_solver(self, solver_id: int) -> Optional[Dict]:
        """Get a single solver by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM solvers WHERE id = ?", (solver_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_solver(self, solver_id: int, **kwargs) -> bool:
        """Update solver fields"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        valid_fields = ['name', 'version', 'executable_path', 'source_path',
                       'compile_command', 'run_command_template', 'status',
                       'description', 'last_compiled', 'metadata']
        
        updates = []
        values = []
        for field, value in kwargs.items():
            if field in valid_fields:
                updates.append(f"{field} = ?")
                if field == 'metadata' and isinstance(value, dict):
                    values.append(json.dumps(value))
                else:
                    values.append(value)
        
        if not updates:
            return False
        
        values.append(solver_id)
        query = f"UPDATE solvers SET {', '.join(updates)} WHERE id = ?"
        
        cursor.execute(query, values)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def delete_solver(self, solver_id: int) -> bool:
        """Delete a solver"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM solvers WHERE id = ?", (solver_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    # ==================== BENCHMARK OPERATIONS ====================

    def get_benchmark_aggregates(self) -> Dict:
        """Get benchmark aggregate statistics using SQL (no full table scan)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Total + averages in one query
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COALESCE(AVG(num_variables), 0) as avg_variables,
                   COALESCE(AVG(num_clauses), 0) as avg_clauses
            FROM benchmarks
        """)
        row = dict(cursor.fetchone())

        # Difficulty distribution
        cursor.execute("""
            SELECT COALESCE(difficulty, 'unknown') as difficulty, COUNT(*) as cnt
            FROM benchmarks GROUP BY difficulty
        """)
        difficulty_distribution = {r['difficulty']: r['cnt'] for r in cursor.fetchall()}

        conn.close()
        return {
            "total": row["total"],
            "avg_variables": row["avg_variables"],
            "avg_clauses": row["avg_clauses"],
            "difficulty_distribution": difficulty_distribution,
        }

    def get_benchmarks_paginated(self, family: str = None, difficulty: str = None,
                                  search: str = None, page: int = 1,
                                  page_size: int = 50) -> Dict:
        """Get benchmarks with server-side pagination"""
        conn = self.get_connection()
        cursor = conn.cursor()

        where_parts = ["1=1"]
        params: list = []

        if family:
            where_parts.append("family = ?")
            params.append(family)
        if difficulty:
            where_parts.append("difficulty = ?")
            params.append(difficulty)
        if search:
            where_parts.append("filename LIKE ?")
            params.append(f"%{search}%")

        where_clause = " AND ".join(where_parts)

        # Count total matching
        cursor.execute(f"SELECT COUNT(*) as cnt FROM benchmarks WHERE {where_clause}", params)
        total = cursor.fetchone()["cnt"]

        # Fetch page
        offset = (max(1, page) - 1) * page_size
        cursor.execute(
            f"SELECT * FROM benchmarks WHERE {where_clause} ORDER BY filename LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()

        pages = max(1, (total + page_size - 1) // page_size)
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    def add_benchmark(self, filename: str, filepath: str,
                     family: str = None, size_bytes: int = None,
                     num_variables: int = None, num_clauses: int = None,
                     clause_variable_ratio: float = None, difficulty: str = None,
                     expected_result: str = None, tags: str = None,
                     checksum: str = None) -> Optional[int]:
        """Add a new benchmark to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO benchmarks (filename, filepath, family, size_bytes,
                                       num_variables, num_clauses, clause_variable_ratio,
                                       difficulty, expected_result, tags, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (filename, filepath, family, size_bytes, num_variables,
                  num_clauses, clause_variable_ratio, difficulty,
                  expected_result, tags, checksum))
            
            conn.commit()
            benchmark_id = cursor.lastrowid
            logger.info(f"Added benchmark: {filename} (ID: {benchmark_id})")
            return benchmark_id
            
        except sqlite3.IntegrityError:
            logger.debug(f"Benchmark '{filename}' already exists, skipping")
            return None
        finally:
            conn.close()
    
    def get_benchmarks(self, family: str = None, difficulty: str = None,
                      limit: int = None) -> List[Dict]:
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
        
        query += " ORDER BY filename"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        benchmarks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return benchmarks
    
    def get_benchmark(self, benchmark_id: int) -> Optional[Dict]:
        """Get a single benchmark by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM benchmarks WHERE id = ?", (benchmark_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_benchmark_families(self) -> List[Dict]:
        """Get unique families with counts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT family, COUNT(*) as count,
                   AVG(num_variables) as avg_variables,
                   AVG(num_clauses) as avg_clauses
            FROM benchmarks
            GROUP BY family
            ORDER BY count DESC
        """)
        families = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return families
    
    def delete_benchmark(self, benchmark_id: int) -> bool:
        """Delete a benchmark"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM benchmarks WHERE id = ?", (benchmark_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    # ==================== EXPERIMENT OPERATIONS ====================
    
    def create_experiment(self, name: str, description: str = None,
                         timeout_seconds: int = 5000, memory_limit_mb: int = 8192,
                         parallel_jobs: int = 1, metadata: dict = None) -> int:
        """Create a new experiment"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experiments (name, description, timeout_seconds,
                                    memory_limit_mb, parallel_jobs, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, description, timeout_seconds, memory_limit_mb,
              parallel_jobs, json.dumps(metadata) if metadata else None))
        
        conn.commit()
        experiment_id = cursor.lastrowid
        conn.close()
        logger.info(f"Created experiment: {name} (ID: {experiment_id})")
        return experiment_id
    
    def get_experiments(self, status: str = None) -> List[Dict]:
        """Get all experiments"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM experiments WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM experiments ORDER BY created_at DESC")
        
        experiments = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return experiments
    
    def get_experiment(self, experiment_id: int) -> Optional[Dict]:
        """Get a single experiment"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_experiment(self, experiment_id: int, **kwargs) -> bool:
        """Update experiment fields"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        valid_fields = ['name', 'description', 'status', 'timeout_seconds',
                       'memory_limit_mb', 'parallel_jobs', 'total_runs',
                       'completed_runs', 'failed_runs', 'started_at',
                       'completed_at', 'metadata']
        
        updates = []
        values = []
        for field, value in kwargs.items():
            if field in valid_fields:
                updates.append(f"{field} = ?")
                if field == 'metadata' and isinstance(value, dict):
                    values.append(json.dumps(value))
                else:
                    values.append(value)
        
        if not updates:
            return False
        
        values.append(experiment_id)
        query = f"UPDATE experiments SET {', '.join(updates)} WHERE id = ?"
        
        cursor.execute(query, values)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def delete_experiment(self, experiment_id: int) -> bool:
        """Delete an experiment and its runs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    # ==================== RUN OPERATIONS ====================
    
    def add_run(self, experiment_id: int, solver_id: int, benchmark_id: int,
                result: str = None, **kwargs) -> int:
        """Add a run result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        columns = ['experiment_id', 'solver_id', 'benchmark_id', 'result']
        values = [experiment_id, solver_id, benchmark_id, result]
        
        valid_fields = ['exit_code', 'verified', 'cpu_time_seconds', 'wall_time_seconds',
                       'user_time_seconds', 'system_time_seconds', 'max_memory_kb',
                       'avg_memory_kb', 'conflicts', 'decisions', 'propagations',
                       'restarts', 'learnt_clauses', 'deleted_clauses', 'hostname',
                       'solver_output', 'error_message', 'par2_score']
        
        for field in valid_fields:
            if field in kwargs:
                columns.append(field)
                values.append(kwargs[field])
        
        placeholders = ', '.join(['?' for _ in columns])
        query = f"INSERT OR REPLACE INTO runs ({', '.join(columns)}) VALUES ({placeholders})"
        
        cursor.execute(query, values)
        conn.commit()
        run_id = cursor.lastrowid
        conn.close()
        return run_id
    
    def get_runs(self, experiment_id: int = None, solver_id: int = None,
                benchmark_id: int = None) -> List[Dict]:
        """Get runs with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Modified query to use LEFT JOIN for solvers since we're using pre-configured solvers
        query = """
            SELECT r.*, 
                   COALESCE(s.name, 'Unknown') as solver_name, 
                   b.filename as benchmark_name,
                   b.family as benchmark_family, 
                   e.name as experiment_name
            FROM runs r
            LEFT JOIN solvers s ON r.solver_id = s.id
            JOIN benchmarks b ON r.benchmark_id = b.id
            JOIN experiments e ON r.experiment_id = e.id
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
        
        query += " ORDER BY r.timestamp DESC"
        
        cursor.execute(query, params)
        runs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Map solver names from the solver plugin registry when missing
        name_map = _get_solver_names()
        for run in runs:
            if run.get('solver_name') == 'Unknown':
                run['solver_name'] = name_map.get(run['solver_id'], 'Unknown')
        
        return runs
    
    def get_all_runs(self) -> List[Dict]:
        """Get all runs with details"""
        return self.get_runs()
    
    # ==================== STATISTICS ====================
    
    def get_dashboard_stats(self) -> Dict:
        """Get statistics for dashboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Counts
        cursor.execute("SELECT COUNT(*) FROM solvers")
        stats['total_solvers'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM solvers WHERE status = 'ready'")
        stats['ready_solvers'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM benchmarks")
        stats['total_benchmarks'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM experiments")
        stats['total_experiments'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE status = 'completed'")
        stats['completed_experiments'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE status = 'running'")
        stats['running_experiments'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runs")
        stats['total_runs'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runs WHERE result = 'SAT'")
        stats['sat_results'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runs WHERE result = 'UNSAT'")
        stats['unsat_results'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runs WHERE result = 'TIMEOUT'")
        stats['timeout_results'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runs WHERE result = 'ERROR'")
        stats['error_results'] = cursor.fetchone()[0]
        
        # Recent activity
        cursor.execute("""
            SELECT e.name, e.status, e.created_at, e.completed_runs, e.total_runs
            FROM experiments e
            ORDER BY e.created_at DESC
            LIMIT 5
        """)
        stats['recent_experiments'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return stats
    
    def has_data(self) -> bool:
        """Check if there's any data in the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM runs")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
