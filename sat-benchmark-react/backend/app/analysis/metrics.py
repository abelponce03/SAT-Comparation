"""
Benchmark Metrics Module
========================

Métricas estándar de la literatura de SAT Competition:
- PAR-k (Penalized Average Runtime)
- VBS (Virtual Best Solver)
- Solve Rate / Solved Instances
- Ranking por familia de benchmarks

Referencia: SAT Competition rules (satcompetition.github.io)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SolverResult:
    """Resultado individual de un solver en un benchmark."""
    solver_name: str
    benchmark_name: str
    benchmark_family: str
    wall_time: float  # segundos
    result: str  # SAT, UNSAT, TIMEOUT, ERROR, UNKNOWN
    conflicts: Optional[int] = None
    decisions: Optional[int] = None
    propagations: Optional[int] = None
    restarts: Optional[int] = None
    memory_kb: Optional[int] = None


@dataclass
class SolverSummary:
    """Resumen de rendimiento de un solver."""
    name: str
    solved: int
    total: int
    sat_count: int
    unsat_count: int
    timeout_count: int
    error_count: int
    solve_rate: float
    avg_time_solved: float
    median_time_solved: float
    total_time: float
    par2: float
    par10: float


class BenchmarkMetrics:
    """
    Motor de métricas para comparación rigurosa de SAT solvers.
    
    Implementa las métricas estándar utilizadas en SAT Competition:
    - PAR-k: Penalized Average Runtime, penaliza instancias no resueltas
    - VBS: Virtual Best Solver, cota inferior teórica
    - Solve Rate: fracción de instancias resueltas
    - Rankings por familia de benchmarks
    """
    
    SOLVED_RESULTS = {'SAT', 'UNSAT'}
    PENALIZED_RESULTS = {'TIMEOUT', 'MEMOUT', 'ERROR', 'UNKNOWN'}
    
    def __init__(self, timeout: float = 5000.0):
        self.timeout = timeout
    
    def compute_all_metrics(self, runs: List[Dict]) -> Dict:
        """
        Calcula todas las métricas estándar de benchmarking.
        
        Args:
            runs: Lista de resultados de ejecución (dicts del DB)
            
        Returns:
            Diccionario con todas las métricas calculadas
        """
        if not runs:
            return {"error": "No runs provided"}
        
        df = pd.DataFrame(runs)
        solvers = df['solver_name'].unique().tolist()
        
        return {
            "summary_per_solver": self._solver_summaries(df),
            "par_scores": self._compute_par_scores(df),
            "vbs_analysis": self._compute_vbs(df),
            "solve_matrix": self._compute_solve_matrix(df),
            "family_breakdown": self._compute_family_breakdown(df),
            "ranking": self._compute_ranking(df),
            "timeout_used": self.timeout,
            "num_solvers": len(solvers),
            "num_benchmarks": df['benchmark_name'].nunique(),
            "total_runs": len(df)
        }
    
    def _solver_summaries(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Resumen detallado por solver."""
        summaries = {}
        
        for solver in df['solver_name'].unique():
            sdf = df[df['solver_name'] == solver]
            solved = sdf[sdf['result'].isin(self.SOLVED_RESULTS)]
            times_solved = solved['wall_time_seconds'].dropna()
            
            par2 = self._par_score(sdf, k=2)
            par10 = self._par_score(sdf, k=10)
            
            summaries[solver] = {
                "solved": len(solved),
                "total": len(sdf),
                "sat": int((sdf['result'] == 'SAT').sum()),
                "unsat": int((sdf['result'] == 'UNSAT').sum()),
                "timeout": int((sdf['result'] == 'TIMEOUT').sum()),
                "error": int(sdf['result'].isin(['ERROR', 'UNKNOWN', 'MEMOUT']).sum()),
                "solve_rate": round(len(solved) / len(sdf) * 100, 2) if len(sdf) > 0 else 0,
                "avg_time_solved": round(float(times_solved.mean()), 4) if len(times_solved) > 0 else None,
                "median_time_solved": round(float(times_solved.median()), 4) if len(times_solved) > 0 else None,
                "std_time_solved": round(float(times_solved.std()), 4) if len(times_solved) > 1 else None,
                "min_time": round(float(times_solved.min()), 6) if len(times_solved) > 0 else None,
                "max_time": round(float(times_solved.max()), 4) if len(times_solved) > 0 else None,
                "total_time": round(float(times_solved.sum()), 4) if len(times_solved) > 0 else 0,
                "par2": round(par2, 2),
                "par10": round(par10, 2),
            }
        
        return summaries
    
    def _par_score(self, solver_df: pd.DataFrame, k: int = 2) -> float:
        """
        Calcula PAR-k score.
        
        PAR-k = (1/n) * Σ t_i  donde t_i = wall_time si resuelto, k*timeout si no.
        
        Estándar en SAT Competition. k=2 es el más usado, k=10 más estricto.
        """
        penalty = k * self.timeout
        
        def penalized_time(row):
            if row.get('result') in self.SOLVED_RESULTS and pd.notna(row.get('wall_time_seconds')):
                return row['wall_time_seconds']
            return penalty
        
        times = solver_df.apply(penalized_time, axis=1)
        return float(times.mean())
    
    def _compute_par_scores(self, df: pd.DataFrame) -> Dict:
        """PAR-2 y PAR-10 para todos los solvers con ranking."""
        par2_scores = {}
        par10_scores = {}
        
        for solver in df['solver_name'].unique():
            sdf = df[df['solver_name'] == solver]
            par2_scores[solver] = round(self._par_score(sdf, 2), 2)
            par10_scores[solver] = round(self._par_score(sdf, 10), 2)
        
        # Rankings (menor es mejor)
        par2_ranking = sorted(par2_scores.items(), key=lambda x: x[1])
        par10_ranking = sorted(par10_scores.items(), key=lambda x: x[1])
        
        return {
            "par2": {s: v for s, v in par2_ranking},
            "par10": {s: v for s, v in par10_ranking},
            "par2_ranking": [{"rank": i+1, "solver": s, "score": v} 
                            for i, (s, v) in enumerate(par2_ranking)],
            "par10_ranking": [{"rank": i+1, "solver": s, "score": v} 
                             for i, (s, v) in enumerate(par10_ranking)],
            "best_par2": par2_ranking[0][0] if par2_ranking else None,
            "best_par10": par10_ranking[0][0] if par10_ranking else None,
        }
    
    def _compute_vbs(self, df: pd.DataFrame) -> Dict:
        """
        Virtual Best Solver (VBS) analysis.
        
        El VBS selecciona el mejor solver para cada instancia.
        Es una cota inferior teórica de rendimiento (oracle solver).
        """
        penalty = 2 * self.timeout
        
        # Pivot: benchmark × solver → wall_time
        pivot = df.pivot_table(
            index='benchmark_name',
            columns='solver_name',
            values='wall_time_seconds',
            aggfunc='first'
        )
        
        # Result pivot
        result_pivot = df.pivot_table(
            index='benchmark_name',
            columns='solver_name',
            values='result',
            aggfunc='first'
        )
        
        # Assign penalty for unsolved
        for col in pivot.columns:
            mask = ~result_pivot[col].isin(self.SOLVED_RESULTS)
            pivot.loc[mask, col] = penalty
        
        pivot = pivot.fillna(penalty)
        
        # VBS = min across solvers per benchmark
        vbs_times = pivot.min(axis=1)
        vbs_solvers = pivot.idxmin(axis=1)
        
        # Contribution by solver
        contributions = vbs_solvers.value_counts().to_dict()
        total = sum(contributions.values())
        
        # Solved by at least one solver
        any_solved = (result_pivot.isin(self.SOLVED_RESULTS)).any(axis=1)
        vbs_solved = int(any_solved.sum())
        
        # Individual solver solved counts
        individual_solved = {}
        for solver in df['solver_name'].unique():
            sdf = df[df['solver_name'] == solver]
            individual_solved[solver] = int(sdf['result'].isin(self.SOLVED_RESULTS).sum())
        
        # Gap analysis: how far is each solver from VBS
        gap_analysis = {}
        for solver in pivot.columns:
            solver_times = pivot[solver]
            gap = float((solver_times / vbs_times.replace(0, 0.001)).median())
            gap_analysis[solver] = round(gap, 2)
        
        return {
            "vbs_solved": vbs_solved,
            "vbs_par2": round(float(vbs_times.mean()), 4),
            "total_benchmarks": len(pivot),
            "individual_solved": individual_solved,
            "contributions": [
                {
                    "solver": s,
                    "unique_wins": c,
                    "percentage": round(c / total * 100, 1) if total > 0 else 0
                }
                for s, c in sorted(contributions.items(), key=lambda x: -x[1])
            ],
            "gap_to_vbs": gap_analysis,
            "marginal_value": vbs_solved - max(individual_solved.values()) if individual_solved else 0
        }
    
    def _compute_solve_matrix(self, df: pd.DataFrame) -> Dict:
        """
        Matriz de resolución: qué solver resuelve qué benchmark.
        Identifica instancias únicamente resueltas por un solo solver.
        """
        result_pivot = df.pivot_table(
            index='benchmark_name',
            columns='solver_name',
            values='result',
            aggfunc='first'
        )
        
        solved_matrix = result_pivot.isin(self.SOLVED_RESULTS)
        
        # Uniquely solved per solver
        unique_solved = {}
        for solver in solved_matrix.columns:
            others = solved_matrix.drop(columns=[solver])
            mask = solved_matrix[solver] & ~others.any(axis=1)
            unique_solved[solver] = int(mask.sum())
        
        # Commonly solved by all
        all_solved = int(solved_matrix.all(axis=1).sum())
        
        # Solved by none
        none_solved = int((~solved_matrix.any(axis=1)).sum())
        
        return {
            "unique_solved": unique_solved,
            "all_solved": all_solved,
            "none_solved": none_solved,
            "total_benchmarks": len(result_pivot)
        }
    
    def _compute_family_breakdown(self, df: pd.DataFrame) -> Dict:
        """Análisis por familia de benchmarks."""
        families = {}
        
        for family in df['benchmark_family'].dropna().unique():
            fdf = df[df['benchmark_family'] == family]
            family_benchmarks = fdf['benchmark_name'].nunique()
            
            solver_stats = {}
            for solver in fdf['solver_name'].unique():
                sdf = fdf[fdf['solver_name'] == solver]
                solved = sdf[sdf['result'].isin(self.SOLVED_RESULTS)]
                
                solver_stats[solver] = {
                    "solved": len(solved),
                    "total": len(sdf),
                    "solve_rate": round(len(solved) / len(sdf) * 100, 2) if len(sdf) > 0 else 0,
                    "par2": round(self._par_score(sdf, 2), 2),
                    "avg_time": round(float(solved['wall_time_seconds'].mean()), 4) if len(solved) > 0 else None,
                }
            
            # Best solver per family
            best = min(solver_stats.items(), key=lambda x: x[1]['par2'])
            
            families[family] = {
                "num_benchmarks": family_benchmarks,
                "solvers": solver_stats,
                "best_solver": best[0],
                "best_par2": best[1]['par2']
            }
        
        return families
    
    def _compute_ranking(self, df: pd.DataFrame) -> List[Dict]:
        """Ranking compuesto usando múltiples métricas."""
        rankings = []
        
        for solver in df['solver_name'].unique():
            sdf = df[df['solver_name'] == solver]
            solved = sdf[sdf['result'].isin(self.SOLVED_RESULTS)]
            
            rankings.append({
                "solver": solver,
                "solved": len(solved),
                "par2": round(self._par_score(sdf, 2), 2),
                "par10": round(self._par_score(sdf, 10), 2),
                "solve_rate": round(len(solved) / len(sdf) * 100, 2) if len(sdf) > 0 else 0,
                "avg_time": round(float(solved['wall_time_seconds'].mean()), 4) if len(solved) > 0 else None,
            })
        
        # Sort by: 1) solved (desc), 2) PAR-2 (asc)
        rankings.sort(key=lambda x: (-x['solved'], x['par2']))
        
        for i, r in enumerate(rankings):
            r['rank'] = i + 1
        
        return rankings
    
    def get_paired_times(self, df: pd.DataFrame, solver1: str, solver2: str,
                         penalize_unsolved: bool = True) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Obtiene tiempos pareados para dos solvers en benchmarks comunes.
        
        Args:
            df: DataFrame con las ejecuciones
            solver1, solver2: nombres de los solvers
            penalize_unsolved: si True, usa penalty para no resueltos
            
        Returns:
            (times1, times2, benchmark_names) - arrays pareados
        """
        penalty = 2 * self.timeout
        
        df1 = df[df['solver_name'] == solver1].set_index('benchmark_name')
        df2 = df[df['solver_name'] == solver2].set_index('benchmark_name')
        
        common = df1.index.intersection(df2.index)
        
        if penalize_unsolved:
            t1 = []
            t2 = []
            for bench in common:
                r1 = df1.loc[bench]
                r2 = df2.loc[bench]
                # Handle potential duplicates
                if isinstance(r1, pd.DataFrame):
                    r1 = r1.iloc[0]
                if isinstance(r2, pd.DataFrame):
                    r2 = r2.iloc[0]
                    
                time1 = r1['wall_time_seconds'] if r1['result'] in self.SOLVED_RESULTS else penalty
                time2 = r2['wall_time_seconds'] if r2['result'] in self.SOLVED_RESULTS else penalty
                t1.append(float(time1) if pd.notna(time1) else penalty)
                t2.append(float(time2) if pd.notna(time2) else penalty)
            
            return np.array(t1), np.array(t2), list(common)
        else:
            # Only commonly solved
            solved1 = df1[df1['result'].isin(self.SOLVED_RESULTS)]
            solved2 = df2[df2['result'].isin(self.SOLVED_RESULTS)]
            common_solved = solved1.index.intersection(solved2.index)
            
            t1 = solved1.loc[common_solved, 'wall_time_seconds'].values.astype(float)
            t2 = solved2.loc[common_solved, 'wall_time_seconds'].values.astype(float)
            
            return t1, t2, list(common_solved)
