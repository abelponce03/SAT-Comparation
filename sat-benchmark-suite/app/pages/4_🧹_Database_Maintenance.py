import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.database import DatabaseManager

st.set_page_config(
    page_title="Database Maintenance - SAT Benchmark Suite",
    page_icon="🧹",
    layout="wide"
)

st.title("🧹 Mantenimiento de Base de Datos")
st.markdown("---")

# Inicializar DB
db = DatabaseManager()

# ===== Sidebar: Actions =====
st.sidebar.header("🛠️ Herramientas")

maintenance_action = st.sidebar.radio(
    "Seleccionar Acción",
    [
        "📊 Estado General",
        "🔍 Detectar Duplicados",
        "❌ Benchmarks Inválidos",
        "🗑️ Eliminación Manual",
        "🧹 Limpieza Automática"
    ]
)

st.sidebar.markdown("---")

# ===== ACTION 1: Estado General =====
if maintenance_action == "📊 Estado General":
    st.header("📊 Estado de la Base de Datos")
    
    # Estadísticas generales
    db_stats = db.get_database_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("⚙️ Solvers", db_stats['solvers_count'])
    with col2:
        st.metric("📁 Benchmarks", db_stats['benchmarks_count'])
    with col3:
        st.metric("🧪 Experimentos", db_stats['experiments_count'])
    with col4:
        st.metric("📊 Ejecuciones", db_stats['runs_count'])
    
    st.markdown("---")
    
    # Completitud de datos
    st.subheader("🔍 Calidad de Datos de Benchmarks")
    
    completeness = db.get_benchmark_completeness()
    
    total = completeness['total']
    
    if total == 0:
        st.info("No hay benchmarks en la base de datos")
    else:
        # Crear DataFrame para visualización
        quality_data = {
            'Campo': [
                'Variables',
                'Cláusulas',
                'Familia',
                'Dificultad',
                'Checksum'
            ],
            'Completos': [
                total - completeness['missing_variables'],
                total - completeness['missing_clauses'],
                total - completeness['unknown_family'],
                total - completeness['unknown_difficulty'],
                total - completeness['missing_checksum']
            ],
            'Incompletos': [
                completeness['missing_variables'],
                completeness['missing_clauses'],
                completeness['unknown_family'],
                completeness['unknown_difficulty'],
                completeness['missing_checksum']
            ]
        }
        
        quality_df = pd.DataFrame(quality_data)
        quality_df['% Completo'] = (quality_df['Completos'] / total * 100).round(1)
        
        st.dataframe(
            quality_df.style.background_gradient(subset=['% Completo'], cmap='RdYlGn', vmin=0, vmax=100),
            use_container_width=True
        )
        
        # Barra de progreso general
        st.markdown("### 📈 Completitud General")
        avg_completeness = quality_df['% Completo'].mean()
        
        st.progress(avg_completeness / 100)
        st.metric("Promedio de Completitud", f"{avg_completeness:.1f}%")
    
    # Tamaño de base de datos
    st.markdown("---")
    st.subheader("💾 Almacenamiento")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tamaño de BD", f"{db_stats['db_size_mb']} MB")
    with col2:
        st.info(f"📁 Ubicación: `{db.db_path}`")

