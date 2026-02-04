"""
SAT Benchmark Suite - Main Application
A comprehensive tool for benchmarking SAT solvers
"""

import streamlit as st
import sys
from pathlib import Path

# Add project path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import DatabaseManager
from app.core.benchmark_manager import BenchmarkManager

st.set_page_config(
    page_title="SAT Benchmark Suite",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔬 SAT Benchmark Suite")
st.markdown("### Sistema Integral de Benchmarking para SAT Solvers")

st.markdown("---")

# Initialize managers
@st.cache_resource
def get_managers():
    db = DatabaseManager()
    bm = BenchmarkManager()
    return db, bm

db, bm = get_managers()

# Dashboard
col1, col2, col3, col4 = st.columns(4)

with col1:
    solvers = db.get_solvers()
    st.metric(
        label="⚙️ Solvers",
        value=len(solvers),
        help="SAT Solvers registrados"
    )

with col2:
    benchmarks_df = bm.get_benchmarks_dataframe()
    st.metric(
        label="📁 Benchmarks",
        value=len(benchmarks_df),
        help="Instancias CNF registradas"
    )

with col3:
    experiments = db.get_experiments()
    st.metric(
        label="🧪 Experimentos",
        value=len(experiments),
        help="Experimentos ejecutados"
    )

with col4:
    has_runs = db.has_data()
    if has_runs:
        all_runs = db.get_all_runs()
        st.metric(
            label="📊 Ejecuciones",
            value=len(all_runs),
            help="Total de ejecuciones completadas"
        )
    else:
        st.metric(
            label="📊 Ejecuciones",
            value=0,
            help="Sin ejecuciones aún"
        )

st.markdown("---")

# Quick Actions
st.subheader("🚀 Acciones Rápidas")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown("### ⚙️ Setup")
    if st.button("Configurar Solvers", use_container_width=True):
        st.switch_page("pages/1_⚙️_Setup_Solvers.py")

with col2:
    st.markdown("### 📁 Benchmarks")
    if st.button("Gestionar Benchmarks", use_container_width=True):
        st.switch_page("pages/2_📁_Benchmarks.py")

with col3:
    st.markdown("### 🧪 Experimentos")
    if st.button("Crear/Ejecutar", use_container_width=True):
        st.switch_page("pages/5_🧪_Experiments.py")

with col4:
    st.markdown("### 📊 Resultados")
    if st.button("Visualizar", use_container_width=True):
        st.switch_page("pages/3_📊_Visualization.py")

with col5:
    st.markdown("### 🧹 Mantenimiento")
    if st.button("Limpiar BD", use_container_width=True):
        st.switch_page("pages/4_🧹_Database_Maintenance.py")

st.markdown("---")

# System Status
st.subheader("💾 Estado del Sistema")

db_stats = db.get_database_stats()

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Base de Datos**")
    st.write(f"- Solvers: {db_stats['solvers_count']}")
    st.write(f"- Benchmarks: {db_stats['benchmarks_count']}")
    st.write(f"- Experimentos: {db_stats['experiments_count']}")
    st.write(f"- Ejecuciones: {db_stats['runs_count']}")

with col2:
    st.markdown("**Almacenamiento**")
    st.write(f"- Tamaño BD: {db_stats['db_size_mb']} MB")
    
    if not benchmarks_df.empty:
        total_bench_size = benchmarks_df['size_kb'].sum() / 1024
        st.write(f"- Benchmarks: {total_bench_size:.2f} MB")

st.markdown("---")

# Documentation
with st.expander("📖 Guía de Uso"):
    st.markdown("""
    ## Flujo de Trabajo
    
    ### 1. Configurar Solvers
    - Ve a **Setup Solvers**
    - Agrega tus SAT solvers (MiniSat, CaDiCaL, etc.)
    - Configura paths y comandos de ejecución
    
    ### 2. Importar Benchmarks
    - Ve a **Benchmarks**
    - Escanea directorio o sube archivos .cnf
    - Los benchmarks se clasifican automáticamente
    
    ### 3. Ejecutar Experimentos
    - Ve a **Experiments** (próximamente)
    - Selecciona solvers y benchmarks
    - Configura timeout y recursos
    - Monitorea ejecución en tiempo real
    
    ### 4. Analizar Resultados
    - Ve a **Visualization**
    - Compara solvers con Cactus plots, Scatter plots
    - Calcula PAR-2, VBS, estadísticas
    - Exporta reportes
    """)

st.caption("Desarrollado con ❤️ usando Streamlit")
