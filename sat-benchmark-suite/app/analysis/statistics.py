"""
Módulo de análisis estadístico para SAT Solvers
Incluye PAR-2, VBS, Win/Loss matrices, etc.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

class SATStatistics:
    """Clase para calcular estadísticas de competición SAT"""
    
    def __init__(self, df: pd.DataFrame, timeout: float = 5000.0):
        """
        Args:
            df: DataFrame con columnas: solver, benchmark, result, wall_time_seconds
            timeout: Timeout en segundos para cálculo PAR-2
        """
        self.df = df.copy()
        self.timeout = timeout
        
        # Limpiar datos: remover NaN y valores inválidos
        self._clean_data()
    
    def _clean_data(self):
        """Limpia datos inválidos del DataFrame"""
        # Rellenar wall_time_seconds con timeout para timeouts/errores
        mask_invalid = self.df['wall_time_seconds'].isna() | (self.df['wall_time_seconds'] < 0)
        self.df.loc[mask_invalid, 'wall_time_seconds'] = self.timeout
        
        # Asegurar que result no sea None
        self.df['result'] = self.df['result'].fillna('ERROR')
        
        # Convertir tipos numéricos
        numeric_cols = ['wall_time_seconds', 'cpu_time_seconds', 'max_memory_kb', 
                       'conflicts', 'decisions', 'propagations']
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)
        
    def calculate_par2(self) -> pd.Series:
        """
        Calcula PAR-2 score por solver
        PAR-2 = Penalized Average Runtime (2x timeout para timeouts)
        """
        def par2_time(row):
            if pd.isna(row['wall_time_seconds']):
                return 2 * self.timeout
            if row['result'] in ['TIMEOUT', 'MEMOUT', 'ERROR']:
                return 2 * self.timeout
            return row['wall_time_seconds']
        
        self.df['par2_time'] = self.df.apply(par2_time, axis=1)
        
        return self.df.groupby('solver')['par2_time'].mean().sort_values()
    
    def count_solved(self) -> pd.DataFrame:
        """Cuenta instancias resueltas por solver"""
        solved_mask = self.df['result'].isin(['SAT', 'UNSAT'])
        
        stats = pd.DataFrame({
            'total': self.df.groupby('solver').size(),
            'solved': self.df[solved_mask].groupby('solver').size(),
            'sat': self.df[self.df['result'] == 'SAT'].groupby('solver').size(),
            'unsat': self.df[self.df['result'] == 'UNSAT'].groupby('solver').size(),
            'timeout': self.df[self.df['result'] == 'TIMEOUT'].groupby('solver').size(),
            'error': self.df[self.df['result'] == 'ERROR'].groupby('solver').size()
        }).fillna(0).astype(int)
        
        stats['solved_pct'] = (stats['solved'] / stats['total'] * 100).round(2)
        
        return stats.sort_values('solved', ascending=False)
    
    def calculate_virtual_best_solver(self) -> Tuple[pd.DataFrame, str]:
        """
        Calcula el Virtual Best Solver (VBS)
        VBS elige el mejor solver para cada instancia
        """
        # Crear pivot: benchmark x solver con tiempos
        pivot = self.df.pivot_table(
            index='benchmark',
            columns='solver',
            values='wall_time_seconds',
            aggfunc='first'
        )
        
        # Para timeouts/NaN, usar valor alto
        pivot = pivot.fillna(self.timeout * 2)
        
        # Mejor solver por benchmark
        vbs_times = pivot.min(axis=1)
        vbs_solvers = pivot.idxmin(axis=1)
        
        vbs_df = pd.DataFrame({
            'benchmark': vbs_times.index,
            'vbs_solver': vbs_solvers.values,
            'vbs_time': vbs_times.values
        })
        
        # Estadísticas VBS
        vbs_stats = f"""
