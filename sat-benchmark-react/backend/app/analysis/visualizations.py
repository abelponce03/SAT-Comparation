"""
SAT Solver Visualization Engine
================================

Generación de gráficos de calidad publicación para comparación de SAT solvers.

Plots disponibles:
- Cactus Plot (instancias resueltas vs tiempo)
- Scatter Plot (comparación pairwise)
- Boxplot con CIs  
- Heatmap de rendimiento (solver × familia)
- ECDF / Performance Profile
- Critical Difference Diagram (Demšar)
- Survival Analysis Plot

Ref:
  Biere et al., "Handbook of Satisfiability", Ch. 28
  Demšar, JMLR 2006 (critical difference diagrams)
"""

import io
import base64
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Lazy imports for heavy libs
_plt = None
_sns = None


def _ensure_matplotlib():
    """Lazy-load matplotlib with non-interactive backend."""
    global _plt
    if _plt is None:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        _plt = plt
    return _plt


def _ensure_seaborn():
    """Lazy-load seaborn."""
    global _sns
    if _sns is None:
        import seaborn as sns
        _sns = sns
    return _sns


# Color palette for solvers (up to 8)
SOLVER_COLORS = [
    "#2563EB",  # Blue - Kissat
    "#DC2626",  # Red - MiniSat
    "#059669",  # Emerald - CaDiCaL
    "#D97706",  # Amber - CryptoMiniSat
    "#7C3AED",  # Violet
    "#DB2777",  # Pink
    "#0891B2",  # Cyan
    "#65A30D",  # Lime
]

SOLVER_MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p']
SOLVER_LINESTYLES = ['-', '--', '-.', ':', '-', '--', '-.', ':']