# ===== ACTION 2: Detectar Duplicados =====
elif maintenance_action == "🔍 Detectar Duplicados":
    st.header("🔍 Detección de Benchmarks Duplicados")
    
    with st.spinner("Buscando duplicados..."):
        duplicates = db.find_duplicate_benchmarks()
    
    if not duplicates:
        st.success("✅ No se encontraron benchmarks duplicados")
    else:
        st.warning(f"⚠️ Encontrados {len(duplicates)} benchmarks con duplicados")
        
        for dup in duplicates:
            with st.expander(f"📁 {dup['filename']} - {dup['count']} versiones"):
                st.write(f"**IDs:** {', '.join(map(str, dup['ids']))}")
                
                # Mostrar detalles de cada versión
                st.markdown("**Comparación de versiones:**")
                
                comparison_data = {
                    'ID': dup['ids'],
                    'Variables': dup['variables'].split(','),
                    'Cláusulas': dup['clauses'].split(','),
                    'Familia': dup['families'].split(',')
                }
                
                comparison_df = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df, use_container_width=True)
                
                # Botones de acción
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"🧹 Mantener Mejor y Eliminar Duplicados", 
                                key=f"keep_best_{dup['filename']}"):
                        deleted = db.keep_best_duplicate(dup['filename'])
                        st.success(f"✅ Eliminadas {deleted} versiones duplicadas")
                        st.rerun()
                
                with col2:
                    if st.button(f"🗑️ Eliminar Todas las Versiones", 
                                key=f"delete_all_{dup['filename']}"):
                        result = db.delete_benchmarks_batch(dup['ids'])
                        st.success(f"✅ Eliminados {result['deleted']} benchmarks")
                        if result['has_runs'] > 0:
                            st.warning(f"⚠️ {result['has_runs']} benchmarks tienen ejecuciones asociadas")
                        st.rerun()

# ===== ACTION 3: Benchmarks Inválidos =====
elif maintenance_action == "❌ Benchmarks Inválidos":
    st.header("❌ Benchmarks con Datos Incompletos")
    
    with st.spinner("Buscando benchmarks inválidos..."):
        invalid = db.find_invalid_benchmarks()
    
    if not invalid:
        st.success("✅ Todos los benchmarks tienen datos completos")
    else:
        st.warning(f"⚠️ Encontrados {len(invalid)} benchmarks con datos incompletos")
        
        invalid_df = pd.DataFrame(invalid)
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            filter_family = st.checkbox("Filtrar solo 'unknown' family", value=False)
        with col2:
            filter_difficulty = st.checkbox("Filtrar solo 'unknown' difficulty", value=False)
        
        if filter_family:
            invalid_df = invalid_df[invalid_df['family'] == 'unknown']
        
        if filter_difficulty:
            invalid_df = invalid_df[invalid_df['difficulty'] == 'unknown']
        
        st.dataframe(invalid_df, use_container_width=True, height=400)
        
        # Selección para eliminación
        st.markdown("---")
        st.subheader("🗑️ Eliminar Benchmarks Inválidos")
        
        st.warning("⚠️ **Advertencia:** Esta acción eliminará permanentemente los benchmarks seleccionados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Eliminar TODOS los inválidos mostrados", type="primary"):
                ids_to_delete = invalid_df['id'].tolist()
                result = db.delete_benchmarks_batch(ids_to_delete)
                
                st.success(f"✅ Eliminados: {result['deleted']}")
                if result['failed'] > 0:
                    st.error(f"❌ Fallidos: {result['failed']}")
                if result['has_runs'] > 0:
                    st.warning(f"⚠️ Con ejecuciones: {result['has_runs']}")
                
                st.rerun()
        
        with col2:
            if st.button("🗑️ Solo sin Variables/Cláusulas"):
                to_delete = invalid_df[
                    invalid_df['num_variables'].isna() | invalid_df['num_clauses'].isna()
                ]
                ids_to_delete = to_delete['id'].tolist()
                result = db.delete_benchmarks_batch(ids_to_delete)
                
                st.success(f"✅ Eliminados: {result['deleted']}")
                st.rerun()
        
        with col3:
            if st.button("🗑️ Solo 'unknown' family"):
                to_delete = invalid_df[invalid_df['family'] == 'unknown']
                ids_to_delete = to_delete['id'].tolist()
                result = db.delete_benchmarks_batch(ids_to_delete)
                
                st.success(f"✅ Eliminados: {result['deleted']}")
                st.rerun()