**Virtual Best Solver (VBS) Statistics:**
- Total Instances: {len(vbs_df)}
- VBS Average Time: {vbs_times.mean():.2f}s
- VBS PAR-2: {vbs_times.mean():.2f}

**Contribution by Solver:**
{vbs_solvers.value_counts().to_string()}
        """
        
        return vbs_df, vbs_stats
    
    def pairwise_comparison(self, solver1: str, solver2: str) -> Dict:
        """
        Compara dos solvers head-to-head
        """
        df1 = self.df[self.df['solver'] == solver1].set_index('benchmark')
        df2 = self.df[self.df['solver'] == solver2].set_index('benchmark')
        
        # Solo benchmarks en común
        common_benchmarks = df1.index.intersection(df2.index)
        
        if len(common_benchmarks) == 0:
            return {
                'total_benchmarks': 0,
                f'{solver1}_wins': 0,
                f'{solver2}_wins': 0,
                'ties': 0,
                'speedup_geometric_mean': 1.0
            }
        
        df1 = df1.loc[common_benchmarks]
        df2 = df2.loc[common_benchmarks]
        
        # Limpiar NaN
        df1['wall_time_seconds'] = df1['wall_time_seconds'].fillna(self.timeout)
        df2['wall_time_seconds'] = df2['wall_time_seconds'].fillna(self.timeout)
        
        # Comparaciones
        wins1 = ((df1['wall_time_seconds'] < df2['wall_time_seconds']) & 
                 (df1['result'].isin(['SAT', 'UNSAT']))).sum()
        
        wins2 = ((df2['wall_time_seconds'] < df1['wall_time_seconds']) & 
                 (df2['result'].isin(['SAT', 'UNSAT']))).sum()
        
        ties = ((df1['wall_time_seconds'] == df2['wall_time_seconds']) & 
                (df1['result'] == df2['result'])).sum()
        
        # Speedup geométrico (evitar división por cero y log de cero)
        time_ratios = df2['wall_time_seconds'] / df1['wall_time_seconds'].replace(0, 0.001)
        time_ratios = time_ratios.replace([np.inf, -np.inf], self.timeout)
        
        speedup = np.exp(np.mean(np.log(time_ratios.clip(0.001, self.timeout))))
        
        return {
            'total_benchmarks': len(common_benchmarks),
            f'{solver1}_wins': int(wins1),
            f'{solver2}_wins': int(wins2),
            'ties': int(ties),
            'speedup_geometric_mean': float(speedup)
        }
    
    def get_cactus_data(self) -> pd.DataFrame:
        """
        Prepara datos para Cactus Plot
        Retorna: DataFrame con columnas [solver, n_solved, time]
        """
        cactus_data = []
        
        for solver in self.df['solver'].unique():
            solver_df = self.df[self.df['solver'] == solver].copy()
            
            # Solo instancias resueltas
            solved_df = solver_df[solver_df['result'].isin(['SAT', 'UNSAT'])].copy()
            
            # Limpiar y ordenar tiempos
            solved_df['wall_time_seconds'] = pd.to_numeric(
                solved_df['wall_time_seconds'], 
                errors='coerce'
            ).fillna(self.timeout)
            
            # Filtrar valores inválidos
            solved_df = solved_df[solved_df['wall_time_seconds'] > 0]
            solved_df = solved_df[solved_df['wall_time_seconds'] < self.timeout * 2]
            
            times = sorted(solved_df['wall_time_seconds'].tolist())
            
            # Agregar puntos para el gráfico
            for i, time in enumerate(times):
                cactus_data.append({
                    'solver': solver,
                    'n_solved': i + 1,
                    'time': time
                })
            
            # Agregar punto final si hay no resueltas
            n_unsolved = len(solver_df) - len(solved_df)
            if n_unsolved > 0 and len(times) > 0:
                cactus_data.append({
                    'solver': solver,
                    'n_solved': len(times),
                    'time': self.timeout
                })
        
        return pd.DataFrame(cactus_data)