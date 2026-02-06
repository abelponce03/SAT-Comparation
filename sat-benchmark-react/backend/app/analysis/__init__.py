"""
SAT Benchmark Suite - Rigorous Statistical Analysis Engine
==========================================================

Módulos para análisis estadístico de calidad académica de SAT solvers.

Componentes:
- statistical_tests: Tests no paramétricos (Wilcoxon, Friedman, Nemenyi)
- bootstrap_engine: Intervalos de confianza vía bootstrap
- metrics: Métricas estándar de benchmarking (PAR-2, PAR-10, VBS, solve rate)
- visualizations: Gráficos profesionales (cactus, scatter, boxplot, heatmap)
- report_generator: Generación de reportes HTML/PDF

Referencias:
  [1] Biere et al., "Handbook of Satisfiability", IOS Press, 2021
  [2] Beyersdorff et al., "SAT Competition 2024 proceedings"
  [3] Demšar, "Statistical Comparisons of Classifiers over Multiple Data Sets", JMLR 2006
"""

from .statistical_tests import StatisticalTestSuite
from .bootstrap_engine import BootstrapEngine
from .metrics import BenchmarkMetrics
from .visualizations import SATVisualizationEngine
from .report_generator import ReportGenerator

__all__ = [
    "StatisticalTestSuite",
    "BootstrapEngine", 
    "BenchmarkMetrics",
    "SATVisualizationEngine",
    "ReportGenerator",
]