def _fig_to_base64(fig, dpi: int = 150, format: str = 'png') -> str:
    """Convert matplotlib figure to base64 string."""
    buf = io.BytesIO()
    fig.savefig(buf, format=format, dpi=dpi, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return f"data:image/{format};base64,{encoded}"


def _fig_to_bytes(fig, dpi: int = 150, format: str = 'png') -> bytes:
    """Convert matplotlib figure to bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format=format, dpi=dpi, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    data = buf.read()
    buf.close()
    return data


class SATVisualizationEngine:
    """
    Motor de visualización para comparación de SAT solvers.
    
    Genera gráficos publication-ready con matplotlib/seaborn.
    Los gráficos se devuelven como base64-encoded images.
    """
    
    def __init__(self, style: str = "seaborn-v0_8-whitegrid", 
                 figsize: Tuple[int, int] = (10, 7),
                 dpi: int = 150):
        self.figsize = figsize
        self.dpi = dpi
        self.style = style
    
    def _apply_style(self):
        """Apply publication-ready style."""
        plt = _ensure_matplotlib()
        try:
            plt.style.use(self.style)
        except OSError:
            plt.style.use('seaborn-v0_8')
        except:
            pass  # fallback to default
        
        plt.rcParams.update({
            'font.size': 12,
            'axes.labelsize': 14,
            'axes.titlesize': 16,
            'legend.fontsize': 11,
            'xtick.labelsize': 11,
            'ytick.labelsize': 11,
            'figure.dpi': self.dpi,
            'savefig.dpi': self.dpi,
            'font.family': 'sans-serif',
        })
    
    # ==================== CACTUS PLOT ====================
    
    def cactus_plot(self, solver_times: Dict[str, List[float]],
                    timeout: float = 300,
                    title: str = "Cactus Plot",
                    log_scale: bool = True) -> str:
        """
        Cactus Plot (instancias resueltas vs tiempo acumulado).
        
        Eje X: número de instancias resueltas
        Eje Y: tiempo (segundos, escala log opcional)
        
        El solver "mejor" tiene la curva más a la derecha y abajo.
        Estándar de facto en SAT Competition.
        """
        plt = _ensure_matplotlib()
        self._apply_style()
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        for idx, (solver, times) in enumerate(solver_times.items()):
            sorted_times = sorted([t for t in times if t < timeout])
            instances = list(range(1, len(sorted_times) + 1))
            
            color = SOLVER_COLORS[idx % len(SOLVER_COLORS)]
            marker = SOLVER_MARKERS[idx % len(SOLVER_MARKERS)]
            ls = SOLVER_LINESTYLES[idx % len(SOLVER_LINESTYLES)]
            
            ax.plot(instances, sorted_times, 
                    color=color, marker=marker, linestyle=ls,
                    linewidth=2, markersize=5,
                    label=f"{solver} ({len(sorted_times)} solved)",
                    alpha=0.85)
        
        ax.set_xlabel("Instances Solved")
        ax.set_ylabel("CPU Time (seconds)")
        ax.set_title(title)
        
        if log_scale and any(t > 0 for times in solver_times.values() for t in times):
            ax.set_yscale('log')
        
        ax.axhline(y=timeout, color='gray', linestyle=':', alpha=0.5, label=f'Timeout ({timeout}s)')
        
        ax.legend(loc='upper left', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    # ==================== SCATTER PLOT ====================
    
    def scatter_plot(self, times1: np.ndarray, times2: np.ndarray,
                     solver1: str, solver2: str,
                     timeout: float = 300,
                     title: Optional[str] = None) -> str:
        """
        Scatter Plot (comparación pairwise).
        
        Cada punto = una instancia.
        Puntos debajo de la diagonal → solver2 es más rápido.
        Puntos encima → solver1 es más rápido.
        """
        plt = _ensure_matplotlib()
        self._apply_style()
        
        fig, ax = plt.subplots(figsize=(self.figsize[0], self.figsize[0]))  # Square
        
        ax.scatter(times1, times2, alpha=0.6, s=40, c=SOLVER_COLORS[0],
                   edgecolors='white', linewidths=0.5, zorder=3)
        
        # Diagonal line
        max_val = max(np.max(times1), np.max(times2), timeout)
        ax.plot([0, max_val*1.1], [0, max_val*1.1], 'k--', alpha=0.4, linewidth=1)
        
        # Timeout lines
        ax.axhline(y=timeout, color='red', linestyle=':', alpha=0.3, linewidth=1)
        ax.axvline(x=timeout, color='red', linestyle=':', alpha=0.3, linewidth=1)
        
        # 10x speedup lines
        ax.plot([0, max_val*1.1], [0, max_val*11], color='gray', linestyle=':', alpha=0.2)
        ax.plot([0, max_val*11], [0, max_val*1.1], color='gray', linestyle=':', alpha=0.2)
        
        ax.set_xlabel(f"{solver1} (seconds)")
        ax.set_ylabel(f"{solver2} (seconds)")
        ax.set_title(title or f"{solver1} vs {solver2}")
        
        ax.set_xscale('log')
        ax.set_yscale('log')
        
        # Count wins
        wins1 = int(np.sum(times1 < times2))
        wins2 = int(np.sum(times2 < times1))
        ax.text(0.05, 0.95, f"{solver1}: {wins1} wins", transform=ax.transAxes,
                fontsize=10, verticalalignment='top', color=SOLVER_COLORS[0])
        ax.text(0.95, 0.05, f"{solver2}: {wins2} wins", transform=ax.transAxes,
                fontsize=10, verticalalignment='bottom', horizontalalignment='right',
                color=SOLVER_COLORS[1])
        
        ax.grid(True, alpha=0.2)
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    # ==================== BOXPLOT ====================
    
    def boxplot(self, solver_times: Dict[str, List[float]],
                title: str = "Runtime Distribution",
                log_scale: bool = True,
                show_points: bool = True) -> str:
        """
        Boxplot con distribución de tiempos por solver.
        Opcionalmente muestra puntos individuales (swarm/strip).
        """
        plt = _ensure_matplotlib()
        sns = _ensure_seaborn()
        self._apply_style()
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Prepare data
        data_list = []
        for solver, times in solver_times.items():
            for t in times:
                data_list.append({"Solver": solver, "Time": t})
        df = pd.DataFrame(data_list)
        
        if df.empty:
            ax.text(0.5, 0.5, "No data available", ha='center', va='center',
                    transform=ax.transAxes, fontsize=14)
            result = _fig_to_base64(fig, self.dpi)
            plt.close(fig)
            return result
        
        # Box plot
        palette = {s: SOLVER_COLORS[i % len(SOLVER_COLORS)] 
                   for i, s in enumerate(solver_times.keys())}
        
        sns.boxplot(data=df, x="Solver", y="Time", palette=palette, ax=ax,
                    showfliers=False, width=0.5, linewidth=1.5)
        
        if show_points and len(df) < 500:
            sns.stripplot(data=df, x="Solver", y="Time", palette=palette, ax=ax,
                         alpha=0.4, size=4, jitter=True)
        
        if log_scale:
            ax.set_yscale('log')
        
        ax.set_title(title)
        ax.set_ylabel("CPU Time (seconds)")
        ax.grid(True, axis='y', alpha=0.3)
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    # ==================== HEATMAP ====================
    
    def heatmap(self, matrix: pd.DataFrame,
                title: str = "Performance Heatmap",
                cmap: str = "RdYlGn_r",
                annot: bool = True,
                fmt: str = ".1f") -> str:
        """
        Heatmap de rendimiento (solver × familia/categoría).
        
        Colores más oscuros = más lento (peor).
        """
        plt = _ensure_matplotlib()
        sns = _ensure_seaborn()
        self._apply_style()
        
        h = max(6, matrix.shape[0] * 0.6)
        w = max(8, matrix.shape[1] * 1.5)
        fig, ax = plt.subplots(figsize=(w, h))
        
        sns.heatmap(matrix, annot=annot, fmt=fmt, cmap=cmap, ax=ax,
                    linewidths=0.5, linecolor='white',
                    cbar_kws={'label': 'Time (seconds)'})
        
        ax.set_title(title)
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    # ==================== ECDF ====================
    
    def ecdf_plot(self, solver_times: Dict[str, List[float]],
                  timeout: float = 300,
                  title: str = "Empirical CDF") -> str:
        """
        Empirical Cumulative Distribution Function.
        
        Muestra la fracción de instancias resueltas dentro de un tiempo dado.
        """
        plt = _ensure_matplotlib()
        self._apply_style()
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        for idx, (solver, times) in enumerate(solver_times.items()):
            solved = sorted([t for t in times if t < timeout])
            total = len(times)
            
            if not solved:
                continue
            
            x = [0] + solved + [timeout]
            y = [0] + [i/total for i in range(1, len(solved)+1)] + [len(solved)/total]
            
            color = SOLVER_COLORS[idx % len(SOLVER_COLORS)]
            ax.step(x, y, where='post', color=color, linewidth=2,
                    label=f"{solver} ({len(solved)}/{total})",
                    linestyle=SOLVER_LINESTYLES[idx % len(SOLVER_LINESTYLES)])
        
        ax.set_xlabel("CPU Time (seconds)")
        ax.set_ylabel("Fraction of Instances Solved")
        ax.set_title(title)
        ax.set_xscale('log')
        ax.set_xlim(left=0.001)
        ax.set_ylim(0, 1.05)
        ax.legend(loc='lower right', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    # ==================== PERFORMANCE PROFILE ====================
    
    def performance_profile(self, solver_times: Dict[str, List[float]],
                            timeout: float = 300,
                            tau_max: float = 100,
                            title: str = "Performance Profile") -> str:
        """
        Performance Profile (Dolan & Moré, 2002).
        
        rho_s(tau) = P(r_{i,s} <= tau) donde r_{i,s} = t_{i,s} / min_s(t_{i,s})
        
        El solver "mejor" tiene la curva más arriba y a la izquierda.
        rho_s(1) = fracción de instancias donde es el más rápido.
        """
        plt = _ensure_matplotlib()
        self._apply_style()
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        solvers = list(solver_times.keys())
        n = len(list(solver_times.values())[0])
        
        # Build time matrix
        time_mat = np.array([solver_times[s] for s in solvers]).T  # [n × k]
        
        # Replace timeouts
        time_mat = np.where(time_mat >= timeout, timeout * 10, time_mat)
        time_mat = np.maximum(time_mat, 1e-9)  # avoid div by zero
        
        # Compute performance ratios
        min_times = time_mat.min(axis=1, keepdims=True)
        ratios = time_mat / min_times
        
        tau_values = np.logspace(0, np.log10(tau_max), 500)
        
        for idx, solver in enumerate(solvers):
            solver_ratios = ratios[:, idx]
            fractions = [np.mean(solver_ratios <= tau) for tau in tau_values]
            
            color = SOLVER_COLORS[idx % len(SOLVER_COLORS)]
            ax.plot(tau_values, fractions, color=color, linewidth=2,
                    label=f"{solver} (best: {np.mean(solver_ratios <= 1.0):.1%})",
                    linestyle=SOLVER_LINESTYLES[idx % len(SOLVER_LINESTYLES)])
        
        ax.set_xlabel("Performance Ratio τ")
        ax.set_ylabel("ρ(τ) = P(ratio ≤ τ)")
        ax.set_title(title)
        ax.set_xscale('log')
        ax.set_ylim(0, 1.05)
        ax.legend(loc='lower right', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    # ==================== CRITICAL DIFFERENCE DIAGRAM ====================
    
    def critical_difference_diagram(self, avg_ranks: Dict[str, float],
                                     cd: float,
                                     title: str = "Critical Difference Diagram",
                                     alpha: float = 0.05) -> str:
        """
        Diagrama de Diferencia Crítica (Demšar, 2006).
        
        Muestra los rangos promedio de cada solver.
        Solvers conectados por una barra horizontal NO tienen diferencia significativa.
        
        Args:
            avg_ranks: {solver_name: average_rank}
            cd: critical difference from Nemenyi test
        """
        plt = _ensure_matplotlib()
        self._apply_style()
        
        k = len(avg_ranks)
        sorted_solvers = sorted(avg_ranks.items(), key=lambda x: x[1])
        
        fig, ax = plt.subplots(figsize=(max(10, k * 2), max(3, k * 0.8)))
        
        # Draw axis
        min_rank = 1
        max_rank = k
        ax.set_xlim(min_rank - 0.5, max_rank + 0.5)
        ax.set_ylim(0, k + 1)
        
        # Draw horizontal axis at top
        ax.hlines(k + 0.5, min_rank, max_rank, colors='black', linewidth=1)
        for i in range(1, k + 1):
            ax.vlines(i, k + 0.3, k + 0.7, colors='black', linewidth=1)
            ax.text(i, k + 0.8, str(i), ha='center', va='bottom', fontsize=11)
        
        # Place solvers
        left_solvers = sorted_solvers[:k//2]
        right_solvers = sorted_solvers[k//2:]
        
        for idx, (solver, rank) in enumerate(left_solvers):
            y = k - idx - 0.5
            ax.plot([rank, rank], [k + 0.3, y + 0.2], 'k-', linewidth=1)
            ax.plot(rank, y + 0.2, 'ko', markersize=5)
            ax.text(min_rank - 0.3, y + 0.2, f"{solver} ({rank:.2f})",
                    ha='right', va='center', fontsize=11, fontweight='bold')
        
        for idx, (solver, rank) in enumerate(right_solvers):
            y = k - (k//2 + idx) - 0.5
            ax.plot([rank, rank], [k + 0.3, y + 0.2], 'k-', linewidth=1)
            ax.plot(rank, y + 0.2, 'ko', markersize=5)
            ax.text(max_rank + 0.3, y + 0.2, f"({rank:.2f}) {solver}",
                    ha='left', va='center', fontsize=11, fontweight='bold')
        
        # Draw CD bars (connect solvers that are NOT significantly different)
        cliques = self._find_cliques(sorted_solvers, cd)
        bar_y = k + 1.2
        
        for clique in cliques:
            if len(clique) > 1:
                left_rank = min(r for _, r in clique)
                right_rank = max(r for _, r in clique)
                ax.hlines(bar_y, left_rank, right_rank, colors='red',
                         linewidth=3, alpha=0.7)
                bar_y += 0.3
        
        # CD annotation
        cd_x = (min_rank + max_rank) / 2
        ax.annotate(f"CD = {cd:.3f}", xy=(cd_x, k + 1.5),
                   fontsize=12, ha='center', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.axis('off')
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    def _find_cliques(self, sorted_solvers: List[Tuple[str, float]],
                       cd: float) -> List[List[Tuple[str, float]]]:
        """Find maximal cliques of solvers within CD of each other."""
        cliques = []
        
        for i, (s1, r1) in enumerate(sorted_solvers):
            clique = [(s1, r1)]
            for j in range(i + 1, len(sorted_solvers)):
                s2, r2 = sorted_solvers[j]
                if abs(r2 - r1) <= cd:
                    clique.append((s2, r2))
            
            # Only keep if this clique is not a subset of an existing one
            if len(clique) > 1:
                is_subset = False
                for existing in cliques:
                    if set(s for s, _ in clique).issubset(set(s for s, _ in existing)):
                        is_subset = True
                        break
                if not is_subset:
                    cliques.append(clique)
        
        return cliques
    
    # ==================== PAR-2 BAR CHART ====================
    
    def par2_bar_chart(self, par2_scores: Dict[str, float],
                       title: str = "PAR-2 Scores") -> str:
        """Bar chart de PAR-2 scores por solver."""
        plt = _ensure_matplotlib()
        self._apply_style()
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        sorted_items = sorted(par2_scores.items(), key=lambda x: x[1])
        solvers = [s for s, _ in sorted_items]
        scores = [v for _, v in sorted_items]
        colors = [SOLVER_COLORS[i % len(SOLVER_COLORS)] for i in range(len(solvers))]
        
        bars = ax.barh(solvers, scores, color=colors, edgecolor='white', linewidth=0.5)
        
        for bar, score in zip(bars, scores):
            ax.text(bar.get_width() + max(scores) * 0.01, bar.get_y() + bar.get_height()/2,
                    f'{score:.1f}', ha='left', va='center', fontsize=11)
        
        ax.set_xlabel("PAR-2 Score (lower is better)")
        ax.set_title(title)
        ax.grid(True, axis='x', alpha=0.3)
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    # ==================== SURVIVAL PLOT ====================
    
    def survival_plot(self, solver_times: Dict[str, List[float]],
                      timeout: float = 300,
                      title: str = "Survival Plot") -> str:
        """
        Survival Plot: fracción de instancias NO resueltas vs tiempo.
        Complemento de la ECDF.
        """
        plt = _ensure_matplotlib()
        self._apply_style()
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        for idx, (solver, times) in enumerate(solver_times.items()):
            total = len(times)
            solved = sorted([t for t in times if t < timeout])
            
            x = [0] + solved + [timeout]
            y = [1.0] + [1.0 - i/total for i in range(1, len(solved)+1)] + \
                [1.0 - len(solved)/total]
            
            color = SOLVER_COLORS[idx % len(SOLVER_COLORS)]
            ax.step(x, y, where='post', color=color, linewidth=2,
                    label=solver,
                    linestyle=SOLVER_LINESTYLES[idx % len(SOLVER_LINESTYLES)])
        
        ax.set_xlabel("CPU Time (seconds)")
        ax.set_ylabel("Fraction of Instances Unsolved")
        ax.set_title(title)
        ax.set_xscale('log')
        ax.set_ylim(-0.05, 1.05)
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        result = _fig_to_base64(fig, self.dpi)
        plt.close(fig)
        return result
    
    # ==================== COMBINED DASHBOARD ====================
    
    def generate_all_plots(self, solver_times: Dict[str, List[float]],
                            time_matrix: Optional[pd.DataFrame] = None,
                            par2_scores: Optional[Dict[str, float]] = None,
                            avg_ranks: Optional[Dict[str, float]] = None,
                            cd: Optional[float] = None,
                            family_matrix: Optional[pd.DataFrame] = None,
                            timeout: float = 300) -> Dict[str, str]:
        """
        Genera todos los gráficos relevantes.
        Devuelve un diccionario {plot_name: base64_image_string}.
        """
        plots = {}
        
        try:
            plots["cactus"] = self.cactus_plot(solver_times, timeout)
        except Exception as e:
            logger.warning(f"Failed to generate cactus plot: {e}")
        
        try:
            plots["ecdf"] = self.ecdf_plot(solver_times, timeout)
        except Exception as e:
            logger.warning(f"Failed to generate ECDF plot: {e}")
        
        try:
            plots["boxplot"] = self.boxplot(solver_times)
        except Exception as e:
            logger.warning(f"Failed to generate boxplot: {e}")
        
        try:
            plots["performance_profile"] = self.performance_profile(solver_times, timeout)
        except Exception as e:
            logger.warning(f"Failed to generate performance profile: {e}")
        
        try:
            plots["survival"] = self.survival_plot(solver_times, timeout)
        except Exception as e:
            logger.warning(f"Failed to generate survival plot: {e}")
        
        # Scatter plots (pairwise)
        solvers = list(solver_times.keys())
        for i, s1 in enumerate(solvers):
            for j, s2 in enumerate(solvers):
                if i >= j:
                    continue
                try:
                    t1 = np.array(solver_times[s1])
                    t2 = np.array(solver_times[s2])
                    n = min(len(t1), len(t2))
                    plots[f"scatter_{s1}_vs_{s2}"] = self.scatter_plot(
                        t1[:n], t2[:n], s1, s2, timeout
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate scatter {s1} vs {s2}: {e}")
        
        # PAR-2 bar chart
        if par2_scores:
            try:
                plots["par2_bar"] = self.par2_bar_chart(par2_scores)
            except Exception as e:
                logger.warning(f"Failed to generate PAR-2 bar chart: {e}")
        
        # Heatmap
        if family_matrix is not None and not family_matrix.empty:
            try:
                plots["heatmap"] = self.heatmap(family_matrix, title="Solver × Family Heatmap")
            except Exception as e:
                logger.warning(f"Failed to generate heatmap: {e}")
        
        # Critical difference diagram
        if avg_ranks and cd:
            try:
                plots["critical_difference"] = self.critical_difference_diagram(avg_ranks, cd)
            except Exception as e:
                logger.warning(f"Failed to generate CD diagram: {e}")
        
        return plots
