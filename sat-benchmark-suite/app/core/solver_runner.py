"""
Solver Runner - Execute SAT solvers with monitoring and resource tracking
"""

import subprocess
import time
import psutil
import signal
import os
from pathlib import Path
from typing import Dict, Optional, Callable
import threading
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class SolverRunner:
    """Manages SAT solver execution with resource monitoring"""
    
    def __init__(self, timeout_seconds: int = 5000, memory_limit_mb: int = 8192):
        self.timeout = timeout_seconds
        self.memory_limit = memory_limit_mb * 1024 * 1024  # Convert to bytes
        self.process = None
        self.start_time = None
        self.monitoring_thread = None
        self.stop_monitoring = False
        
        # Monitoring data
        self.resource_usage = {
            'max_memory_kb': 0,
            'avg_memory_kb': 0,
            'memory_samples': [],
            'cpu_percentage': 0.0,
            'cpu_samples': [],
            'page_faults': 0,
            'context_switches_voluntary': 0,
            'context_switches_involuntary': 0
        }
    
    def run_solver(
        self,
        solver_executable: str,
        benchmark_path: str,
        output_file: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Execute solver on a benchmark with monitoring
        
        Args:
            solver_executable: Path to solver binary
            benchmark_path: Path to CNF benchmark file
            output_file: Optional path to save solver output
            progress_callback: Callback for progress updates (elapsed_time, memory_usage)
        
        Returns:
            Dict with execution results and statistics
        """
        
        logger.info(f"Running solver: {solver_executable} on {benchmark_path}")
        
        # ========== FIX: Validar ejecutable ==========
        from pathlib import Path
        
        exe_path = Path(solver_executable)
        
        # Verificar que existe
        if not exe_path.exists():
            logger.error(f"Solver executable not found: {solver_executable}")
            return {
                'result': 'ERROR',
                'error_message': f"Executable not found: {solver_executable}",
                'exit_code': -1,
                'wall_time_seconds': 0,
                'cpu_time_seconds': 0,
                'max_memory_kb': 0,
                'avg_memory_kb': 0,
                'cpu_percentage': 0.0,
                'solver_output': '',
                'conflicts': None,
                'decisions': None,
                'propagations': None,
                'restarts': None,
                'learnt_literals': None,
                'deleted_literals': None,
                'learnt_clauses': None,
            }
        
        # Verificar que NO es un header
        if exe_path.suffix in ['.h', '.hpp', '.c', '.cpp']:
            logger.error(f"Executable appears to be source code: {solver_executable}")
            return {
                'result': 'ERROR',
                'error_message': f"Invalid executable (source file): {solver_executable}",
                'exit_code': -1,
                'wall_time_seconds': 0,
                'cpu_time_seconds': 0,
                'max_memory_kb': 0,
                'avg_memory_kb': 0,
                'cpu_percentage': 0.0,
                'solver_output': '',
                'conflicts': None,
                'decisions': None,
                'propagations': None,
                'restarts': None,
                'learnt_literals': None,
                'deleted_literals': None,
                'learnt_clauses': None,
            }
        
        # Verificar permisos de ejecución (Unix)
        if os.name != 'nt' and not os.access(solver_executable, os.X_OK):
            logger.error(f"Solver not executable: {solver_executable}")
            return {
                'result': 'ERROR',
                'error_message': f"File not executable: {solver_executable}",
                'exit_code': -1,
                'wall_time_seconds': 0,
                'cpu_time_seconds': 0,
                'max_memory_kb': 0,
                'avg_memory_kb': 0,
                'cpu_percentage': 0.0,
                'solver_output': '',
                'conflicts': None,
                'decisions': None,
                'propagations': None,
                'restarts': None,
                'learnt_literals': None,
                'deleted_literals': None,
                'learnt_clauses': None,
            }
        
        # ========== FIX: Construir comando correctamente ==========
        
        # Escapar rutas con espacios
        solver_executable = f'"{solver_executable}"' if ' ' in solver_executable else solver_executable
        benchmark_path = f'"{benchmark_path}"' if ' ' in benchmark_path else benchmark_path
        
        # Construir comando
        if output_file:
            output_file = f'"{output_file}"' if ' ' in output_file else output_file
            cmd = f"{solver_executable} {benchmark_path} > {output_file}"
        else:
            cmd = f"{solver_executable} {benchmark_path}"
        
        logger.info(f"Command: {cmd}")
        
        # ========== FIX: No abrir archivos automáticamente ==========
        
        # Reset monitoring data
        self.resource_usage = {
            'max_memory_kb': 0,
            'avg_memory_kb': 0,
            'memory_samples': [],
            'cpu_percentage': 0.0,
            'cpu_samples': [],
            'page_faults': 0,
            'context_switches_voluntary': 0,
            'context_switches_involuntary': 0
        }
        
        self.start_time = time.time()
        result = {
            'result': 'UNKNOWN',
            'exit_code': -1,
            'cpu_time_seconds': 0,
            'wall_time_seconds': 0,
            'user_time_seconds': 0,
            'system_time_seconds': 0,
            'max_memory_kb': 0,
            'avg_memory_kb': 0,
            'cpu_percentage': 0.0,
            'solver_output': '',
            'error_message': '',
            'timed_out': False,
            'memory_exceeded': False,
            
            # SAT solver statistics
            'conflicts': None,
            'decisions': None,
            'propagations': None,
            'restarts': None,
            'learnt_literals': None,
            'deleted_literals': None,
            'learnt_clauses': None,
        }
        
        try:
            # Start process
            self.process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None,
                # ========== FIX: Importante para evitar ventanas emergentes ==========
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Start monitoring thread
            self.stop_monitoring = False
            self.monitoring_thread = threading.Thread(
                target=self._monitor_resources,
                args=(progress_callback,)
            )
            self.monitoring_thread.start()
            
            # Wait for completion or timeout
            try:
                stdout, stderr = self.process.communicate(timeout=self.timeout)
                result['exit_code'] = self.process.returncode
                result['solver_output'] = stdout.decode('utf-8', errors='ignore')
                
                if stderr:
                    result['error_message'] = stderr.decode('utf-8', errors='ignore')
                
            except subprocess.TimeoutExpired:
                logger.warning(f"Solver timed out after {self.timeout}s")
                result['timed_out'] = True
                result['result'] = 'TIMEOUT'
                self._kill_process()
                
                # Try to get partial output
                try:
                    stdout, stderr = self.process.communicate(timeout=5)
                    result['solver_output'] = stdout.decode('utf-8', errors='ignore')
                except:
                    pass
            
            # Stop monitoring
            self.stop_monitoring = True
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=2)
            
            # Calculate timing
            end_time = time.time()
            result['wall_time_seconds'] = end_time - self.start_time
            
            # Get process resource usage if available
            try:
                if self.process and self.process.pid:
                    proc = psutil.Process(self.process.pid)
                    cpu_times = proc.cpu_times()
                    result['user_time_seconds'] = cpu_times.user
                    result['system_time_seconds'] = cpu_times.system
                    result['cpu_time_seconds'] = cpu_times.user + cpu_times.system
                    
                    # Context switches and page faults
                    num_ctx_switches = proc.num_ctx_switches()
                    result['context_switches_voluntary'] = num_ctx_switches.voluntary
                    result['context_switches_involuntary'] = num_ctx_switches.involuntary
                    
                    memory_info = proc.memory_info()
                    result['page_faults'] = memory_info.pfaults if hasattr(memory_info, 'pfaults') else 0
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # Add monitoring data
            result['max_memory_kb'] = self.resource_usage['max_memory_kb']
            result['avg_memory_kb'] = self.resource_usage['avg_memory_kb']
            result['cpu_percentage'] = self.resource_usage['cpu_percentage']
            
            # Parse result from output
            if not result['timed_out']:
                result['result'] = self._parse_solver_result(
                    result['solver_output'],
                    result['exit_code']
                )
            
            # Parse solver statistics
            stats = self._parse_solver_statistics(result['solver_output'])
            result.update(stats)
            
            # Check memory exceeded
            if result['max_memory_kb'] > self.memory_limit // 1024:
                result['memory_exceeded'] = True
                if result['result'] not in ['TIMEOUT', 'ERROR']:
                    result['result'] = 'MEMOUT'
            
            logger.info(f"Solver finished: {result['result']} in {result['wall_time_seconds']:.2f}s")
            
        except Exception as e:
            logger.error(f"Error running solver: {e}")
            result['error_message'] = str(e)
            result['result'] = 'ERROR'
            self.stop_monitoring = True
        
        return result
    
    def _monitor_resources(self, progress_callback: Optional[Callable] = None):
        """Monitor process resources in background thread"""
        
        try:
            proc = psutil.Process(self.process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.warning("Cannot monitor process resources")
            return
        
        sample_interval = 0.1  # 100ms
        
        while not self.stop_monitoring:
            try:
                # Memory usage
                memory_info = proc.memory_info()
                memory_kb = memory_info.rss // 1024
                
                self.resource_usage['memory_samples'].append(memory_kb)
                self.resource_usage['max_memory_kb'] = max(
                    self.resource_usage['max_memory_kb'],
                    memory_kb
                )
                
                # CPU usage
                cpu_percent = proc.cpu_percent(interval=None)
                self.resource_usage['cpu_samples'].append(cpu_percent)
                
                # Check memory limit
                if memory_kb > self.memory_limit // 1024:
                    logger.warning(f"Memory limit exceeded: {memory_kb} KB")
                    self._kill_process()
                    break
                
                # Progress callback
                if progress_callback:
                    elapsed = time.time() - self.start_time
                    progress_callback(elapsed, memory_kb)
                
                time.sleep(sample_interval)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                break
        
        # Calculate averages
        if self.resource_usage['memory_samples']:
            self.resource_usage['avg_memory_kb'] = int(
                sum(self.resource_usage['memory_samples']) / len(self.resource_usage['memory_samples'])
            )
        
        if self.resource_usage['cpu_samples']:
            self.resource_usage['cpu_percentage'] = sum(self.resource_usage['cpu_samples']) / len(self.resource_usage['cpu_samples'])
    
    def _kill_process(self):
        """Kill the running process"""
        if self.process:
            try:
                if os.name == 'nt':
                    self.process.kill()
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except Exception as e:
                logger.error(f"Error killing process: {e}")
    
    def _parse_solver_result(self, output: str, exit_code: int) -> str:
        """Parse solver result from output"""
        
        output_upper = output.upper()
        
        # Check for explicit SAT/UNSAT in output
        if 'UNSATISFIABLE' in output_upper or 's UNSATISFIABLE' in output_upper:
            return 'UNSAT'
        elif 'SATISFIABLE' in output_upper and 'UNSATISFIABLE' not in output_upper:
            return 'SAT'
        
        # Check exit codes (MiniSat convention)
        if exit_code == 10:
            return 'SAT'
        elif exit_code == 20:
            return 'UNSAT'
        elif exit_code == 124:  # Timeout exit code
            return 'TIMEOUT'
        elif exit_code != 0:
            return 'ERROR'
        
        return 'UNKNOWN'
    
    def _parse_solver_statistics(self, output: str) -> Dict:
        """Parse solver statistics from output (MiniSat format)"""
        
        stats = {
            'conflicts': None,
            'decisions': None,
            'propagations': None,
            'restarts': None,
            'learnt_literals': None,
            'deleted_literals': None,
            'learnt_clauses': None,
        }
        
        # MiniSat output patterns
        patterns = {
            'conflicts': r'conflicts\s*:\s*(\d+)',
            'decisions': r'decisions\s*:\s*(\d+)',
            'propagations': r'propagations\s*:\s*(\d+)',
            'restarts': r'restarts\s*:\s*(\d+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                stats[key] = int(match.group(1))
        
        # Parse learned clauses info
        learnt_match = re.search(r'learnt literals\s*:\s*(\d+)', output, re.IGNORECASE)
        if learnt_match:
            stats['learnt_literals'] = int(learnt_match.group(1))
        
        deleted_match = re.search(r'deleted literals\s*:\s*(\d+\.?\d*)%', output, re.IGNORECASE)
        if deleted_match:
            stats['deleted_literals'] = float(deleted_match.group(1))
        
        return stats


class ExperimentRunner:
    """Manages execution of multiple solver runs (experiments)"""
    
    def __init__(self, db_manager, timeout: int = 5000, memory_limit: int = 8192):
        self.db = db_manager
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.current_run = None
        self.stop_requested = False
    
    def get_pending_runs(self, experiment_id: int, solver_ids: list, benchmark_ids: list) -> list:
        """
        Get list of runs that haven't been executed yet
        
        Returns:
            List of (solver_id, benchmark_id) tuples for pending runs
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get already completed runs
        cursor.execute("""
            SELECT solver_id, benchmark_id
            FROM runs
            WHERE experiment_id = ?
        """, (experiment_id,))
        
        completed = set((row['solver_id'], row['benchmark_id']) for row in cursor.fetchall())
        conn.close()
        
        # Generate all possible combinations
        all_runs = [(sid, bid) for sid in solver_ids for bid in benchmark_ids]
        
        # Filter out completed runs
        pending = [run for run in all_runs if run not in completed]
        
        logger.info(f"Experiment {experiment_id}: {len(pending)} pending runs, {len(completed)} already completed")
        
        return pending
    
    def run_experiment(
        self,
        experiment_id: int,
        solver_ids: list,
        benchmark_ids: list,
        progress_callback: Optional[Callable] = None,
        resume: bool = True  # ← NEW: Enable resume by default
    ) -> Dict:
        """
        Run experiment: execute multiple solvers on multiple benchmarks
        
        Args:
            experiment_id: Database experiment ID
            solver_ids: List of solver IDs to run
            benchmark_ids: List of benchmark IDs to test
            progress_callback: Callback(completed, total, current_info)
            resume: If True, skip already completed runs
        
        Returns:
            Dict with execution statistics
        """
        
        self.stop_requested = False
        
        # ========== NEW: Get pending runs ==========
        if resume:
            pending_runs = self.get_pending_runs(experiment_id, solver_ids, benchmark_ids)
            total_runs = len(solver_ids) * len(benchmark_ids)
            already_completed = total_runs - len(pending_runs)
            
            logger.info(f"Resuming experiment: {already_completed} already completed, {len(pending_runs)} pending")
        else:
            pending_runs = [(sid, bid) for sid in solver_ids for bid in benchmark_ids]
            total_runs = len(pending_runs)
            already_completed = 0
        
        completed = already_completed
        failed = 0
        
        stats = {
            'total_runs': total_runs,
            'completed': completed,
            'failed': 0,
            'sat_count': 0,
            'unsat_count': 0,
            'timeout_count': 0,
            'error_count': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'resumed': resume and already_completed > 0
        }
        
        logger.info(f"Starting experiment {experiment_id}: {len(pending_runs)} runs to execute")
        
        # Update experiment status
        self.db.update_experiment_status(
            experiment_id,
            'running',
            started_at=datetime.now() if already_completed == 0 else None,
            total_runs=total_runs
        )
        
        try:
            # ========== MODIFIED: Iterate over pending runs only ==========
            for solver_id, benchmark_id in pending_runs:
                if self.stop_requested:
                    logger.info("Experiment stopped by user request")
                    break
                
                # Get solver info
                solvers = self.db.get_solvers()
                solver = next((s for s in solvers if s['id'] == solver_id), None)
                
                if not solver:
                    logger.error(f"Solver ID {solver_id} not found")
                    failed += 1
                    continue
                
                # Get benchmark info
                benchmarks = self.db.get_benchmarks()
                benchmark = next((b for b in benchmarks if b['id'] == benchmark_id), None)
                
                if not benchmark:
                    logger.error(f"Benchmark ID {benchmark_id} not found")
                    failed += 1
                    continue
                
                # Progress callback
                if progress_callback:
                    progress_callback(
                        completed,
                        total_runs,
                        {
                            'solver': solver['name'],
                            'benchmark': benchmark['filename'],
                            'solver_id': solver_id,
                            'benchmark_id': benchmark_id
                        }
                    )
                
                self.current_run = {
                    'solver': solver['name'],
                    'benchmark': benchmark['filename']
                }
                
                # Run solver
                runner = SolverRunner(
                    timeout_seconds=self.timeout,
                    memory_limit_mb=self.memory_limit
                )
                
                try:
                    result = runner.run_solver(
                        solver['executable_path'],
                        benchmark['filepath']
                    )
                    
                    # Save to database
                    self.db.add_run(
                        experiment_id=experiment_id,
                        solver_id=solver_id,
                        benchmark_id=benchmark_id,
                        **result
                    )
                    
                    completed += 1
                    stats['completed'] = completed
                    
                    # Update counters
                    result_type = result['result']
                    if result_type == 'SAT':
                        stats['sat_count'] += 1
                    elif result_type == 'UNSAT':
                        stats['unsat_count'] += 1
                    elif result_type == 'TIMEOUT':
                        stats['timeout_count'] += 1
                    else:
                        stats['error_count'] += 1
                    
                    # Update experiment progress
                    self.db.update_experiment_status(
                        experiment_id,
                        'running',
                        completed_runs=completed
                    )
                    
                    logger.info(f"Run {completed}/{total_runs} completed: {solver['name']} on {benchmark['filename']} = {result_type}")
                    
                except Exception as e:
                    logger.error(f"Error running solver: {e}")
                    failed += 1
                    stats['failed'] = failed
            
            # Mark experiment as completed
            stats['end_time'] = datetime.now()
            
            final_status = 'completed' if not self.stop_requested else 'stopped'
            self.db.update_experiment_status(
                experiment_id,
                final_status,
                completed_at=stats['end_time'],
                completed_runs=completed,
                failed_runs=failed
            )
            
            logger.info(f"Experiment {experiment_id} finished: {completed}/{total_runs} completed")
            
        except Exception as e:
            logger.error(f"Experiment failed: {e}")
            self.db.update_experiment_status(experiment_id, 'failed')
            raise
        
        return stats
    
    def stop_experiment(self):
        """Request to stop the current experiment"""
        self.stop_requested = True
        logger.info("Stop requested for current experiment")