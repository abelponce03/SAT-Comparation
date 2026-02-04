import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.database import DatabaseManager
from app.analysis.statistics import SATStatistics
from app.analysis.plots import SATPlotter

st.set_page_config(
    page_title="Visualización - SAT Benchmark Suite",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Análisis y Visualización")
st.markdown("---")

# Inicializar DB
db = DatabaseManager()

# Verificar que hay datos
if not db.has_data():
    st.warning("⚠️ No hay datos de experimentos. Primero ejecuta experimentos o migra datos existentes.")
    st.stop()

# ===== Sidebar: Filtros =====
st.sidebar.header("🔍 Filtros")

# Cargar datos
all_runs = db.get_all_runs()

if all_runs.empty:
    st.error("No hay ejecuciones en la base de datos")
    st.stop()

# Filtros
available_solvers = sorted(all_runs['solver'].unique())
available_families = sorted(all_runs['family'].dropna().unique()) if 'family' in all_runs.columns else []

selected_solvers = st.sidebar.multiselect(
    "Solvers a Comparar",
    options=available_solvers,
    default=available_solvers[:min(3, len(available_solvers))]
)

if 'family' in all_runs.columns:
    selected_families = st.sidebar.multiselect(
        "Familias de Benchmarks",
        options=available_families,
        default=available_families
    )
else:
    selected_families = []

timeout_value = st.sidebar.number_input(
    "Timeout (segundos)",
    min_value=1,
    value=5000,
    step=100
)

# Filtrar datos
filtered_df = all_runs[all_runs['solver'].isin(selected_solvers)].copy()

if selected_families and 'family' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['family'].isin(selected_families)]

if filtered_df.empty:
    st.warning("No hay datos con los filtros seleccionados")
    st.stop()

st.sidebar.markdown(f"**Datos filtrados:** {len(filtered_df)} ejecuciones")

# ===== Inicializar análisis =====
stats = SATStatistics(filtered_df, timeout=timeout_value)
plotter = SATPlotter()

# ===== Tabs de visualización =====
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Cactus Plot",
    "🔀 Comparación Pairwise",
    "🏆 Rankings",
    "🗺️ Heatmap",
    "📊 Estadísticas Detalladas"
])

# ===== TAB 1: Cactus Plot =====
with tab1:
    st.header("Cactus Plot - Instancias Resueltas vs Tiempo")
    st.markdown("""
    El **Cactus Plot** muestra cuántas instancias resuelve cada solver en función del tiempo.
    - **Eje X**: Número de instancias resueltas (ordenadas por tiempo)
    - **Eje Y**: Tiempo acumulado (escala logarítmica)
    - **Mejor solver**: curva más a la derecha/abajo
    """)
    
    cactus_data = stats.get_cactus_data()
    
    if not cactus_data.empty:
        fig_cactus = plotter.cactus_plot(cactus_data)
        st.plotly_chart(fig_cactus, use_container_width=True)
        
        # Tabla resumen
        st.subheader("📋 Resumen de Instancias Resueltas")
        summary = cactus_data.groupby('solver')['n_solved'].max().sort_values(ascending=False)
        
        col1, col2, col3 = st.columns(3)
        for i, (solver, count) in enumerate(summary.items()):
            with [col1, col2, col3][i % 3]:
                total = len(filtered_df[filtered_df['solver'] == solver]['benchmark'].unique())
                st.metric(
                    label=solver,
                    value=f"{count} / {total}",
                    delta=f"{count/total*100:.1f}%"
                )
    else:
        st.warning("No hay datos suficientes para generar Cactus Plot")

