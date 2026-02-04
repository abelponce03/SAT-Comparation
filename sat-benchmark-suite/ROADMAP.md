# 📋 SAT Benchmark Suite - Development Roadmap

## ✅ Fase 1: Estructura Base (COMPLETADO)

### Infraestructura
- ✅ Estructura de directorios completa
- ✅ Base de datos SQLite con schema completo
- ✅ Sistema de configuración (YAML + JSON)
- ✅ Requirements.txt con todas las dependencias
- ✅ Logging y helpers utilities
- ✅ CNF parser para extraer metadata

### Aplicación Base
- ✅ Página principal con overview
- ✅ Configuración de Streamlit
- ✅ Sidebar con estadísticas
- ✅ Sistema de temas y CSS personalizado

### Página 1: Setup de Solvers
- ✅ Listado de solvers registrados
- ✅ Upload de archivos ZIP/TAR.GZ
- ✅ Extracción automática
- ✅ Auto-detección de build system
- ✅ Templates para solvers conocidos
- ✅ Sistema de compilación con logs en tiempo real
- ✅ Agregar solver pre-compilado
- ✅ Agregar desde directorio local

### Scripts Auxiliares
- ✅ Script de inicio (start.py)
- ✅ Script de migración de datos existentes
- ✅ README completo con documentación

---

## 🚧 Fase 2: Gestión de Benchmarks (PRÓXIMO)

### Página 2: Manage Benchmarks
- [ ] Escanear directorio de benchmarks
- [ ] Upload individual/múltiple de CNF files
- [ ] Tabla interactiva con filtros (familia, dificultad, tamaño)
- [ ] Vista de detalles de benchmark
- [ ] Clasificación automática por familia
- [ ] Edición manual de metadata
- [ ] Búsqueda y filtrado avanzado
- [ ] Exportar lista de benchmarks
- [ ] Importar desde SAT competition
- [ ] Validación de archivos CNF
- [ ] Gestión de tags personalizados
- [ ] Estadísticas de la colección

### Backend Necesario
- [ ] `benchmark_manager.py`: Clase para gestionar benchmarks
- [ ] Funciones de búsqueda y filtrado eficientes
- [ ] Cache para metadata de benchmarks grandes
- [ ] Validador de integridad de archivos

---

## 🚧 Fase 3: Ejecución de Experimentos (ALTA PRIORIDAD)

### Página 3: Run Experiments
- [ ] Crear nuevo experimento (nombre, descripción)
- [ ] Selección múltiple de solvers
- [ ] Selección múltiple de benchmarks con filtros
- [ ] Configuración: timeout, memory limit, parallel jobs
- [ ] Vista previa: X solvers × Y benchmarks = Z runs
- [ ] Botón de lanzamiento
- [ ] Monitoreo en tiempo real:
  - [ ] Progress bar global
  - [ ] Progress por solver
  - [ ] Tabla de últimos completados
  - [ ] Streaming de logs
  - [ ] Actualización automática cada 5s
- [ ] Controles: Pausar / Reanudar / Cancelar
- [ ] Estimación de tiempo restante
- [ ] Checkpoint automático cada 100 runs

### Backend: Executor
- [ ] `executor.py`: Sistema de ejecución paralela
  - [ ] Pool de workers con multiprocessing
  - [ ] Queue de tareas
  - [ ] Timeout management con subprocess
  - [ ] Memory monitoring con psutil
  - [ ] Signal handling (SIGTERM, SIGKILL)
  - [ ] Parsing de output del solver
  - [ ] Checkpoint y recovery
  - [ ] Error handling robusto

### Backend: Monitor
- [ ] `monitor.py`: Sistema de monitoreo
  - [ ] Estado global del experimento
  - [ ] Métricas por solver
  - [ ] Queue de resultados
  - [ ] Streaming de logs
  - [ ] Detección de problemas (solver crashed, OOM, etc.)

### Parsers de Output
- [ ] Parser para MiniSat
- [ ] Parser para CaDiCaL
- [ ] Parser para Glucose
- [ ] Parser para CryptoMiniSat
- [ ] Parser genérico (SAT/UNSAT básico)
- [ ] Extracción de métricas del solver

---

## 🚧 Fase 4: Visualización de Resultados

