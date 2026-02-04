import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import time
from datetime import datetime
import plotly.graph_objects as go

# Agregar path del proyecto
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.database import DatabaseManager
from app.core.solver_runner import ExperimentRunner
from app.utils.helpers import format_time, format_memory

st.set_page_config(
    page_title="Experiments - SAT Benchmark Suite",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Gestión de Experimentos")
st.markdown("---")

# Inicializar
db = DatabaseManager()

# ===== Sidebar: Actions =====
st.sidebar.header("⚙️ Acciones")

action = st.sidebar.radio(
    "Seleccionar Acción",
    [
        "➕ Nuevo Experimento",
        "📊 Ver Experimentos",
        "▶️ Ejecutar Experimento",
        "📈 Monitoreo en Tiempo Real"
    ]
)

st.sidebar.markdown("---")

# ===== ACTION 1: Nuevo Experimento =====
if action == "➕ Nuevo Experimento":
    st.header("➕ Crear Nuevo Experimento")
    
    with st.form("new_experiment"):
        exp_name = st.text_input(
            "Nombre del Experimento",
            placeholder="ej: minisat_vs_cadical_2024"
        )
        
        exp_description = st.text_area(
            "Descripción",
            placeholder="Descripción detallada del experimento..."
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            timeout = st.number_input(
                "Timeout (segundos)",
                min_value=1,
                value=5000,
                step=100
            )
        
        with col2:
            memory_limit = st.number_input(
                "Límite de Memoria (MB)",
                min_value=128,
                value=8192,
                step=512
            )
        
        with col3:
            parallel_jobs = st.number_input(
                "Jobs Paralelos",
                min_value=1,
                max_value=16,
                value=1
            )
        
        # Solver selection
        st.markdown("### Seleccionar Solvers")
        available_solvers = db.get_solvers(status='ready')
        
        if not available_solvers:
            st.warning("⚠️ No hay solvers disponibles. Configura solvers primero.")
        else:
            solver_names = [s['name'] for s in available_solvers]
            selected_solvers = st.multiselect(
                "Solvers a Evaluar",
                options=solver_names,
                default=solver_names[:min(2, len(solver_names))]
            )
        
        # Benchmark selection
        st.markdown("### Seleccionar Benchmarks")
        
        selection_mode = st.radio(
            "Modo de Selección",
            ["Por Familia", "Por Dificultad", "Todos", "Manual"]
        )
        
        all_benchmarks = db.get_benchmarks()
        benchmark_df = pd.DataFrame(all_benchmarks)
        
        selected_benchmark_ids = []
        
        if selection_mode == "Por Familia":
            families = sorted(benchmark_df['family'].unique())
            selected_families = st.multiselect("Familias", families)
            
            if selected_families:
                filtered = benchmark_df[benchmark_df['family'].isin(selected_families)]
                selected_benchmark_ids = filtered['id'].tolist()
                st.info(f"📁 {len(selected_benchmark_ids)} benchmarks seleccionados")
        
        elif selection_mode == "Por Dificultad":
            difficulties = sorted(benchmark_df['difficulty'].unique())
            selected_difficulties = st.multiselect("Dificultades", difficulties)
            
            if selected_difficulties:
                filtered = benchmark_df[benchmark_df['difficulty'].isin(selected_difficulties)]
                selected_benchmark_ids = filtered['id'].tolist()
                st.info(f"📁 {len(selected_benchmark_ids)} benchmarks seleccionados")
        
        elif selection_mode == "Todos":
            selected_benchmark_ids = benchmark_df['id'].tolist()
            st.info(f"📁 Todos los benchmarks: {len(selected_benchmark_ids)}")
        
        else:  # Manual
            max_display = st.slider("Máximo a mostrar", 10, len(benchmark_df), min(100, len(benchmark_df)))
            display_df = benchmark_df[['id', 'filename', 'family', 'difficulty']].head(max_display)
            
            st.dataframe(display_df, use_container_width=True, height=300)
            
            ids_input = st.text_input(
                "IDs de Benchmarks (separados por comas o rangos)",
                placeholder="1,2,3 o 1-10"
            )
            
            if ids_input:
                selected_benchmark_ids = []
                for part in ids_input.split(','):
                    part = part.strip()
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        selected_benchmark_ids.extend(range(start, end + 1))
                    else:
                        selected_benchmark_ids.append(int(part))
                
                st.info(f"📁 {len(selected_benchmark_ids)} benchmarks seleccionados")
        
        # Summary
        st.markdown("---")
        st.subheader("📋 Resumen del Experimento")
        
        if selected_solvers and selected_benchmark_ids:
            total_runs = len(selected_solvers) * len(selected_benchmark_ids)
            estimated_time = (total_runs * timeout) / (3600 * parallel_jobs)  # hours
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Ejecuciones", total_runs)
            with col2:
                st.metric("Tiempo Estimado (worst case)", f"{estimated_time:.1f}h")
            with col3:
                st.metric("Solvers × Benchmarks", f"{len(selected_solvers)} × {len(selected_benchmark_ids)}")
        
        # Submit
        submitted = st.form_submit_button("🚀 Crear Experimento", type="primary")
        
        if submitted:
            if not exp_name:
                st.error("❌ Debes proporcionar un nombre")
            elif not selected_solvers:
                st.error("❌ Debes seleccionar al menos un solver")
            elif not selected_benchmark_ids:
                st.error("❌ Debes seleccionar al menos un benchmark")
            else:
                # Get solver IDs
                solver_ids = [
                    s['id'] for s in available_solvers 
                    if s['name'] in selected_solvers
                ]
                
                # Create experiment
                exp_id = db.create_experiment(
                    name=exp_name,
                    description=exp_description,
                    timeout_seconds=timeout,
                    memory_limit_mb=memory_limit,
                    parallel_jobs=parallel_jobs,
                    metadata={
                        'solver_ids': solver_ids,
                        'benchmark_ids': selected_benchmark_ids,
                        'total_runs': len(solver_ids) * len(selected_benchmark_ids)
                    }
                )
                
                st.success(f"✅ Experimento creado con ID: {exp_id}")
                st.info("Ve a 'Ejecutar Experimento' para iniciar la ejecución")
                
                time.sleep(2)
                st.rerun()

# ===== ACTION 2: Ver Experimentos =====
elif action == "📊 Ver Experimentos":
    st.header("📊 Experimentos Registrados")
    
    experiments = db.get_experiments()
    
    if not experiments:
        st.info("No hay experimentos registrados. Crea uno nuevo.")
    else:
        exp_df = pd.DataFrame(experiments)
        
        # ========== MODIFIED: Eliminación directa por IDs sin filtros ==========
        st.markdown("### 🗑️ Eliminación de Experimentos")
        
        st.info("""
        **Eliminar experimentos por ID:**
        - Ingresa los IDs de los experimentos que deseas eliminar
        - Soporta rangos (ej: 1-5) y listas (ej: 1,3,7)
        - Se eliminarán todos los runs asociados automáticamente
        """)
        
        # Input directo de IDs
        ids_input = st.text_area(
            "IDs de experimentos a eliminar (separados por comas)",
            help="Ejemplo: 1, 5, 10, 15-20 (soporta rangos)",
            placeholder="1, 2, 3 o 10-20",
            key="delete_ids_input"
        )
        
        if ids_input:
            # Parse IDs
            ids_to_delete = []
            parse_errors = []
            
            for part in ids_input.split(','):
                part = part.strip()
                
                if not part:
                    continue
                
                if '-' in part:
                    # Range
                    try:
                        start, end = map(int, part.split('-'))
                        if start > end:
                            parse_errors.append(f"Rango inválido: {part} (inicio > fin)")
                        else:
                            ids_to_delete.extend(range(start, end + 1))
                    except ValueError:
                        parse_errors.append(f"Rango inválido: {part}")
                else:
                    # Single ID
                    try:
                        ids_to_delete.append(int(part))
                    except ValueError:
                        parse_errors.append(f"ID inválido: {part}")
            
            # Mostrar errores de parseo si existen
            if parse_errors:
                st.error("❌ Errores al parsear IDs:")
                for error in parse_errors:
                    st.write(f"  - {error}")
            
            if ids_to_delete:
                # Remover duplicados
                ids_to_delete = sorted(list(set(ids_to_delete)))
                
                # Filtrar IDs que existen en la BD
                existing_ids = exp_df['id'].tolist()
                valid_ids = [id for id in ids_to_delete if id in existing_ids]
                invalid_ids = [id for id in ids_to_delete if id not in existing_ids]
                
                if invalid_ids:
                    st.warning(f"⚠️ IDs no encontrados en la BD: {', '.join(map(str, invalid_ids))}")
                
                if valid_ids:
                    # Mostrar preview de experimentos a eliminar
                    preview_df = exp_df[exp_df['id'].isin(valid_ids)].copy()
                    
                    st.markdown("---")
                    st.subheader("📋 Preview de Experimentos a Eliminar")
                    
                    st.info(f"📊 {len(valid_ids)} experimentos seleccionados para eliminar")
                    
                    # Mostrar tabla con información relevante
                    display_preview = preview_df[[
                        'id', 'name', 'status', 'total_runs', 
                        'completed_runs', 'failed_runs', 'created_at'
                    ]].copy()
                    
                    display_preview.columns = [
                        'ID', 'Nombre', 'Estado', 'Total Runs',
                        'Completados', 'Fallidos', 'Creado'
                    ]
                    
                    # Color coding por estado
                    def color_status_delete(row):
                        status = row['Estado']
                        if status == 'completed':
                            return ['background-color: #d4edda'] * len(row)
                        elif status == 'failed':
                            return ['background-color: #f8d7da'] * len(row)
                        elif status == 'running':
                            return ['background-color: #fff3cd'] * len(row)
                        elif status == 'stopped':
                            return ['background-color: #ffc107'] * len(row)
                        else:
                            return ['background-color: #e9ecef'] * len(row)
                    
                    styled_preview = display_preview.style.apply(color_status_delete, axis=1)
                    
                    st.dataframe(styled_preview, use_container_width=True)
                    
                    # Calcular estadísticas totales
                    total_runs_to_delete = preview_df['total_runs'].sum()
                    total_completed = preview_df['completed_runs'].sum()
                    
                    st.markdown("---")
                    st.subheader("⚠️ Resumen de Eliminación")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Experimentos", len(valid_ids))
                    with col2:
                        st.metric("Total Runs", int(total_runs_to_delete))
                    with col3:
                        st.metric("Runs Completados", int(total_completed))
                    with col4:
                        percentage = (total_completed / total_runs_to_delete * 100) if total_runs_to_delete > 0 else 0
                        st.metric("% Completitud", f"{percentage:.1f}%")
                    
                    # Breakdown por estado
                    st.markdown("**Distribución por Estado:**")
                    status_counts = preview_df['status'].value_counts()
                    
                    status_cols = st.columns(len(status_counts))
                    for col, (status, count) in zip(status_cols, status_counts.items()):
                        with col:
                            st.metric(status.upper(), count)
                    
                    st.markdown("---")
                    
                    # Advertencia final
                    st.error(f"""
                    ⚠️ **ADVERTENCIA: Esta acción es IRREVERSIBLE**
                    
                    Se eliminarán permanentemente:
                    - **{len(valid_ids)} experimentos**
                    - **{int(total_runs_to_delete)} runs** asociados
                    - Todos los datos de ejecución relacionados
                    
                    Esta operación NO puede deshacerse.
                    """)
                    
                    # Botones de confirmación
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        # Checkbox de confirmación adicional
                        confirm_checkbox = st.checkbox(
                            "He leído la advertencia y confirmo la eliminación",
                            key="confirm_delete_checkbox"
                        )
                    
                    with col2:
                        if st.button("🗑️ ELIMINAR PERMANENTEMENTE", 
                                   type="primary", 
                                   disabled=not confirm_checkbox,
                                   key="delete_selected_btn"):
                            
                            # Doble confirmación en session_state
                            if st.session_state.get('confirm_final_delete', False):
                                # EJECUTAR ELIMINACIÓN
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                deleted = 0
                                failed = 0
                                errors = []
                                
                                for i, exp_id in enumerate(valid_ids):
                                    try:
                                        status_text.text(f"Eliminando experimento {exp_id}...")
                                        db.delete_experiment(exp_id)
                                        deleted += 1
                                    except Exception as e:
                                        failed += 1
                                        errors.append({'id': exp_id, 'error': str(e)})
                                        st.error(f"Error eliminando experimento {exp_id}: {e}")
                                    
                                    progress_bar.progress((i + 1) / len(valid_ids))
                                
                                progress_bar.empty()
                                status_text.empty()
                                
                                # Mostrar resultados
                                st.markdown("---")
                                st.success("✅ Eliminación Completada")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("✅ Eliminados", deleted)
                                with col2:
                                    st.metric("❌ Fallidos", failed)
                                
                                if errors:
                                    with st.expander("Ver Errores"):
                                        for error in errors:
                                            st.error(f"**Experimento {error['id']}**: {error['error']}")
                                
                                # Reset state
                                st.session_state['confirm_final_delete'] = False
                                st.session_state['confirm_delete_checkbox'] = False
                                
                                st.balloons()
                                
                                time.sleep(2)
                                st.rerun()
                            else:
                                # Primera confirmación
                                st.session_state['confirm_final_delete'] = True
                                st.warning("⚠️ **CONFIRMACIÓN FINAL**: Haz clic de nuevo en ELIMINAR para confirmar")
                    
                    with col3:
                        if st.button("❌ Cancelar", key="cancel_delete_btn"):
                            st.session_state['confirm_final_delete'] = False
                            st.session_state['confirm_delete_checkbox'] = False
                            st.rerun()
        
        st.markdown("---")
        
        # ========== Tabla principal de experimentos (sin cambios) ==========
        st.subheader("📊 Lista de Experimentos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.selectbox(
                "Filtrar por Estado",
                ['All'] + list(exp_df['status'].unique())
            )
        
        if status_filter != 'All':
            filtered_exp_df = exp_df[exp_df['status'] == status_filter]
        else:
            filtered_exp_df = exp_df
        
        # Tabla de experimentos
        display_df = filtered_exp_df[[
            'id', 'name', 'status', 'total_runs', 'completed_runs',
            'failed_runs', 'created_at'
        ]].copy()
        
        display_df.columns = [
            'ID', 'Nombre', 'Estado', 'Total Runs', 'Completados',
            'Fallidos', 'Creado'
        ]
        
        # Color coding por estado
        def color_status(row):
            status = row['Estado']
            if status == 'completed':
                return ['background-color: #d4edda'] * len(row)
            elif status == 'failed':
                return ['background-color: #f8d7da'] * len(row)
            elif status == 'running':
                return ['background-color: #fff3cd'] * len(row)
            elif status == 'stopped':
                return ['background-color: #ffc107'] * len(row)
            else:
                return [''] * len(row)
        
        styled_df = display_df.style.apply(color_status, axis=1)
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        st.caption(f"Mostrando {len(filtered_exp_df)} de {len(exp_df)} experimentos")
        
        # ========== Detalles de experimento seleccionado ==========
        st.markdown("---")
        st.subheader("📋 Detalles del Experimento")
        
        if len(filtered_exp_df) > 0:
            selected_id = st.selectbox(
                "Seleccionar Experimento",
                filtered_exp_df['id'].tolist(),
                format_func=lambda x: f"#{x} - {filtered_exp_df[filtered_exp_df['id']==x]['name'].iloc[0]}"
            )
            
            if selected_id:
                exp = filtered_exp_df[filtered_exp_df['id'] == selected_id].iloc[0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Información General**")
                    st.write(f"- **ID**: {exp['id']}")
                    st.write(f"- **Nombre**: {exp['name']}")
                    st.write(f"- **Estado**: {exp['status']}")
                    st.write(f"- **Timeout**: {exp['timeout_seconds']}s")
                    st.write(f"- **Memoria**: {exp['memory_limit_mb']} MB")
                
                with col2:
                    st.markdown("**Progreso**")
                    progress = exp['completed_runs'] / exp['total_runs'] if exp['total_runs'] > 0 else 0
                    st.progress(progress)
                    st.write(f"- **Completados**: {exp['completed_runs']}/{exp['total_runs']}")
                    st.write(f"- **Fallidos**: {exp['failed_runs']}")
                    
                    if exp['status'] == 'stopped':
                        st.warning("⚠️ **Experimento detenido**. Puedes reanudarlo desde 'Ejecutar Experimento'.")
                    
                    if exp['started_at']:
                        st.write(f"- **Iniciado**: {exp['started_at']}")
                    if exp['completed_at']:
                        st.write(f"- **Completado**: {exp['completed_at']}")
            
           