import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# Agregar path del proyecto
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.benchmark_manager import BenchmarkManager
from app.utils.helpers import format_memory, format_number

st.set_page_config(
    page_title="Benchmarks - SAT Benchmark Suite",
    page_icon="📁",
    layout="wide"
)

st.title("📁 Gestión de Benchmarks")
st.markdown("---")

# Inicializar manager
@st.cache_resource
def get_benchmark_manager():
    return BenchmarkManager()

bm = get_benchmark_manager()

# ===== Sidebar: Actions =====
st.sidebar.header("⚙️ Acciones")

action = st.sidebar.radio(
    "Seleccionar Acción",
    ["📊 Ver Benchmarks", "➕ Importar", "🔍 Buscar", "📈 Estadísticas"]
)

st.sidebar.markdown("---")

# ===== ACTION 1: Ver Benchmarks =====
if action == "📊 Ver Benchmarks":
    st.header("📋 Benchmarks Registrados")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    df = bm.get_benchmarks_dataframe()
    
    if df.empty:
        st.warning("⚠️ No hay benchmarks registrados. Importa benchmarks primero.")
        st.stop()
    
    with col1:
        families = ['All'] + sorted(df['family'].dropna().unique().tolist())
        selected_family = st.selectbox("Familia", families)
    
    with col2:
        difficulties = ['All'] + sorted(df['difficulty'].dropna().unique().tolist())
        selected_difficulty = st.selectbox("Dificultad", difficulties)
    
    with col3:
        sort_by = st.selectbox(
            "Ordenar por",
            ['filename', 'size_kb', 'num_variables', 'num_clauses', 'family']
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_family != 'All':
        filtered_df = filtered_df[filtered_df['family'] == selected_family]
    
    if selected_difficulty != 'All':
        filtered_df = filtered_df[filtered_df['difficulty'] == selected_difficulty]
    
    filtered_df = filtered_df.sort_values(sort_by)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Benchmarks", len(filtered_df))
    with col2:
        total_size = filtered_df['size_kb'].sum()
        st.metric("Total Size", format_memory(int(total_size)) if pd.notna(total_size) else "N/A")
    with col3:
        avg_vars = filtered_df['num_variables'].mean()
        st.metric("Avg Variables", format_number(int(avg_vars)) if pd.notna(avg_vars) else "N/A")
    with col4:
        avg_clauses = filtered_df['num_clauses'].mean()
        st.metric("Avg Clauses", format_number(int(avg_clauses)) if pd.notna(avg_clauses) else "N/A")
    
    st.markdown("---")
    
    # Tabla interactiva
    st.subheader("📄 Lista de Benchmarks")
    
    # Preparar columnas para display
    display_df = filtered_df[['filename', 'family', 'difficulty', 'size_kb', 
                               'num_variables', 'num_clauses', 'clause_variable_ratio']].copy()
    
    display_df.columns = ['Filename', 'Family', 'Difficulty', 'Size (KB)', 
                          'Variables', 'Clauses', 'C/V Ratio']
    
    # Funciones de formateo seguras
    def safe_format_number(x):
        if pd.isna(x) or x == 0:
            return 'N/A'
        try:
            return f"{int(x):,}"
        except:
            return 'N/A'
    
    def safe_format_ratio(x):
        if pd.isna(x) or x == 0:
            return 'N/A'
        try:
            return f'{float(x):.2f}'
        except:
            return 'N/A'
    
    def safe_format_size(x):
        if pd.isna(x) or x == 0:
            return '0'
        try:
            return f'{int(x):,}'
        except:
            return 'N/A'
    
    # Aplicar estilo
    styled_df = display_df.style.format({
        'Size (KB)': safe_format_size,
        'Variables': safe_format_number,
        'Clauses': safe_format_number,
        'C/V Ratio': safe_format_ratio
    })
    
    # Aplicar gradient solo a columnas numéricas que no sean NaN
    vars_not_na = display_df['Variables'].notna()
    clauses_not_na = display_df['Clauses'].notna()
    
    if vars_not_na.any() and clauses_not_na.any():
        styled_df = styled_df.background_gradient(
            subset=['Variables', 'Clauses'], 
            cmap='YlOrRd'
        )
    
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Botón de descarga
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="⬇️ Descargar CSV",
        data=csv,
        file_name="benchmarks.csv",
        mime="text/csv"
    )