# ===== ACTION 4: Eliminación Manual =====
elif maintenance_action == "🗑️ Eliminación Manual":
    st.header("🗑️ Eliminación Manual de Benchmarks")
    
    # Obtener todos los benchmarks
    all_benchmarks = db.get_benchmarks()
    
    if not all_benchmarks:
        st.info("No hay benchmarks en la base de datos")
    else:
        df = pd.DataFrame(all_benchmarks)
        
        st.write(f"**Total de benchmarks:** {len(df)}")
        
        # Tabla con selección
        st.markdown("### Selecciona benchmarks para eliminar")
        
        # Multiselect por búsqueda
        search_query = st.text_input("🔍 Buscar benchmarks", "")
        
        if search_query:
            filtered_df = df[df['filename'].str.contains(search_query, case=False, na=False)]
        else:
            filtered_df = df
        
        st.write(f"**Mostrando:** {len(filtered_df)} benchmarks")
        
        # Mostrar tabla
        display_df = filtered_df[['id', 'filename', 'family', 'difficulty', 
                                   'num_variables', 'num_clauses']].copy()
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # Selección de IDs
        st.markdown("---")
        st.subheader("Eliminar benchmarks seleccionados")
        
        # Input de IDs
        ids_input = st.text_area(
            "IDs a eliminar (separados por comas)",
            help="Ejemplo: 1, 5, 10, 15-20",
            placeholder="1, 2, 3 o 10-20"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("🗑️ Eliminar Seleccionados", type="primary"):
                if not ids_input:
                    st.error("❌ Debes ingresar al menos un ID")
                else:
                    # Parse IDs
                    ids_to_delete = []
                    
                    for part in ids_input.split(','):
                        part = part.strip()
                        
                        if '-' in part:
                            # Range
                            start, end = map(int, part.split('-'))
                            ids_to_delete.extend(range(start, end + 1))
                        else:
                            # Single ID
                            ids_to_delete.append(int(part))
                    
                    # Eliminar
                    with st.spinner(f"Eliminando {len(ids_to_delete)} benchmarks..."):
                        result = db.delete_benchmarks_batch(ids_to_delete)
                    
                    st.success(f"✅ Eliminados: {result['deleted']}")
                    
                    if result['failed'] > 0:
                        st.error(f"❌ Fallidos: {result['failed']}")
                    
                    if result['has_runs'] > 0:
                        st.warning(f"⚠️ Con ejecuciones (no eliminados): {result['has_runs']}")
                    
                    if result['errors']:
                        with st.expander("Ver errores"):
                            for error in result['errors']:
                                st.error(f"ID {error['id']}: {error['error']}")
                    
                    st.rerun()

# ===== ACTION 5: Limpieza Automática =====
elif maintenance_action == "🧹 Limpieza Automática":
    st.header("🧹 Limpieza Automática de Base de Datos")
    
    st.info("""
    **Esta herramienta realizará las siguientes acciones:**
    1. Detectar y eliminar benchmarks duplicados (mantiene la versión más completa)
    2. Opcionalmente eliminar benchmarks con datos incompletos
    3. Generar reporte de limpieza
    
    ⚠️ **Nota:** No se eliminarán benchmarks que tengan ejecuciones asociadas.
    """)
    
    st.markdown("---")
    
    # Pre-scan
    st.subheader("📊 Análisis Previo")
    
    with st.spinner("Analizando base de datos..."):
        duplicates = db.find_duplicate_benchmarks()
        invalid = db.find_invalid_benchmarks()
        completeness = db.get_benchmark_completeness()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🔄 Duplicados Encontrados", len(duplicates))
    with col2:
        st.metric("❌ Benchmarks Inválidos", len(invalid))
    with col3:
        total_issues = len(duplicates) + len(invalid)
        st.metric("⚠️ Total de Problemas", total_issues)
    
    # Show details of invalid benchmarks
    if invalid:
        with st.expander("📋 Ver Benchmarks Inválidos"):
            invalid_df = pd.DataFrame(invalid)
            st.dataframe(
                invalid_df[['id', 'filename', 'family', 'difficulty', 'num_variables', 'num_clauses']],
                use_container_width=True
            )
    
    if total_issues == 0:
        st.success("✅ ¡Base de datos en perfecto estado! No se requiere limpieza.")
    else:
        st.markdown("---")
        st.subheader("⚙️ Configuración de Limpieza")
        
        clean_duplicates = st.checkbox("🔄 Limpiar duplicados", value=True)
        clean_invalid = st.checkbox("❌ Eliminar benchmarks inválidos", value=False)
        
        if clean_invalid:
            st.warning("⚠️ **Advertencia:** Esto eliminará benchmarks con datos incompletos permanentemente")
            st.info(f"Se intentarán eliminar {len(invalid)} benchmarks inválidos")
        
        st.markdown("---")
        
        if st.button("🚀 Ejecutar Limpieza Automática", type="primary"):
            progress_bar = st.progress(0)
            status = st.empty()
            
            results = {
                'duplicates_cleaned': 0,
                'invalid_deleted': 0,
                'invalid_skipped': 0,
                'errors': []
            }
            
            # Step 1: Clean duplicates
            if clean_duplicates and duplicates:
                status.text("🔄 Limpiando duplicados...")
                try:
                    dup_stats = db.cleanup_all_duplicates()
                    results['duplicates_cleaned'] = dup_stats['versions_deleted']
                    status.text(f"✅ Duplicados eliminados: {results['duplicates_cleaned']}")
                except Exception as e:
                    st.error(f"Error limpiando duplicados: {e}")
                    results['errors'].append({'step': 'duplicates', 'error': str(e)})
                
                progress_bar.progress(0.5)
            
            # Step 2: Clean invalid
            if clean_invalid and invalid:
                status.text(f"❌ Eliminando {len(invalid)} benchmarks inválidos...")
                try:
                    invalid_ids = [b['id'] for b in invalid]
                    
                    status.text(f"Procesando {len(invalid_ids)} benchmarks...")
                    
                    invalid_stats = db.delete_benchmarks_batch(invalid_ids)
                    
                    results['invalid_deleted'] = invalid_stats['deleted']
                    results['invalid_skipped'] = invalid_stats['has_runs']
                    results['errors'].extend(invalid_stats.get('errors', []))
                    
                    status.text(f"✅ Inválidos eliminados: {results['invalid_deleted']}")
                    
                except Exception as e:
                    st.error(f"Error eliminando benchmarks inválidos: {e}")
                    results['errors'].append({'step': 'invalid', 'error': str(e)})
                
                progress_bar.progress(1.0)
            
            # Clear progress indicators
            progress_bar.empty()
            status.empty()
            
            # Show Results
            st.success("✅ Limpieza Completada")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔄 Duplicados Eliminados", results['duplicates_cleaned'])
            with col2:
                st.metric("❌ Inválidos Eliminados", results['invalid_deleted'])
            with col3:
                st.metric("⏭️ Omitidos (con runs)", results['invalid_skipped'])
            
            # Show detailed results
            if results['invalid_deleted'] > 0 or results['invalid_skipped'] > 0:
                st.markdown("---")
                st.subheader("📊 Detalles de la Limpieza")
                
                if results['invalid_deleted'] > 0:
                    st.success(f"✅ Se eliminaron {results['invalid_deleted']} benchmarks inválidos sin ejecuciones")
                
                if results['invalid_skipped'] > 0:
                    st.warning(f"⚠️ Se omitieron {results['invalid_skipped']} benchmarks que tienen ejecuciones asociadas")
            
            # Show errors if any
            if results['errors']:
                st.markdown("---")
                with st.expander("⚠️ Ver Errores y Advertencias"):
                    for error in results['errors']:
                        if 'filename' in error:
                            st.warning(f"**{error.get('filename', 'Unknown')}** (ID {error['id']}): {error['error']}")
                        else:
                            st.error(f"{error}")
            
            st.balloons()
            
            # Refresh button
            st.markdown("---")
            if st.button("🔄 Refrescar Estado", type="primary"):
                st.rerun()

# ===== Footer =====
st.markdown("---")
st.caption("🧹 Herramientas de mantenimiento de base de datos - SAT Benchmark Suite")