### Página 4: View Results
- [ ] Tabla interactiva con todos los runs
- [ ] Filtros: experimento, solver, benchmark, resultado
- [ ] Búsqueda full-text
- [ ] Ordenamiento por columna
- [ ] Paginación para grandes datasets
- [ ] Vista de detalles de un run específico
- [ ] Comparación lado a lado (2 runs)
- [ ] Exportar a CSV/Excel
- [ ] Exportar filtrado
- [ ] Estadísticas resumidas del experimento

### Backend
- [ ] Queries optimizadas con índices
- [ ] Cache de resultados frecuentes
- [ ] Formateo de métricas para display
- [ ] Generación de CSV/Excel

---

## 🚧 Fase 5: Análisis Estadístico (ALTA PRIORIDAD)

### Página 5: Statistical Analysis
- [ ] Selector de experimento
- [ ] Selector de métricas a analizar

#### Análisis Básico
- [ ] Resumen por solver (solved, timeout, error)
- [ ] Tabla de PAR-2 scores
- [ ] Ranking de solvers
- [ ] Tiempo promedio por familia

#### PAR-2 Analysis
- [ ] Cálculo de PAR-2 score
- [ ] Tabla comparativa
- [ ] Gráfico de barras

#### Virtual Best Solver (VBS)
- [ ] Cálculo de VBS (mejor solver por benchmark)
- [ ] Comparación VBS vs cada solver real
- [ ] Porcentaje de contribución de cada solver al VBS

#### Comparaciones Pairwise
- [ ] Scatter plot Solver A vs Solver B
- [ ] Win/Loss/Tie analysis
- [ ] Speedup analysis
- [ ] Test de significancia estadística (Wilcoxon, t-test)
- [ ] Confidence intervals

#### Análisis por Familia
- [ ] Performance por familia de benchmarks
- [ ] Heatmap: solvers × familias
- [ ] Mejores solvers por familia

### Backend: statistics.py
- [ ] Función para PAR-2
- [ ] Función para VBS
- [ ] Tests estadísticos (scipy.stats)
- [ ] Bootstrap confidence intervals
- [ ] Correlación entre métricas
- [ ] Análisis de outliers

---

## 🚧 Fase 6: Visualizaciones

### Página 6: Visualizations
- [ ] Selector de experimento
- [ ] Selector de solvers a comparar
- [ ] Configuración de plots

#### Cactus Plot
- [ ] Implementación con Plotly
- [ ] Eje X: benchmarks resueltos (ordenados)
- [ ] Eje Y: tiempo acumulado
- [ ] Línea por solver
- [ ] Exportar como PNG/SVG
- [ ] Interactividad (zoom, pan, hover)

#### Scatter Plot
- [ ] Solver A vs Solver B
- [ ] Puntos por benchmark
- [ ] Línea de referencia (y=x)
- [ ] Color por resultado
- [ ] Escala log opcional
- [ ] Zoom interactivo

#### Performance Profile
- [ ] CDF de performance ratio
- [ ] Curvas por solver
- [ ] Interpretación clara

#### Heatmap
- [ ] Solvers × Benchmarks
- [ ] Color según resultado o tiempo
- [ ] Clustering opcional
- [ ] Exportable

#### Box Plots
- [ ] Distribución de tiempos por solver
- [ ] Por familia de benchmarks

#### Histogramas
- [ ] Distribución de métricas
- [ ] Comparación entre solvers

### Backend: plots.py
- [ ] Función para cactus plot
- [ ] Función para scatter plot
- [ ] Función para performance profile
- [ ] Función para heatmap
- [ ] Función para box plots
- [ ] Utils para preparar datos
- [ ] Templates de estilo consistentes

---

## 🚧 Fase 7: Sistema de Reportes

### Página 7: Reports
- [ ] Selector de experimento
- [ ] Plantillas de reporte (Standard, Extended, Custom)
- [ ] Configuración:
  - [ ] Incluir qué secciones
  - [ ] Qué plots incluir
  - [ ] Formato (PDF, HTML, Markdown)
- [ ] Vista previa del reporte
- [ ] Generación y descarga

#### Secciones del Reporte
- [ ] Executive Summary
- [ ] Experiment Configuration
- [ ] Solvers Description
- [ ] Benchmarks Overview
- [ ] Results Summary (tabla)
- [ ] Statistical Analysis
- [ ] Visualizations (plots embebidos)
- [ ] Conclusions