# ===== ACTION 2: Importar =====
elif action == "➕ Importar":
    st.header("➕ Importar Benchmarks")
    
    tab1, tab2 = st.tabs(["📂 Escanear Directorio", "📤 Upload Archivos"])
    
    with tab1:
        st.subheader("Escanear Directorio de Benchmarks")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            benchmark_dir = st.text_input(
                "Directorio de Benchmarks",
                value=str(bm.benchmark_dir.absolute()),
                help="Ruta del directorio conteniendo archivos .cnf"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            scan_button = st.button("🔍 Escanear", type="primary")
        
        if scan_button:
            with st.spinner("Escaneando directorio..."):
                cnf_files = bm.scan_benchmark_directory(benchmark_dir)
            
            if not cnf_files:
                st.warning(f"⚠️ No se encontraron archivos .cnf en {benchmark_dir}")
            else:
                st.success(f"✅ Encontrados {len(cnf_files)} archivos CNF")
                
                # Preview
                st.subheader("Vista Previa")
                preview_df = pd.DataFrame({
                    'Filename': [Path(f).name for f in cnf_files[:100]],
                    'Path': cnf_files[:100]
                })
                st.dataframe(preview_df, use_container_width=True, height=300)
                
                if len(cnf_files) > 100:
                    st.info(f"ℹ️ Mostrando primeros 100 de {len(cnf_files)} archivos")
                
                # Import button
                col1, col2 = st.columns([1, 4])
                with col1:
                    max_workers = st.number_input("Workers Paralelos", 1, 16, 4)
                
                st.markdown("---")
                
                if st.button("🚀 Importar Todos", type="primary"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def progress_callback(completed, total, filename):
                        progress = completed / total
                        progress_bar.progress(progress)
                        status_text.text(f"Importando {completed}/{total}: {filename}")
                    
                    with st.spinner("Importando benchmarks..."):
                        results = bm.import_benchmarks_batch(
                            cnf_files,
                            max_workers=max_workers,
                            progress_callback=progress_callback
                        )
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Results
                    st.success("✅ Importación Completada")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("✅ Exitosos", results['success'])
                    with col2:
                        st.metric("⏭️ Omitidos", results['skipped'])
                    with col3:
                        st.metric("❌ Fallidos", results['failed'])
                    
                    if results['errors']:
                        with st.expander("Ver Errores"):
                            for error in results['errors']:
                                st.error(f"**{error['file']}**: {error['error']}")
    
    with tab2:
        st.subheader("Upload Archivos CNF")
        
        uploaded_files = st.file_uploader(
            "Selecciona archivos .cnf",
            type=['cnf'],
            accept_multiple_files=True,
            help="Puedes seleccionar múltiples archivos"
        )
        
        if uploaded_files:
            st.info(f"📁 {len(uploaded_files)} archivos seleccionados")
            
            if st.button("📤 Importar Archivos Uploaded", type="primary"):
                progress_bar = st.progress(0)
                imported = 0
                
                for i, uploaded_file in enumerate(uploaded_files):
                    # Save temporarily
                    temp_path = Path("temp") / uploaded_file.name
                    temp_path.parent.mkdir(exist_ok=True)
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Import
                    result = bm.import_benchmark(str(temp_path))
                    
                    if result:
                        imported += 1
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                st.success(f"✅ Importados {imported}/{len(uploaded_files)} benchmarks")

# ===== ACTION 3: Buscar =====
elif action == "🔍 Buscar":
    st.header("🔍 Buscar Benchmarks")
    
    search_query = st.text_input(
        "Buscar por nombre de archivo",
        placeholder="Ej: circuit, crypto, sat-comp-2020..."
    )
    
    if search_query:
        with st.spinner("Buscando..."):
            results = bm.search_benchmarks(search_query)
        
        if not results:
            st.warning("No se encontraron resultados")
        else:
            st.success(f"✅ Encontrados {len(results)} benchmarks")
            
            df = pd.DataFrame(results)
            
            st.dataframe(
                df[['filename', 'family', 'difficulty', 'num_variables', 'num_clauses']],
                use_container_width=True
            )
            
            # Detalles de benchmark seleccionado
            st.markdown("---")
            st.subheader("📊 Detalles del Benchmark")
            
            selected_name = st.selectbox(
                "Seleccionar benchmark",
                df['filename'].tolist()
            )
            
            if selected_name:
                selected_id = df[df['filename'] == selected_name].iloc[0]['id']
                details = bm.get_benchmark_details(selected_id)
                
                if details:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Información General**")
                        st.write(f"- **Archivo**: {details['filename']}")
                        st.write(f"- **Familia**: {details.get('family', 'N/A')}")
                        st.write(f"- **Dificultad**: {details.get('difficulty', 'N/A')}")
                        st.write(f"- **Tamaño**: {format_memory(details.get('size_kb', 0))}")
                        
                        checksum = details.get('checksum', '')
                        if checksum:
                            st.write(f"- **Checksum**: `{checksum[:16]}...`")
                        else:
                            st.write(f"- **Checksum**: N/A")
                    
                    with col2:
                        st.markdown("**Características CNF**")
                        
                        num_vars = details.get('num_variables')
                        num_clauses = details.get('num_clauses')
                        ratio = details.get('clause_variable_ratio')
                        
                        st.write(f"- **Variables**: {format_number(num_vars) if num_vars else 'N/A'}")
                        st.write(f"- **Cláusulas**: {format_number(num_clauses) if num_clauses else 'N/A'}")
                        st.write(f"- **Ratio C/V**: {ratio:.2f if ratio else 'N/A'}")
                    
                    # Run statistics
                    run_stats = details.get('run_stats', {})
                    if run_stats and run_stats.get('total_runs', 0) > 0:
                        st.markdown("---")
                        st.markdown("**Estadísticas de Ejecución**")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Runs", run_stats.get('total_runs', 0))
                        with col2:
                            st.metric("Solvers", run_stats.get('unique_solvers', 0))
                        with col3:
                            avg_time = run_stats.get('avg_time')
                            st.metric("Tiempo Promedio", 
                                    f"{avg_time:.2f}s" if avg_time else "N/A")
                        with col4:
                            best_time = run_stats.get('best_time')
                            st.metric("Mejor Tiempo", 
                                    f"{best_time:.2f}s" if best_time else "N/A")

# ===== ACTION 4: Estadísticas =====
elif action == "📈 Estadísticas":
    st.header("📈 Estadísticas de Benchmarks")
    
    df = bm.get_benchmarks_dataframe()
    
    if df.empty:
        st.warning("⚠️ No hay benchmarks para analizar")
        st.stop()
    
    # Estadísticas por familia
    st.subheader("📊 Distribución por Familia")
    
    family_stats = bm.get_family_statistics()
    
    if not family_stats.empty:
        st.dataframe(family_stats, use_container_width=True)
        
        # Gráfico de barras
        fig = px.bar(
            family_stats.reset_index(),
            x='family',
            y='Count',
            title="Benchmarks por Familia",
            labels={'family': 'Familia', 'Count': 'Cantidad'},
            color='Count',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Distribución por dificultad
    st.subheader("📊 Distribución por Dificultad")
    
    difficulty_dist = bm.get_difficulty_distribution()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart
        fig = px.pie(
            values=list(difficulty_dist.values()),
            names=list(difficulty_dist.keys()),
            title="Distribución de Dificultad"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Métricas
        for difficulty, count in difficulty_dist.items():
            st.metric(difficulty.capitalize(), count)
    
    st.markdown("---")
    
    # Scatter plot: Variables vs Clauses
    st.subheader("📊 Variables vs Cláusulas")
    
    fig = px.scatter(
        df.dropna(subset=['num_variables', 'num_clauses']),
        x='num_variables',
        y='num_clauses',
        color='family',
        size='size_kb',
        hover_data=['filename', 'difficulty'],
        title="Relación Variables-Cláusulas por Familia",
        labels={'num_variables': 'Variables', 'num_clauses': 'Cláusulas'},
        log_x=True,
        log_y=True
    )
    st.plotly_chart(fig, use_container_width=True)

# ===== Footer =====
st.markdown("---")
total_benchmarks = len(bm.get_benchmarks_dataframe())
st.caption(f"📁 Total de benchmarks registrados: {total_benchmarks}")