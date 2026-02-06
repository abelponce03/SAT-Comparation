"""
Statistical Tests Module for SAT Solver Comparison
====================================================

Tests estadísticos rigurosos para comparación de solvers:

Para 2 solvers:
- Wilcoxon signed-rank test (pareado, no paramétrico) [RECOMENDADO]
- Mann-Whitney U test (independiente, no paramétrico)
- Sign test (robusto ante outliers)

Para k≥3 solvers:
- Friedman test (ANOVA no paramétrico para k tratamientos)
- Post-hoc: Nemenyi test (comparaciones múltiples)
- Post-hoc: Conover test  

Corrección por comparaciones múltiples:
- Bonferroni (más conservador)
- Holm step-down (más potente que Bonferroni)
- Benjamini-Hochberg (controla FDR, menos conservador)

Medidas de efecto:
- Cohen's d (paramétrico)
- Rank-biserial correlation (no paramétrico)
- Vargha-Delaney A measure

Referencias:
  [1] Demšar, "Statistical Comparisons of Classifiers over Multiple Data Sets", JMLR 2006
  [2] García et al., "Advanced nonparametric tests for multiple comparisons", 2010
  [3] Arcuri & Briand, "A practical guide for statistical tests", ICSE 2011
"""

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
import warnings

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Resultado de un test estadístico."""
    test_name: str
    statistic: float
    p_value: float
    significant_005: bool
    significant_001: bool
    effect_size: Optional[float] = None
    effect_interpretation: Optional[str] = None
    description: str = ""
    recommendation: str = ""
    
    def to_dict(self) -> Dict:
        d = {
            "test_name": self.test_name,
            "statistic": round(self.statistic, 6),
            "p_value": round(self.p_value, 6),
            "significant_005": self.significant_005,
            "significant_001": self.significant_001,
            "description": self.description,
            "recommendation": self.recommendation,
        }
        if self.effect_size is not None:
            d["effect_size"] = round(self.effect_size, 4)
            d["effect_interpretation"] = self.effect_interpretation
        return d


class StatisticalTestSuite:
    """
    Suite completa de tests estadísticos para comparación de SAT solvers.
    
    Workflow recomendado (Demšar 2006):
    1. Para 2 solvers: Wilcoxon signed-rank test
    2. Para k≥3: Friedman test → si significativo → post-hoc Nemenyi
    3. Siempre reportar tamaño de efecto
    4. Aplicar corrección por comparaciones múltiples
    """
    
    # ==================== 2-SOLVER TESTS ====================
    
    def wilcoxon_test(self, times1: np.ndarray, times2: np.ndarray) -> TestResult:
        """
        Wilcoxon Signed-Rank Test.
        
        TEST RECOMENDADO para comparación pareada de 2 solvers (Demšar 2006).
        - No paramétrico: no asume normalidad
        - Pareado: usa las diferencias por instancia
        - H0: la distribución de diferencias es simétrica alrededor de 0
        
        Requiere: n ≥ 6 pares con diferencias no nulas.
        """
        # Remove tied pairs (difference = 0) 
        diff = times1 - times2
        nonzero = diff != 0
        
        if nonzero.sum() < 6:
            return TestResult(
                test_name="Wilcoxon Signed-Rank",
                statistic=0.0,
                p_value=1.0,
                significant_005=False,
                significant_001=False,
                description="Insufficient non-tied pairs (need ≥ 6)",
                recommendation="Collect more data or use sign test"
            )
        
        try:
            stat, p = scipy_stats.wilcoxon(times1, times2, alternative='two-sided')
            
            # Rank-biserial correlation as effect size
            n = len(times1)
            r = 1 - (2 * stat) / (n * (n + 1) / 2)
            effect_interp = self._interpret_r(abs(r))
            
            return TestResult(
                test_name="Wilcoxon Signed-Rank",
                statistic=float(stat),
                p_value=float(p),
                significant_005=bool(p < 0.05),
                significant_001=bool(p < 0.01),
                effect_size=float(r),
                effect_interpretation=effect_interp,
                description="Non-parametric paired test. H0: no difference in performance.",
                recommendation="Preferred test for 2-solver comparison on same benchmark set."
            )
        except Exception as e:
            return TestResult(
                test_name="Wilcoxon Signed-Rank",
                statistic=0.0, p_value=1.0,
                significant_005=False, significant_001=False,
                description=f"Error: {str(e)}"
            )
    
    def mann_whitney_test(self, times1: np.ndarray, times2: np.ndarray) -> TestResult:
        """
        Mann-Whitney U Test.
        
        Test no paramétrico para muestras independientes.
        Útil cuando los solvers se ejecutan en conjuntos diferentes de benchmarks.
        """
        try:
            stat, p = scipy_stats.mannwhitneyu(times1, times2, alternative='two-sided')
            
            # Vargha-Delaney A measure as effect size
            n1, n2 = len(times1), len(times2)
            a_measure = stat / (n1 * n2)
            effect_interp = self._interpret_a_measure(a_measure)
            
            return TestResult(
                test_name="Mann-Whitney U",
                statistic=float(stat),
                p_value=float(p),
                significant_005=bool(p < 0.05),
                significant_001=bool(p < 0.01),
                effect_size=float(a_measure),
                effect_interpretation=effect_interp,
                description="Non-parametric test for independent samples.",
                recommendation="Use when solvers run on different benchmark subsets."
            )
        except Exception as e:
            return TestResult(
                test_name="Mann-Whitney U",
                statistic=0.0, p_value=1.0,
                significant_005=False, significant_001=False,
                description=f"Error: {str(e)}"
            )
    
    def sign_test(self, times1: np.ndarray, times2: np.ndarray) -> TestResult:
        """
        Sign Test.
        
        El test más robusto: solo usa el signo de las diferencias.
        Menos potente que Wilcoxon pero más robusto ante outliers.
        """
        diff = times1 - times2
        n_positive = int(np.sum(diff > 0))  # solver1 slower
        n_negative = int(np.sum(diff < 0))  # solver1 faster
        n_nonzero = n_positive + n_negative
        
        if n_nonzero == 0:
            return TestResult(
                test_name="Sign Test",
                statistic=0.0, p_value=1.0,
                significant_005=False, significant_001=False,
                description="No differences found"
            )
        
        # Binomial test: P(X >= max(n+, n-)) under H0: p=0.5
        p = float(scipy_stats.binom_test(max(n_positive, n_negative), n_nonzero, 0.5))
        
        return TestResult(
            test_name="Sign Test",
            statistic=float(max(n_positive, n_negative)),
            p_value=p,
            significant_005=bool(p < 0.05),
            significant_001=bool(p < 0.01),
            description=f"Solver1 slower in {n_positive} cases, faster in {n_negative} cases.",
            recommendation="Most robust test, use when data has extreme outliers."
        )
    
    # ==================== k-SOLVER TESTS (k ≥ 3) ====================
    
    def friedman_test(self, time_matrix: pd.DataFrame) -> TestResult:
        """
        Friedman Test.
        
        ANOVA no paramétrico para k ≥ 3 tratamientos (solvers) medidos
        repetidamente (en los mismos benchmarks).
        
        Args:
            time_matrix: DataFrame con benchmarks como filas, solvers como columnas.
                         Valores = tiempos (o PAR-2 penalizados).
        
        H0: Todos los solvers tienen el mismo rendimiento medio.
        Si se rechaza → proceder con test post-hoc (Nemenyi).
        """
        k = time_matrix.shape[1]  # number of solvers
        n = time_matrix.shape[0]  # number of benchmarks
        
        if k < 3:
            return TestResult(
                test_name="Friedman",
                statistic=0.0, p_value=1.0,
                significant_005=False, significant_001=False,
                description="Need ≥ 3 solvers for Friedman test"
            )
        
        if n < 3:
            return TestResult(
                test_name="Friedman",
                statistic=0.0, p_value=1.0,
                significant_005=False, significant_001=False,
                description="Need ≥ 3 benchmarks for Friedman test"
            )
        
        try:
            # Compute ranks per benchmark (row)
            ranks = time_matrix.rank(axis=1, method='average')
            avg_ranks = ranks.mean(axis=0)
            
            # Friedman statistic
            stat, p = scipy_stats.friedmanchisquare(
                *[time_matrix[col].values for col in time_matrix.columns]
            )
            
            # Kendall's W (effect size for Friedman)
            w = stat / (n * (k - 1))
            
            return TestResult(
                test_name="Friedman",
                statistic=float(stat),
                p_value=float(p),
                significant_005=bool(p < 0.05),
                significant_001=bool(p < 0.01),
                effect_size=float(w),
                effect_interpretation=self._interpret_w(w),
                description=f"Non-parametric ANOVA for {k} solvers on {n} benchmarks. "
                           f"Average ranks: {dict(avg_ranks.round(3))}",
                recommendation="If significant, proceed with Nemenyi post-hoc test."
            )
        except Exception as e:
            return TestResult(
                test_name="Friedman",
                statistic=0.0, p_value=1.0,
                significant_005=False, significant_001=False,
                description=f"Error: {str(e)}"
            )
    
    def nemenyi_post_hoc(self, time_matrix: pd.DataFrame, 
                         alpha: float = 0.05) -> Dict:
        """
        Nemenyi Post-Hoc Test.
        
        Comparaciones por pares tras un Friedman significativo.
        Análogo a Tukey HSD pero basado en rangos.
        
        La diferencia es significativa si |R_i - R_j| > CD
        donde CD = q_α * sqrt(k(k+1) / (6n))
        
        Ref: Demšar 2006, Section 3.2
        """
        k = time_matrix.shape[1]
        n = time_matrix.shape[0]
        
        # Compute average ranks
        ranks = time_matrix.rank(axis=1, method='average')
        avg_ranks = ranks.mean(axis=0)
        
        # Critical difference
        # q_alpha values for Nemenyi test (from studentized range / sqrt(2))
        # Using approximation via scipy
        from scipy.stats import studentized_range
        q_alpha = studentized_range.ppf(1 - alpha, k, np.inf) / np.sqrt(2)
        cd = q_alpha * np.sqrt(k * (k + 1) / (6 * n))
        
        # Pairwise comparisons
        solvers = list(time_matrix.columns)
        comparisons = []
        
        for i, s1 in enumerate(solvers):
            for j, s2 in enumerate(solvers):
                if i >= j:
                    continue
                
                rank_diff = abs(float(avg_ranks[s1]) - float(avg_ranks[s2]))
                significant = rank_diff > cd
                
                comparisons.append({
                    "solver1": s1,
                    "solver2": s2,
                    "rank1": round(float(avg_ranks[s1]), 3),
                    "rank2": round(float(avg_ranks[s2]), 3),
                    "rank_difference": round(rank_diff, 3),
                    "critical_difference": round(cd, 3),
                    "significant": bool(significant),
                    "better_solver": s1 if avg_ranks[s1] < avg_ranks[s2] else s2
                })
        
        return {
            "test_name": "Nemenyi Post-Hoc",
            "alpha": alpha,
            "critical_difference": round(cd, 3),
            "average_ranks": {s: round(float(r), 3) for s, r in avg_ranks.items()},
            "ranking": sorted(
                [(s, float(r)) for s, r in avg_ranks.items()],
                key=lambda x: x[1]
            ),
            "comparisons": comparisons,
            "description": (
                f"Critical difference CD = {cd:.3f}. "
                f"Pairs with |R_i - R_j| > CD are significantly different."
            )
        }
    
    # ==================== MULTIPLE COMPARISON CORRECTIONS ====================
    
    def correct_pvalues(self, p_values: List[float], 
                        method: str = "holm") -> Dict:
        """
        Corrección por comparaciones múltiples.
        
        Métodos:
        - bonferroni: p_adj = p * m (más conservador)
        - holm: step-down Bonferroni (más potente)
        - bh: Benjamini-Hochberg (controla FDR, menos conservador)
        
        Args:
            p_values: lista de p-values a corregir
            method: 'bonferroni', 'holm', o 'bh'
        """
        m = len(p_values)
        p_array = np.array(p_values)
        
        if method == "bonferroni":
            adjusted = np.minimum(p_array * m, 1.0)
            
        elif method == "holm":
            # Holm step-down: order p-values, multiply by (m - rank + 1)
            order = np.argsort(p_array)
            adjusted = np.zeros(m)
            for i, idx in enumerate(order):
                adjusted[idx] = min(p_array[idx] * (m - i), 1.0)
            # Enforce monotonicity
            for i in range(1, len(order)):
                adjusted[order[i]] = max(adjusted[order[i]], adjusted[order[i-1]])
                
        elif method == "bh":
            # Benjamini-Hochberg: controls False Discovery Rate
            order = np.argsort(p_array)
            adjusted = np.zeros(m)
            for i, idx in enumerate(order):
                adjusted[idx] = min(p_array[idx] * m / (i + 1), 1.0)
            # Enforce monotonicity (from largest to smallest)
            for i in range(len(order) - 2, -1, -1):
                adjusted[order[i]] = min(adjusted[order[i]], adjusted[order[i+1]])
        else:
            raise ValueError(f"Unknown method: {method}. Use 'bonferroni', 'holm', or 'bh'.")
        
        return {
            "method": method,
            "original_pvalues": [round(p, 6) for p in p_values],
            "adjusted_pvalues": [round(float(p), 6) for p in adjusted],
            "significant_005": [bool(p < 0.05) for p in adjusted],
            "significant_001": [bool(p < 0.01) for p in adjusted],
            "description": {
                "bonferroni": "Most conservative. Controls familywise error rate (FWER). Multiply each p by m.",
                "holm": "Step-down Bonferroni. More powerful than Bonferroni, still controls FWER.",
                "bh": "Benjamini-Hochberg. Controls False Discovery Rate (FDR). Least conservative."
            }[method]
        }
    
    # ==================== EFFECT SIZE MEASURES ====================
    
    def cohens_d(self, times1: np.ndarray, times2: np.ndarray) -> Dict:
        """
        Cohen's d para muestras pareadas.
        
        d = mean(diff) / std(diff)
        Interpretación: |d| < 0.2 negligible, < 0.5 small, < 0.8 medium, ≥ 0.8 large
        """
        diff = times1 - times2
        d = float(np.mean(diff) / np.std(diff, ddof=1)) if np.std(diff, ddof=1) > 0 else 0.0
        
        return {
            "cohens_d": round(d, 4),
            "abs_d": round(abs(d), 4),
            "interpretation": self._interpret_d(abs(d)),
            "direction": "solver1 faster" if d < 0 else "solver2 faster",
            "description": "Standardized mean difference. |d|<0.2: negligible, <0.5: small, <0.8: medium, ≥0.8: large"
        }
    
    def vargha_delaney(self, times1: np.ndarray, times2: np.ndarray) -> Dict:
        """
        Vargha-Delaney A measure.
        
        Probabilidad de que solver1 sea más rápido que solver2.
        A = 0.5 → no difference, A > 0.5 → solver1 better, A < 0.5 → solver2 better.
        
        Recomendado por Arcuri & Briand (2011) para benchmarking de algoritmos.
        """
        n1, n2 = len(times1), len(times2)
        
        # Count: for each pair (t1, t2), count wins and ties
        comparisons = 0
        for t1 in times1:
            for t2 in times2:
                if t1 < t2:
                    comparisons += 1
                elif t1 == t2:
                    comparisons += 0.5
        
        a = comparisons / (n1 * n2)
        
        # Interpretation
        a_diff = abs(a - 0.5)
        if a_diff < 0.06:
            interp = "negligible"
        elif a_diff < 0.14:
            interp = "small"
        elif a_diff < 0.21:
            interp = "medium"
        else:
            interp = "large"
        
        return {
            "A_measure": round(float(a), 4),
            "interpretation": interp,
            "direction": "solver1 better" if a > 0.5 else ("solver2 better" if a < 0.5 else "equal"),
            "description": (
                "P(solver1 < solver2). A=0.5: no difference. "
                "Thresholds: |A-0.5| < 0.06: negligible, <0.14: small, <0.21: medium, ≥0.21: large"
            )
        }
    
    # ==================== NORMALITY CHECK ====================
    
    def normality_tests(self, data: np.ndarray, name: str = "data") -> Dict:
        """
        Tests de normalidad para validar supuestos de tests paramétricos.
        
        - Shapiro-Wilk: mejor para n < 50
        - D'Agostino-Pearson: mejor para n ≥ 20
        """
        results = {"sample_name": name, "n": len(data)}
        
        if len(data) < 3:
            results["error"] = "Need ≥ 3 observations"
            return results
        
        # Shapiro-Wilk
        try:
            w, p = scipy_stats.shapiro(data[:min(50, len(data))])
            results["shapiro_wilk"] = {
                "statistic": round(float(w), 6),
                "p_value": round(float(p), 6),
                "is_normal": bool(p > 0.05),
                "description": "Best for n < 50. H0: data is normally distributed."
            }
        except Exception as e:
            results["shapiro_wilk"] = {"error": str(e)}
        
        # D'Agostino-Pearson
        if len(data) >= 20:
            try:
                stat, p = scipy_stats.normaltest(data)
                results["dagostino"] = {
                    "statistic": round(float(stat), 6),
                    "p_value": round(float(p), 6),
                    "is_normal": bool(p > 0.05),
                    "description": "Based on skewness and kurtosis. Best for n ≥ 20."
                }
            except Exception as e:
                results["dagostino"] = {"error": str(e)}
        
        # Descriptive stats
        results["skewness"] = round(float(scipy_stats.skew(data)), 4)
        results["kurtosis"] = round(float(scipy_stats.kurtosis(data)), 4)
        
        # Recommendation
        is_normal = results.get("shapiro_wilk", {}).get("is_normal", False)
        results["recommendation"] = (
            "Data appears normally distributed → parametric tests are valid."
            if is_normal else
            "Data is NOT normally distributed → use non-parametric tests (Wilcoxon, Friedman)."
        )
        
        return results
    
    # ==================== COMPREHENSIVE ANALYSIS ====================
    
    def full_pairwise_analysis(self, times1: np.ndarray, times2: np.ndarray,
                                solver1_name: str, solver2_name: str) -> Dict:
        """
        Análisis completo de comparación entre dos solvers.
        
        Ejecuta todos los tests relevantes, verifica supuestos,
        y proporciona interpretación automatizada.
        """
        results = {
            "solvers": {"solver1": solver1_name, "solver2": solver2_name},
            "n_instances": len(times1),
        }
        
        # 1. Normality check (on differences)
        diff = times1 - times2
        results["normality"] = self.normality_tests(diff, "time_differences")
        
        # 2. Primary test: Wilcoxon (recommended)
        results["wilcoxon"] = self.wilcoxon_test(times1, times2).to_dict()
        
        # 3. Alternative tests
        results["mann_whitney"] = self.mann_whitney_test(times1, times2).to_dict()
        
        # 4. Effect sizes
        results["cohens_d"] = self.cohens_d(times1, times2)
        results["vargha_delaney"] = self.vargha_delaney(times1, times2)
        
        # 5. Descriptive comparison
        results["descriptive"] = {
            solver1_name: {
                "mean": round(float(np.mean(times1)), 6),
                "median": round(float(np.median(times1)), 6),
                "std": round(float(np.std(times1, ddof=1)), 6),
                "q1": round(float(np.percentile(times1, 25)), 6),
                "q3": round(float(np.percentile(times1, 75)), 6),
            },
            solver2_name: {
                "mean": round(float(np.mean(times2)), 6),
                "median": round(float(np.median(times2)), 6),
                "std": round(float(np.std(times2, ddof=1)), 6),
                "q1": round(float(np.percentile(times2, 25)), 6),
                "q3": round(float(np.percentile(times2, 75)), 6),
            },
        }
        
        # 6. Win/loss analysis
        wins1 = int(np.sum(times1 < times2))
        wins2 = int(np.sum(times2 < times1))
        ties = len(times1) - wins1 - wins2
        
        results["wins"] = {
            f"{solver1_name}_wins": wins1,
            f"{solver2_name}_wins": wins2,
            "ties": ties,
            "speedup_geometric": round(float(np.exp(np.mean(np.log(times2 / np.maximum(times1, 1e-9))))), 4)
        }
        
        # 7. Automated interpretation
        wilcoxon_p = results["wilcoxon"]["p_value"]
        effect = results["vargha_delaney"]["interpretation"]
        faster = solver1_name if np.mean(times1) < np.mean(times2) else solver2_name
        
        if wilcoxon_p < 0.01:
            significance = "altamente significativa (p < 0.01)"
        elif wilcoxon_p < 0.05:
            significance = "significativa (p < 0.05)"
        else:
            significance = "NO significativa (p ≥ 0.05)"
        
        results["interpretation"] = {
            "summary": (
                f"La diferencia es {significance} con un efecto {effect}. "
                f"{faster} es más rápido en promedio."
            ),
            "recommended_test": "Wilcoxon signed-rank (non-parametric, paired)",
            "is_normal": results["normality"].get("shapiro_wilk", {}).get("is_normal", False),
        }
        
        return results
    
    def full_multi_solver_analysis(self, time_matrix: pd.DataFrame) -> Dict:
        """
        Análisis completo para k ≥ 3 solvers.
        
        Friedman → si significativo → Nemenyi post-hoc + correcciones
        
        Args:
            time_matrix: DataFrame [benchmarks × solvers] de tiempos
        """
        k = time_matrix.shape[1]
        n = time_matrix.shape[0]
        
        results = {
            "n_solvers": k,
            "n_benchmarks": n,
            "solvers": list(time_matrix.columns),
        }
        
        # 1. Friedman test
        friedman = self.friedman_test(time_matrix)
        results["friedman"] = friedman.to_dict()
        
        # 2. If significant, do post-hoc
        if friedman.significant_005:
            results["nemenyi"] = self.nemenyi_post_hoc(time_matrix, alpha=0.05)
            
            # Also collect all pairwise p-values for multiple correction
            pairwise_p = []
            pairwise_labels = []
            solvers = list(time_matrix.columns)
            
            for i, s1 in enumerate(solvers):
                for j, s2 in enumerate(solvers):
                    if i >= j:
                        continue
                    t1 = time_matrix[s1].values
                    t2 = time_matrix[s2].values
                    try:
                        _, p = scipy_stats.wilcoxon(t1, t2)
                        pairwise_p.append(float(p))
                        pairwise_labels.append(f"{s1} vs {s2}")
                    except:
                        pairwise_p.append(1.0)
                        pairwise_labels.append(f"{s1} vs {s2}")
            
            # Multiple comparison corrections
            results["multiple_corrections"] = {
                "labels": pairwise_labels,
                "bonferroni": self.correct_pvalues(pairwise_p, "bonferroni"),
                "holm": self.correct_pvalues(pairwise_p, "holm"),
                "benjamini_hochberg": self.correct_pvalues(pairwise_p, "bh"),
            }
        else:
            results["post_hoc"] = {
                "message": "Friedman test not significant. No post-hoc tests needed.",
                "interpretation": "No statistically significant differences among solvers."
            }
        
        # 3. Ranking
        ranks = time_matrix.rank(axis=1, method='average')
        avg_ranks = ranks.mean(axis=0).sort_values()
        
        results["ranking"] = [
            {"rank": i+1, "solver": s, "avg_rank": round(float(r), 3)}
            for i, (s, r) in enumerate(avg_ranks.items())
        ]
        
        return results
    
    # ==================== HELPERS ====================
    
    @staticmethod
    def _interpret_d(d: float) -> str:
        if d < 0.2: return "negligible"
        elif d < 0.5: return "small"
        elif d < 0.8: return "medium"
        else: return "large"
    
    @staticmethod
    def _interpret_r(r: float) -> str:
        if r < 0.1: return "negligible"
        elif r < 0.3: return "small"
        elif r < 0.5: return "medium"
        else: return "large"
    
    @staticmethod
    def _interpret_a_measure(a: float) -> str:
        d = abs(a - 0.5)
        if d < 0.06: return "negligible"
        elif d < 0.14: return "small"
        elif d < 0.21: return "medium"
        else: return "large"
    
    @staticmethod
    def _interpret_w(w: float) -> str:
        if w < 0.1: return "negligible"
        elif w < 0.3: return "small"
        elif w < 0.5: return "medium"
        else: return "large"
