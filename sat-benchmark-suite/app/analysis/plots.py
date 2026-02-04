"""
Módulo de visualización con Plotly para análisis de SAT Solvers
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Optional

class SATPlotter:
    """Clase para generar gráficos de comparación de solvers"""
    
    # Paleta de colores profesional
    COLORS = px.colors.qualitative.Set2
    
    @staticmethod
    def cactus_plot(df: pd.DataFrame, title: str = "Cactus Plot") -> go.Figure:
        """
        Genera un Cactus Plot (instancias resueltas vs tiempo)
        
        Args:
            df: DataFrame con columnas [solver, n_solved, time]
        """
        fig = go.Figure()
        
        solvers = df['solver'].unique()
        
        for i, solver in enumerate(solvers):
            solver_data = df[df['solver'] == solver].sort_values('n_solved')
            
            fig.add_trace(go.Scatter(
                x=solver_data['n_solved'],
                y=solver_data['time'],
                mode='lines',
                name=solver,
                line=dict(width=3, color=SATPlotter.COLORS[i % len(SATPlotter.COLORS)]),
                hovertemplate=(
                    f'<b>{solver}</b><br>' +
                    'Resueltas: %{x}<br>' +
                    'Tiempo: %{y:.2f}s<br>' +
                    '<extra></extra>'
                )
            ))
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'family': 'Arial Black'}
            },
            xaxis_title="Número de Instancias Resueltas",
            yaxis_title="Tiempo (segundos)",
            yaxis_type="log",
            hovermode='closest',
            template='plotly_white',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="Black",
                borderwidth=1
            ),
            height=600
        )
        
        return fig
    
    @staticmethod
    def scatter_comparison(df: pd.DataFrame, solver1: str, solver2: str,
                          timeout: float = 5000.0) -> go.Figure:
        """
        Scatter Plot comparando dos solvers
        
        Args:
            df: DataFrame con columnas [benchmark, solver, wall_time_seconds, result]
        """
        # Pivot para comparación
        pivot = df.pivot_table(
            index='benchmark',
            columns='solver',
            values='wall_time_seconds',
            aggfunc='first'
        )
        
        if solver1 not in pivot.columns or solver2 not in pivot.columns:
            return go.Figure().add_annotation(
                text="Los solvers seleccionados no tienen datos",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20)
            )
        
        # Preparar datos (rellenar NaN con 2x timeout)
        x = pivot[solver1].fillna(timeout * 2)
        y = pivot[solver2].fillna(timeout * 2)
        
        # Limitar valores extremos
        x = x.clip(0.01, timeout * 2)
        y = y.clip(0.01, timeout * 2)
        
        # Determinar colores por resultado
        results_df = df[df['solver'] == solver1].set_index('benchmark')
        
        # Crear mapeo de colores
        color_map = {
            'SAT': 'green',
            'UNSAT': 'blue',
            'TIMEOUT': 'orange',
            'ERROR': 'red',
            'MEMOUT': 'purple'
        }
        
        colors = results_df.loc[pivot.index, 'result'].map(color_map).fillna('gray')
        
        fig = go.Figure()
        
        # Scatter points
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='markers',
            marker=dict(
                size=8,
                color=colors,
                opacity=0.6,
                line=dict(width=1, color='DarkSlateGrey')
            ),
            text=pivot.index,
            hovertemplate=(
                '<b>%{text}</b><br>' +
                f'{solver1}: %{{x:.2f}}s<br>' +
                f'{solver2}: %{{y:.2f}}s<br>' +
                '<extra></extra>'
            ),
            showlegend=False
        ))
        
        # Línea diagonal (igual rendimiento)
        max_val = min(max(x.max(), y.max()), timeout * 2)
        fig.add_trace(go.Scatter(
            x=[0.01, max_val],
            y=[0.01, max_val],
            mode='lines',
            line=dict(dash='dash', color='gray', width=2),
            name='Mismo rendimiento',
            showlegend=True
        ))
        
        # Línea 2x más rápido
        fig.add_trace(go.Scatter(
            x=[0.01, max_val / 2],
            y=[0.02, max_val],
            mode='lines',
            line=dict(dash='dot', color='lightblue', width=1),
            name=f'{solver2} 2x más lento',
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=[0.02, max_val],
            y=[0.01, max_val / 2],
            mode='lines',
            line=dict(dash='dot', color='lightcoral', width=1),
            name=f'{solver1} 2x más lento',
            showlegend=True
        ))
        
        fig.update_layout(
            title=f"Comparación: {solver1} vs {solver2}",
            xaxis_title=f"{solver1} - Tiempo (s)",
            yaxis_title=f"{solver2} - Tiempo (s)",
            xaxis_type="log",
            yaxis_type="log",
            xaxis=dict(range=[np.log10(0.01), np.log10(max_val)]),
            yaxis=dict(range=[np.log10(0.01), np.log10(max_val)]),
            template='plotly_white',
            height=700,
            width=700
        )
        
        return fig
    
    @staticmethod
    def performance_heatmap(df: pd.DataFrame, metric: str = 'wall_time_seconds') -> go.Figure:
        """
        Heatmap de rendimiento: solver x benchmark
        """
        pivot = df.pivot_table(
            index='benchmark',
            columns='solver',
            values=metric,
            aggfunc='first'
        )
        
        # Normalizar por fila (benchmark)
        pivot_norm = pivot.div(pivot.min(axis=1), axis=0)
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_norm.values,
            x=pivot_norm.columns,
            y=pivot_norm.index,
            colorscale='RdYlGn_r',
            text=pivot.values,
            texttemplate='%{text:.1f}s',
            textfont={"size": 8},
            colorbar=dict(title="Slowdown Factor")
        ))
        
        fig.update_layout(
            title="Heatmap de Rendimiento Relativo",
            xaxis_title="Solver",
            yaxis_title="Benchmark",
            height=max(400, len(pivot) * 15),
            template='plotly_white'
        )
        
        return fig
    
    @staticmethod
    def par2_comparison_bar(par2_scores: pd.Series) -> go.Figure:
        """Gráfico de barras de PAR-2 scores"""
        fig = go.Figure(data=[
            go.Bar(
                x=par2_scores.index,
                y=par2_scores.values,
                marker_color=SATPlotter.COLORS[:len(par2_scores)],
                text=par2_scores.values.round(2),
                textposition='outside',
            )
        ])
        
        fig.update_layout(
            title="PAR-2 Scores por Solver (menor es mejor)",
            xaxis_title="Solver",
            yaxis_title="PAR-2 Score (segundos)",
            template='plotly_white',
            height=500
        )
        
        return fig
    
    @staticmethod
    def solved_instances_bar(stats_df: pd.DataFrame) -> go.Figure:
        """Gráfico de instancias resueltas por solver"""
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Resueltas',
            x=stats_df.index,
            y=stats_df['solved'],
            marker_color='lightseagreen',
            text=stats_df['solved'],
            textposition='outside'
        ))
        
        fig.add_trace(go.Bar(
            name='Timeouts',
            x=stats_df.index,
            y=stats_df['timeout'],
            marker_color='orange',
            text=stats_df['timeout'],
            textposition='inside'
        ))
        
        fig.add_trace(go.Bar(
            name='Errores',
            x=stats_df.index,
            y=stats_df['error'],
            marker_color='crimson',
            text=stats_df['error'],
            textposition='inside'
        ))
        
        fig.update_layout(
            barmode='stack',
            title="Distribución de Resultados por Solver",
            xaxis_title="Solver",
            yaxis_title="Número de Instancias",
            template='plotly_white',
            height=500
        )
        
        return fig