# ===== TAB 2: Comparación Pairwise =====
with tab2:
    st.header("Comparación Head-to-Head")
    
    if len(selected_solvers) < 2:
        st.warning("Selecciona al menos 2 solvers para comparación")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            solver_a = st.selectbox("Solver A (Eje X)", selected_solvers, key='solver_a')
        with col2:
            solver_b = st.selectbox("Solver B (Eje Y)", 
                                    [s for s in selected_solvers if s != solver_a],
                                    key='solver_b')
        
        if solver_a and solver_b:
            # Scatter plot
            fig_scatter = plotter.scatter_comparison(
                filtered_df, solver_a, solver_b, timeout=timeout_value
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Estadísticas pairwise
            st.subheader("📊 Estadísticas Head-to-Head")
            pairwise_stats = stats.pairwise_comparison(solver_a, solver_b)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Benchmarks", pairwise_stats['total_benchmarks'])
            with col2:
                st.metric(f"{solver_a} Gana", pairwise_stats[f'{solver_a}_wins'])
            with col3:
                st.metric(f"{solver_b} Gana", pairwise_stats[f'{solver_b}_wins'])
            with col4:
                st.metric("Empates", pairwise_stats['ties'])
            
            st.markdown(f"""
            **Speedup Geométrico:** {pairwise_stats['speedup_geometric_mean']:.2f}x
            - Valor > 1: {solver_a} es más rápido en promedio
            - Valor < 1: {solver_b} es más rápido en promedio
            """)

# ===== TAB 3: Rankings =====
with tab3:
    st.header("🏆 Rankings y PAR-2 Scores")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("PAR-2 Scores")
        par2_scores = stats.calculate_par2()
        fig_par2 = plotter.par2_comparison_bar(par2_scores)
        st.plotly_chart(fig_par2, use_container_width=True)
        
        st.markdown("""
        **PAR-2 Score**: Penalized Average Runtime
        - Tiempo promedio de ejecución
        - Timeouts cuentan como 2× timeout
        - **Menor es mejor**
        """)
    
    with col2:
        st.subheader("Instancias Resueltas")
        solved_stats = stats.count_solved()
        fig_solved = plotter.solved_instances_bar(solved_stats)
        st.plotly_chart(fig_solved, use_container_width=True)
    
    # Tabla comparativa
    st.subheader("📋 Tabla Comparativa")
    comparison_table = solved_stats.copy()
    comparison_table['PAR-2'] = par2_scores
    comparison_table = comparison_table.sort_values('solved', ascending=False)
    
    st.dataframe(
        comparison_table.style.background_gradient(subset=['solved'], cmap='Greens')
                              .background_gradient(subset=['PAR-2'], cmap='Reds_r')
                              .format({'PAR-2': '{:.2f}', 'solved_pct': '{:.1f}%'}),
        use_container_width=True
    )

# ===== TAB 4: Heatmap =====
with tab4:
    st.header("🗺️ Heatmap de Rendimiento")
    st.markdown("""
    Visualiza el rendimiento relativo de cada solver en cada benchmark.
    - **Verde**: Mejor rendimiento (más rápido)
    - **Rojo**: Peor rendimiento (más lento)
    - Valores normalizados por benchmark (1.0 = mejor solver)
    """)
    
    # Limitar número de benchmarks para visualización
    max_benchmarks = st.slider("Máximo de benchmarks a mostrar", 10, 100, 30)
    
    # Seleccionar benchmarks más interesantes (mayor variación entre solvers)
    benchmark_variance = filtered_df.groupby('benchmark')['wall_time_seconds'].std()
    top_benchmarks = benchmark_variance.nlargest(max_benchmarks).index
    
    heatmap_df = filtered_df[filtered_df['benchmark'].isin(top_benchmarks)]
    
    if not heatmap_df.empty:
        fig_heatmap = plotter.performance_heatmap(heatmap_df)
        st.plotly_chart(fig_heatmap, use_container_width=True)
    else:
        st.warning("No hay suficientes datos para generar heatmap")

# ===== TAB 5: Estadísticas Detalladas =====
with tab5:
    st.header("📊 Estadísticas Detalladas")
    
    # Virtual Best Solver
    st.subheader("🏅 Virtual Best Solver (VBS)")
    vbs_df, vbs_stats = stats.calculate_virtual_best_solver()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(vbs_stats)
    
    with col2:
        # Distribución de contribuciones al VBS
        vbs_contribution = vbs_df['vbs_solver'].value_counts()
        st.bar_chart(vbs_contribution)
    
    st.markdown("---")
    
    # Tabla de datos raw
    st.subheader("📄 Datos Raw Filtrados")
    st.dataframe(
        filtered_df[['solver', 'benchmark', 'result', 'wall_time_seconds', 
                     'conflicts', 'decisions', 'max_memory_kb']].head(100),
        use_container_width=True
    )
    
    # Botón de descarga
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="⬇️ Descargar CSV Filtrado",
        data=csv,
        file_name="filtered_results.csv",
        mime="text/csv"
    )

# ===== Footer =====
st.markdown("---")
st.caption(f"📊 Mostrando {len(filtered_df)} ejecuciones de {len(selected_solvers)} solvers")