### Backend: report_generator.py
- [ ] Templates con Jinja2 o similar
- [ ] Generación PDF con ReportLab
- [ ] Generación HTML
- [ ] Generación Markdown
- [ ] Embedding de plots (base64 para HTML/PDF)
- [ ] Formateo de tablas
- [ ] Sistema de secciones modulares

---

## 🔧 Mejoras y Features Adicionales

### Sistema
- [ ] Sistema de plugins para nuevos solvers
- [ ] API REST para automatización externa
- [ ] Autenticación multi-usuario (opcional)
- [ ] Sistema de notificaciones (email cuando termina experimento)
- [ ] Backup automático de base de datos
- [ ] Importar/Exportar configuraciones completas
- [ ] Modo "dry-run" para testear configuración

### Optimizaciones
- [ ] Cache de queries frecuentes
- [ ] Paginación en tablas grandes
- [ ] Lazy loading de benchmarks
- [ ] Compresión de outputs de solvers
- [ ] Índices adicionales en base de datos
- [ ] Cleanup de archivos temporales

### Análisis Avanzado
- [ ] Machine Learning: predecir dificultad de benchmark
- [ ] Clustering de benchmarks similares
- [ ] Feature extraction de CNF files
- [ ] Portfolio solver simulation
- [ ] Análisis de sensibilidad de parámetros

### Integración
- [ ] Import desde SAT Competition results
- [ ] Export a formato EDACC
- [ ] Compatibilidad con Slurm (HPC clusters)
- [ ] Docker containerization
- [ ] CI/CD para testing automático

---

## 📅 Cronograma Sugerido

### Semana 1-2: Fase 2 (Benchmarks)
- Implementar gestión completa de benchmarks
- Testing con tus 400 benchmarks existentes

### Semana 3-4: Fase 3 (Experiments)
- Sistema de ejecución paralela
- Monitoreo en tiempo real
- Testing con experimentos pequeños

### Semana 5: Fase 4 (Results)
- Vista de resultados
- Exportación
- Testing con datos migrados

### Semana 6-7: Fase 5 (Statistics)
- Análisis estadístico completo
- PAR-2, VBS, comparaciones
- Validación de métricas

### Semana 8: Fase 6 (Visualizations)
- Todos los plots principales
- Interactividad y exportación

### Semana 9: Fase 7 (Reports)
- Sistema de reportes
- Templates y generación

### Semana 10: Testing & Polish
- Bug fixes
- Optimizaciones
- Documentación

---

## 🎯 Prioridades Inmediatas

1. **AHORA**: Migrar tus datos existentes
   ```bash
   python migrate_existing_data.py
   ```

2. **SIGUIENTE**: Implementar Fase 2 (Benchmarks)
   - Para que puedas gestionar tus 400 CNFs

3. **LUEGO**: Implementar Fase 3 (Experiments)
   - Para que puedas lanzar nuevos experimentos

4. **DESPUÉS**: Análisis y Visualizaciones
   - Para comparar solvers

---

## 📝 Notas de Desarrollo

### Decisiones de Arquitectura
- **SQLite**: Suficiente para millones de runs, sin necesidad de server
- **Multiprocessing**: Mejor que threading para CPU-bound tasks
- **Streamlit**: Rápido desarrollo, UI moderna, pero limitado para real-time
- **Plotly**: Gráficos interactivos, mejor que matplotlib para web

### Consideraciones
- **Timeout handling**: Usar `signal` en Linux, `subprocess.communicate(timeout=...)` en Windows
- **Memory limits**: Difícil en Windows, posible con `psutil` monitoring
- **Parallel execution**: Cuidado con race conditions en DB (usar locks)
- **Large datasets**: Implementar paginación y streaming

### Testing
- Probar con 5-10 benchmarks primero
- Validar parsers con outputs reales
- Verificar memory leaks en ejecución larga
- Testing en Windows y Linux (diferencias en subprocess)

---

## ❓ Preguntas para Continuar

1. **¿Quieres que empiece con la Fase 2 (Benchmarks) ahora?**
   - O prefieres primero probar la estructura base

2. **¿Tienes solvers adicionales que quieras agregar?**
   - Puedo configurar templates específicos

3. **¿Qué análisis estadísticos son más importantes para tu tesis?**
   - PAR-2, VBS, otros?

4. **¿Necesitas features específicas no mencionadas?**
   - Puedo ajustar el roadmap

---

**Siguiente paso: ¿Qué quieres que implemente primero?** 🚀
