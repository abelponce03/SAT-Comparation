"""
Bootstrap Confidence Interval Engine
=====================================

Implementa estimación de incertidumbre por bootstrap no paramétrico.
Esencial para reportar resultados con significancia estadística.

Métodos:
- Bootstrap percentil
- Bootstrap BCa (Bias-Corrected and Accelerated)
- Bootstrap para diferencias de medias

Referencia:
  Efron & Tibshirani, "An Introduction to the Bootstrap", 1993
  Davison & Hinkley, "Bootstrap Methods and their Application", 1997
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Callable, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class BootstrapResult:
    """Resultado de un análisis bootstrap."""
    statistic: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    n_bootstrap: int
    std_error: float
    bias: float
    method: str
    
    def to_dict(self) -> Dict:
        return {
            "statistic": round(self.statistic, 6),
            "ci_lower": round(self.ci_lower, 6),
            "ci_upper": round(self.ci_upper, 6),
            "confidence_level": self.confidence_level,
            "n_bootstrap": self.n_bootstrap,
            "std_error": round(self.std_error, 6),
            "bias": round(self.bias, 6),
            "method": self.method,
            "ci_width": round(self.ci_upper - self.ci_lower, 6)
        }


class BootstrapEngine:
    """
    Motor de Bootstrap para estimación de intervalos de confianza.
    
    Permite calcular ICs para cualquier estadístico (media, mediana,
    PAR-2, diferencias, etc.) sin asumir distribución paramétrica.
    
    Uso:
        engine = BootstrapEngine(n_bootstrap=10000, seed=42)
        result = engine.ci_mean(data, confidence=0.95)
    """
    
    def __init__(self, n_bootstrap: int = 10000, seed: int = 42):
        """
        Args:
            n_bootstrap: Número de muestras bootstrap (≥10000 recomendado)
            seed: Semilla para reproducibilidad
        """
        self.n_bootstrap = n_bootstrap
        self.rng = np.random.RandomState(seed)
    
    def _bootstrap_samples(self, data: np.ndarray) -> np.ndarray:
        """Genera muestras bootstrap (remuestreo con reemplazo)."""
        n = len(data)
        indices = self.rng.randint(0, n, size=(self.n_bootstrap, n))
        return data[indices]
    
    def percentile_ci(self, data: np.ndarray, 
                      statistic_fn: Callable = np.mean,
                      confidence: float = 0.95) -> BootstrapResult:
        """
        Bootstrap percentil estándar.
        
        Método más simple. Calcula el estadístico en cada muestra bootstrap
        y toma los percentiles como límites del IC.
        
        Args:
            data: array de observaciones
            statistic_fn: función que calcula el estadístico
            confidence: nivel de confianza (0.95 = 95%)
        """
        data = np.asarray(data, dtype=float)
        observed = float(statistic_fn(data))
        
        # Bootstrap
        samples = self._bootstrap_samples(data)
        boot_stats = np.array([statistic_fn(s) for s in samples])
        
        # Percentiles
        alpha = (1 - confidence) / 2
        ci_lower = float(np.percentile(boot_stats, alpha * 100))
        ci_upper = float(np.percentile(boot_stats, (1 - alpha) * 100))
        
        return BootstrapResult(
            statistic=observed,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence_level=confidence,
            n_bootstrap=self.n_bootstrap,
            std_error=float(np.std(boot_stats, ddof=1)),
            bias=float(np.mean(boot_stats) - observed),
            method="percentile"
        )
    
    def bca_ci(self, data: np.ndarray,
               statistic_fn: Callable = np.mean,
               confidence: float = 0.95) -> BootstrapResult:
        """
        Bootstrap BCa (Bias-Corrected and Accelerated).
        
        Mejora sobre el método percentil, corrige sesgo y asimetría.
        Recomendado para muestras pequeñas o distribuciones sesgadas.
        
        Ref: Efron, "Better Bootstrap Confidence Intervals", JASA 1987
        """
        from scipy import stats as scipy_stats
        
        data = np.asarray(data, dtype=float)
        n = len(data)
        observed = float(statistic_fn(data))
        
        # Bootstrap statistics
        samples = self._bootstrap_samples(data)
        boot_stats = np.array([statistic_fn(s) for s in samples])
        
        # Bias correction factor (z0)
        prop_less = np.mean(boot_stats < observed)
        prop_less = np.clip(prop_less, 1e-10, 1 - 1e-10)
        z0 = scipy_stats.norm.ppf(prop_less)
        
        # Acceleration factor (a) via jackknife
        jackknife_stats = np.zeros(n)
        for i in range(n):
            jack_sample = np.delete(data, i)
            jackknife_stats[i] = statistic_fn(jack_sample)
        
        jack_mean = np.mean(jackknife_stats)
        diff = jack_mean - jackknife_stats
        
        numerator = np.sum(diff ** 3)
        denominator = 6 * (np.sum(diff ** 2)) ** 1.5
        
        if abs(denominator) < 1e-10:
            a = 0.0
        else:
            a = numerator / denominator
        
        # Adjusted percentiles
        alpha = (1 - confidence) / 2
        z_alpha = scipy_stats.norm.ppf(alpha)
        z_1_alpha = scipy_stats.norm.ppf(1 - alpha)
        
        # BCa adjusted quantiles
        def bca_quantile(z_score):
            adj = z0 + (z0 + z_score) / (1 - a * (z0 + z_score))
            return scipy_stats.norm.cdf(adj)
        
        try:
            q_lower = bca_quantile(z_alpha)
            q_upper = bca_quantile(z_1_alpha)
            
            # Clamp to valid range
            q_lower = np.clip(q_lower, 0.001, 0.999)
            q_upper = np.clip(q_upper, 0.001, 0.999)
            
            ci_lower = float(np.percentile(boot_stats, q_lower * 100))
            ci_upper = float(np.percentile(boot_stats, q_upper * 100))
        except (ValueError, FloatingPointError):
            # Fallback to percentile method
            ci_lower = float(np.percentile(boot_stats, alpha * 100))
            ci_upper = float(np.percentile(boot_stats, (1 - alpha) * 100))
        
        return BootstrapResult(
            statistic=observed,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence_level=confidence,
            n_bootstrap=self.n_bootstrap,
            std_error=float(np.std(boot_stats, ddof=1)),
            bias=float(np.mean(boot_stats) - observed),
            method="BCa"
        )
    
    def ci_mean(self, data: np.ndarray, confidence: float = 0.95,
                method: str = "bca") -> BootstrapResult:
        """IC para la media."""
        fn = self.bca_ci if method == "bca" else self.percentile_ci
        return fn(data, np.mean, confidence)
    
    def ci_median(self, data: np.ndarray, confidence: float = 0.95,
                  method: str = "bca") -> BootstrapResult:
        """IC para la mediana."""
        fn = self.bca_ci if method == "bca" else self.percentile_ci
        return fn(data, np.median, confidence)
    
    def ci_par2(self, times: np.ndarray, results: np.ndarray,
                timeout: float = 5000.0, confidence: float = 0.95) -> BootstrapResult:
        """
        IC para PAR-2 score vía bootstrap.
        
        Remuestrea pares (tiempo, resultado) y calcula PAR-2 en cada muestra.
        """
        penalty = 2 * timeout
        n = len(times)
        
        # Compute penalized times
        penalized = np.where(
            np.isin(results, ['SAT', 'UNSAT']),
            times,
            penalty
        )
        
        observed_par2 = float(np.mean(penalized))
        
        # Bootstrap
        boot_par2 = np.zeros(self.n_bootstrap)
        for b in range(self.n_bootstrap):
            idx = self.rng.randint(0, n, n)
            boot_par2[b] = np.mean(penalized[idx])
        
        alpha = (1 - confidence) / 2
        
        return BootstrapResult(
            statistic=observed_par2,
            ci_lower=float(np.percentile(boot_par2, alpha * 100)),
            ci_upper=float(np.percentile(boot_par2, (1 - alpha) * 100)),
            confidence_level=confidence,
            n_bootstrap=self.n_bootstrap,
            std_error=float(np.std(boot_par2, ddof=1)),
            bias=float(np.mean(boot_par2) - observed_par2),
            method="percentile_par2"
        )
    
    def ci_difference(self, data1: np.ndarray, data2: np.ndarray,
                      confidence: float = 0.95) -> BootstrapResult:
        """
        IC para la diferencia de medias (solver1 - solver2).
        
        Útil para determinar si la diferencia es significativa.
        Si el IC no contiene 0, la diferencia es significativa al nivel dado.
        
        Args:
            data1: tiempos del solver 1
            data2: tiempos del solver 2 (pareados, mismo orden de benchmarks)
        """
        assert len(data1) == len(data2), "Arrays must be paired (same length)"
        
        diff = data1 - data2
        observed = float(np.mean(diff))
        
        n = len(diff)
        boot_diffs = np.zeros(self.n_bootstrap)
        for b in range(self.n_bootstrap):
            idx = self.rng.randint(0, n, n)
            boot_diffs[b] = np.mean(diff[idx])
        
        alpha = (1 - confidence) / 2
        
        return BootstrapResult(
            statistic=observed,
            ci_lower=float(np.percentile(boot_diffs, alpha * 100)),
            ci_upper=float(np.percentile(boot_diffs, (1 - alpha) * 100)),
            confidence_level=confidence,
            n_bootstrap=self.n_bootstrap,
            std_error=float(np.std(boot_diffs, ddof=1)),
            bias=float(np.mean(boot_diffs) - observed),
            method="paired_difference"
        )
    
    def ci_solve_rate(self, solved_count: int, total: int,
                      confidence: float = 0.95) -> BootstrapResult:
        """IC para tasa de resolución (proporción binomial)."""
        data = np.concatenate([
            np.ones(solved_count),
            np.zeros(total - solved_count)
        ])
        return self.percentile_ci(data, np.mean, confidence)
    
    def full_solver_bootstrap(self, runs: List[Dict], timeout: float = 5000.0,
                               confidence: float = 0.95) -> Dict:
        """
        Bootstrap completo para todos los solvers.
        
        Calcula ICs para: media, mediana, PAR-2, solve rate de cada solver.
        
        Args:
            runs: ejecuciones del experimento
            timeout: timeout del experimento
            confidence: nivel de confianza
            
        Returns:
            Diccionario con ICs por solver y por métrica
        """
        df = pd.DataFrame(runs)
        results = {}
        
        for solver in df['solver_name'].unique():
            sdf = df[df['solver_name'] == solver]
            solved = sdf[sdf['result'].isin(['SAT', 'UNSAT'])]
            times = solved['wall_time_seconds'].dropna().values
            
            solver_results = {}
            
            if len(times) >= 3:
                solver_results['mean_time'] = self.ci_mean(times, confidence).to_dict()
                solver_results['median_time'] = self.ci_median(times, confidence).to_dict()
            
            # PAR-2 bootstrap
            all_times = sdf['wall_time_seconds'].fillna(timeout).values
            all_results = sdf['result'].values
            solver_results['par2'] = self.ci_par2(
                all_times, all_results, timeout, confidence
            ).to_dict()
            
            # Solve rate
            solver_results['solve_rate'] = self.ci_solve_rate(
                len(solved), len(sdf), confidence
            ).to_dict()
            
            results[solver] = solver_results
        
        # Pairwise difference CIs
        solvers = df['solver_name'].unique()
        if len(solvers) >= 2:
            pairwise = {}
            for i, s1 in enumerate(solvers):
                for s2 in solvers[i+1:]:
                    # Get paired times
                    df1 = df[df['solver_name'] == s1].set_index('benchmark_name')
                    df2 = df[df['solver_name'] == s2].set_index('benchmark_name')
                    common = df1.index.intersection(df2.index)
                    
                    if len(common) >= 3:
                        t1 = df1.loc[common, 'wall_time_seconds'].values.astype(float)
                        t2 = df2.loc[common, 'wall_time_seconds'].values.astype(float)
                        
                        diff_result = self.ci_difference(t1, t2, confidence)
                        key = f"{s1}_vs_{s2}"
                        pairwise[key] = {
                            **diff_result.to_dict(),
                            "significant": not (diff_result.ci_lower <= 0 <= diff_result.ci_upper),
                            "faster_solver": s1 if diff_result.statistic < 0 else s2,
                            "n_common": len(common)
                        }
            
            results["pairwise_differences"] = pairwise
        
        return {
            "bootstrap_results": results,
            "confidence_level": confidence,
            "n_bootstrap": self.n_bootstrap,
            "method": "BCa for individual, percentile for paired differences"
        }
