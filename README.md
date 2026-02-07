<div align="center">

# ⚡ SAT Benchmark Suite v2.0

### Plataforma Integral para Benchmarking, Análisis Estadístico Riguroso y Modelado de Problemas SAT

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-Academic-green.svg)](#licencia)

</div>

---

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Stack Tecnológico](#-stack-tecnológico)
- [Módulos de la Aplicación](#-módulos-de-la-aplicación)
  - [Dashboard](#1--dashboard)
  - [Solvers](#2-%EF%B8%8F-solvers)
  - [Benchmarks](#3--benchmarks)
  - [Experiments](#4--experiments)
  - [Analysis](#5--analysis)
  - [Visualization](#6--visualization)
  - [SAT Modeler](#7--sat-modeler)
- [Solvers Soportados](#-solvers-soportados)
- [Pipeline de Análisis Riguroso](#-pipeline-de-análisis-riguroso)
- [Base de Datos](#-base-de-datos)
- [Instalación y Despliegue](#-instalación-y-despliegue)
- [Uso Rápido](#-uso-rápido)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API REST](#-api-rest)
- [Lenguaje del SAT Modeler](#-lenguaje-del-sat-modeler)
- [Metodología Estadística](#-metodología-estadística)
- [Exportación y Reportes](#-exportación-y-reportes)
- [Contribuciones](#-contribuciones)

---

## 🎯 Descripción General

**SAT Benchmark Suite** es una plataforma web completa diseñada para la **evaluación comparativa rigurosa** de solvers SAT (Boolean Satisfiability Problem). El sistema integra todo el ciclo de vida del benchmarking: desde la gestión de solvers y benchmarks, pasando por la ejecución controlada de experimentos, hasta el análisis estadístico con rigor académico siguiendo la metodología de **Demšar (2006)** y las prácticas de la **SAT Competition**.

### Características Principales

- 🔬 **Pipeline estadístico riguroso**: Tests de Friedman, Wilcoxon, Mann-Whitney U, post-hoc Nemenyi/Conover con correcciones de Bonferroni, Holm y Benjamini-Hochberg
- 📊 **Métricas estándar**: PAR-2, PAR-10, Virtual Best Solver (VBS), tasas de resolución, análisis CDCL
- 📈 **Visualizaciones publicables**: Cactus plots, ECDF, scatter plots, heatmaps, diagramas de diferencia crítica, análisis de supervivencia
- 🔢 **Intervalos de confianza Bootstrap**: Método BCa (Bias-Corrected and Accelerated) con 10,000 réplicas
- 🧮 **SAT Modeler**: IDE integrado con lenguaje inspirado en MiniZinc para crear y resolver problemas SAT interactivamente
- 🐳 **Despliegue Docker**: Configuración completa con 3 servicios (backend, frontend, nginx)
- 📄 **Reportes automáticos**: Generación de reportes HTML/PDF con gráficos embebidos
- ⚡ **Tiempo real**: WebSocket para monitoreo en vivo de la ejecución de experimentos

---

## 🏗 Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    SAT Benchmark Suite v2.0                  │
├─────────────┬──────────────────────┬────────────────────────┤
│   Frontend  │       Nginx          │       Backend          │
│  React 18   │   Reverse Proxy      │      FastAPI           │
│  Vite 5     │   (Producción)       │    Python 3.11         │
│  TypeScript │                      │                        │
│  TailwindCSS│   Puerto: 80         │    Puerto: 8000        │
│  Recharts   │   Rate Limiting      │    SQLite + SQLAlchemy │
│             │   Gzip + SPA         │    SciPy + NumPy       │
│  Puerto:    │   Fallback           │    Matplotlib/Seaborn  │
│   5173      │                      │    Bootstrap CI        │
├─────────────┴──────────────────────┴────────────────────────┤
│                      Docker Compose                         │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────────────┐│
│  │ frontend │   │    nginx     │   │      backend         ││
│  │ node:20  │   │ nginx:alpine │   │  python:3.11-slim    ││
│  │ alpine   │   │ (production) │   │  + gcc/make (solvers)││
│  └──────────┘   └──────────────┘   └──────────────────────┘│
│                                                             │
│  Volúmenes Persistentes:                                    │
│  📁 data/ → SQLite DB, resultados, modelos                  │
│  📁 solvers/ → Binarios compilados de Kissat, MiniSat       │
│  📁 benchmarks/ → Archivos CNF                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠 Stack Tecnológico

### Backend
| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| **Python** | 3.11 | Lenguaje principal |
| **FastAPI** | 0.109.0 | Framework API REST + WebSocket |
| **Uvicorn** | 0.27.0 | Servidor ASGI |
| **SQLAlchemy** | 2.0.25 | ORM para SQLite |
| **Pandas** | 2.1.4 | Procesamiento de datos |
| **NumPy** | 1.26.3 | Cálculos numéricos |
| **SciPy** | 1.12.0 | Tests estadísticos |
| **Matplotlib** | 3.8.3 | Generación de gráficos |
| **Seaborn** | 0.13.2 | Visualizaciones estadísticas |
| **Jinja2** | 3.1.3 | Plantillas para reportes |
| **Pydantic** | 2.x | Validación de datos |

### Frontend
| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| **React** | 18 | Framework UI |
| **TypeScript** | 5.3 | Tipado estático |
| **Vite** | 5.x | Build tool + HMR |
| **TailwindCSS** | 3.4 | Estilos utility-first |
| **Recharts** | 2.x | Gráficos interactivos |
| **TanStack Query** | 5.x | Data fetching + caching |
| **Zustand** | 4.x | State management |
| **React Router** | 6.x | Enrutamiento SPA |
| **Lucide React** | — | Iconografía |

### Infraestructura
| Tecnología | Propósito |
|-----------|-----------|
| **Docker Compose** | Orquestación de contenedores |
| **Nginx** | Reverse proxy + servir estáticos |
| **SQLite** | Base de datos embebida |

---

## 📱 Módulos de la Aplicación

### 1. 📊 Dashboard

Panel de control con métricas generales del sistema:

- **Contadores globales**: Número de solvers, benchmarks y experimentos
- **Distribución de resultados**: Gráfico de SAT/UNSAT/TIMEOUT/ERROR
- **Actividad reciente**: Últimos experimentos ejecutados con estado y progreso
- **Estado del sistema**: Resumen de solvers disponibles y listos

### 2. ⚙️ Solvers

Gestión completa de los solvers SAT disponibles:

- **Catálogo de solvers**: Lista de solvers pre-configurados con información detallada
- **Detección automática de versión**: Ejecución de `--version` para verificar la versión real instalada
- **Matriz de comparación**: Tabla de características lado a lado (tipo SAT, técnica CDCL, features especiales)
- **Test de ejecutabilidad**: Verificación de que el binario del solver funciona correctamente
- **Información detallada**: Descripción, categoría (competition/educational), features técnicas por solver

### 3. 📁 Benchmarks

Gestión de instancias CNF con capacidades avanzadas:

- **Paginación server-side**: Navegación eficiente en colecciones grandes (25 por página)
- **Filtrado avanzado**: Por familia (circuit, crypto, planning, graph, etc.), dificultad (easy/medium/hard), búsqueda de texto
- **Estadísticas agregadas**: Promedio de variables, cláusulas, distribución de dificultad (calculadas con SQL)
- **Upload de archivos**: Drag & drop con auto-clasificación de familia y estimación de dificultad
- **Escaneo de directorio**: Importación masiva de archivos CNF desde una carpeta
- **Preview de CNF**: Visualización de las primeras líneas del archivo DIMACS
- **Metadatos calculados**: Variables, cláusulas, ratio cláusulas/variables, tamaño en bytes, hash MD5

### 4. 🧪 Experiments

Motor de ejecución de benchmarks con monitoreo en tiempo real:

- **Creación de experimentos**: Selección flexible de solvers y benchmarks (multi-select)
- **Configuración**: Timeout (default: 5000s), límite de memoria (default: 8192 MB), repeticiones
- **Ejecución en background**: Con barra de progreso en tiempo real vía WebSocket
- **Monitoreo detallado**: Solver actual, benchmark actual, porcentaje completado
- **Control de ejecución**: Start/Stop con cleanup de procesos
- **Resultados detallados por run**:
  - Resultado: SAT/UNSAT/TIMEOUT/ERROR/UNKNOWN
  - Tiempos: Wall time, CPU time, User time, System time
  - Memoria: Máxima y promedio (KB)
  - **Métricas CDCL**: Conflictos, decisiones, propagaciones, restarts, cláusulas aprendidas/eliminadas
  - Exit codes estándar: 10 = SAT, 20 = UNSAT
  - Salida raw del solver (hasta 10 KB)

### 5. 📈 Analysis

Módulo de análisis estadístico completo con **10 pestañas**:

| Pestaña | Contenido |
|---------|-----------|
| **Overview** | PAR-2 ranking, solved counts, resumen general |
| **Metrics** | PAR-2, PAR-10, VBS, solve matrix, instancias únicas resueltas |
| **Statistical Tests** | Wilcoxon signed-rank, Mann-Whitney U, Sign test, Friedman, paired/independent t-tests |
| **Bootstrap CI** | Intervalos de confianza BCa con 10,000 réplicas |
| **Pairwise Comparison** | Comparación detallada entre pares de solvers |
| **Family Analysis** | PAR-2 y rendimiento por familia de benchmarks |
| **CDCL Metrics** | Análisis de métricas internas de los solvers (conflicts/s, decisions/s) |
| **Effect Sizes** | Cohen's d, Vargha-Delaney A measure |
| **Normality Tests** | Shapiro-Wilk, D'Agostino-Pearson, Anderson-Darling |
| **CSV Export** | Exportación de cualquier tabla de análisis |

### 6. 📉 Visualization

Visualizaciones interactivas con **5 tipos de gráficos**:

| Gráfico | Descripción |
|---------|-------------|
| **Cactus Plot** | Instancias resueltas vs. tiempo (curva acumulativa) |
| **Scatter Plot** | Comparación pairwise de tiempos entre solvers |
| **ECDF** | Distribución empírica acumulativa / Performance Profile |
| **PAR-2 / Solved** | Barras de PAR-2 score y número de instancias resueltas |
| **Heatmap** | Matriz solver × benchmark con tiempos de resolución |

Cada gráfico incluye controles interactivos (tooltips, zoom, filtros, selección de solvers).

### 7. 🧮 SAT Modeler

IDE integrado con lenguaje propio para modelar y resolver problemas SAT:

- **Editor de código**: Con resaltado de sintaxis token-based (9 categorías de colores), números de línea y scroll sincronizado
- **Validación en tiempo real**: Parsing con debounce de 400ms, errores mostrados inline
- **Panel de ejemplos**: 4 problemas pre-definidos (Graph Coloring, Pigeonhole, Logic Puzzle, N-Queens)
- **Modelos guardados**: Crear, guardar y cargar modelos personalizados
- **Referencia del lenguaje**: Documentación completa accesible desde la sidebar
- **Compilación a CNF**: Traducción Tseitin con encodings de cardinalidad
- **Resolución directa**: Selección de solver (Kissat/MiniSat) con timeout configurable
- **Resultados interactivos**: Tabla de asignaciones, visor DIMACS con copy/download, output del solver

---

## 🔧 Solvers Soportados

| Solver | Versión | Estado | Categoría | Técnicas Clave |
|--------|---------|--------|-----------|---------------|
| **Kissat** | 4.0.4 | ✅ Listo | Competition | CDCL, Preprocessing, Inprocessing, Vivification, Lucky phases |
| **MiniSat** | 2.2.0 | ✅ Listo | Educational | CDCL, VSIDS, Two-watched literals, Phase saving |
| **CaDiCaL** | 2.1.3 | ⬚ No instalado | Competition | CDCL, Chronological backtracking, BVE |
| **CryptoMiniSat** | 5.11.22 | ⬚ No instalado | Competition | CDCL, XOR reasoning, Gaussian elimination |

Los solvers `Kissat` y `MiniSat` vienen compilados y listos para usar dentro del contenedor Docker. `CaDiCaL` y `CryptoMiniSat` pueden ser agregados compilando sus binarios en el directorio `solvers/`.

---

## 🔬 Pipeline de Análisis Riguroso

El pipeline estadístico sigue las mejores prácticas de la comunidad SAT y la metodología de Demšar (2006) para comparación de clasificadores/algoritmos:

```
┌─────────────────────────────────────────────────────────────┐
│              Pipeline de Análisis Estadístico                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. MÉTRICAS BASE                                           │
│     ├── PAR-2 Score (Penalized Average Runtime × 2)         │
│     ├── PAR-10 Score (para comparación con literatura)      │
│     ├── Virtual Best Solver (VBS)                           │
│     ├── Tasa de resolución (solved/total)                   │
│     ├── Solve Matrix (instancias únicas/comunes)            │
│     └── Ranking por familia de benchmarks                   │
│                                                             │
│  2. TESTS DE NORMALIDAD                                     │
│     ├── Shapiro-Wilk (N < 5000)                             │
│     ├── D'Agostino-Pearson (N ≥ 20)                         │
│     └── Anderson-Darling (robusto)                          │
│                                                             │
│  3. TESTS ESTADÍSTICOS                                      │
│     ├── 2 Solvers:                                          │
│     │   ├── Wilcoxon Signed-Rank (pareado, no paramétrico)  │
│     │   ├── Mann-Whitney U (independiente)                  │
│     │   └── Sign Test                                       │
│     └── k ≥ 3 Solvers:                                      │
│         ├── Friedman Test (ANOVA no paramétrico)            │
│         ├── Nemenyi Post-hoc (pairwise)                     │
│         └── Conover Test (más potente)                      │
│                                                             │
│  4. CORRECCIONES MÚLTIPLES                                  │
│     ├── Bonferroni (conservador)                            │
│     ├── Holm step-down (menos conservador)                  │
│     └── Benjamini-Hochberg FDR (control de tasa)            │
│                                                             │
│  5. TAMAÑOS DE EFECTO                                       │
│     ├── Cohen's d (diferencia estandarizada)                │
│     └── Vargha-Delaney A (probabilístico, no paramétrico)   │
│                                                             │
│  6. BOOTSTRAP                                               │
│     ├── Intervalos de confianza BCa (10,000 réplicas)       │
│     ├── Bootstrap para diferencias de medias                │
│     └── Seed fijo (42) para reproducibilidad                │
│                                                             │
│  7. VISUALIZACIONES                                         │
│     ├── Cactus Plot (instancias vs. tiempo)                 │
│     ├── ECDF / Performance Profile                          │
│     ├── Boxplot con intervalos de confianza                 │
│     ├── Scatter pairwise (log-log)                          │
│     ├── Heatmap (solver × familia)                          │
│     ├── Critical Difference Diagram (Demšar)                │
│     ├── Survival Analysis Plot                              │
│     └── PAR-2 Bar Chart                                     │
│                                                             │
│  8. REPORTES                                                │
│     ├── HTML standalone con gráficos embebidos (base64)     │
│     ├── PDF (via weasyprint)                                │
│     └── CSV export (10+ tablas de datos)                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄 Base de Datos

SQLite con 4 tablas principales y esquema optimizado con índices:

### Tablas

**`solvers`** — Catálogo de solvers SAT
- `id`, `name` (UNIQUE), `version`, `path`, `description`, `category`, `status`, `features` (JSON)

**`benchmarks`** — Instancias CNF
- `id`, `name` (UNIQUE), `file_path`, `family`, `num_variables`, `num_clauses`, `file_size_bytes`, `clause_variable_ratio`, `difficulty`, `hash` (MD5)

**`experiments`** — Experimentos de benchmarking
- `id`, `name` (UNIQUE), `description`, `status`, `timeout_seconds`, `memory_limit_mb`, `repetitions`, `total_runs`, `completed_runs`, `failed_runs`, `config` (JSON: solver_ids, benchmark_ids)

**`runs`** — Resultados individuales (tabla principal)
- `id`, `experiment_id` (FK), `solver_id` (FK), `benchmark_id` (FK)
- **Resultado**: `result` (SAT/UNSAT/TIMEOUT/ERROR), `exit_code`, `verified`
- **Tiempos**: `wall_time_seconds`, `cpu_time_seconds`, `user_time_seconds`, `system_time_seconds`
- **Memoria**: `max_memory_kb`, `avg_memory_kb`
- **CDCL**: `conflicts`, `decisions`, `propagations`, `restarts`, `learnt_clauses`, `deleted_clauses`
- **Meta**: `solver_output` (raw, ≤10KB), `par2_score` (pre-calculado), `hostname`

### Índices
- `idx_runs_experiment`, `idx_runs_solver`, `idx_runs_benchmark`, `idx_benchmarks_family`

---

## 🚀 Instalación y Despliegue

### Prerrequisitos

- Docker Engine ≥ 20.x
- Docker Compose ≥ 2.x
- 4 GB RAM mínimo (recomendado 8 GB para análisis estadístico)

### Inicio Rápido

```bash
# Clonar el repositorio
git clone https://github.com/<usuario>/SAT-Comparation.git
cd SAT-Comparation/sat-benchmark-react

# Levantar los servicios (desarrollo)
sudo docker-compose up -d

# Verificar que los servicios están corriendo
sudo docker-compose ps
```

### Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Frontend** | http://localhost:5173 | Interfaz web (desarrollo) |
| **Backend API** | http://localhost:8000 | API REST + Docs |
| **API Docs** | http://localhost:8000/docs | Swagger UI (auto-generada) |
| **Producción** | http://localhost:80 | Nginx reverse proxy |

### Modo Producción

```bash
# Construir y levantar con perfil de producción
sudo docker-compose --profile production up -d

# La app estará disponible en http://localhost
```

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///data/experiments.db` | Ruta a la base de datos |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | URL del servidor Ollama (AI) |
| `VITE_API_URL` | `http://localhost:8000` | URL del backend para el frontend |

---

## 💡 Uso Rápido

### 1. Verificar Solvers
Ir a **Solvers** → verificar que Kissat y MiniSat están en estado "ready".

### 2. Cargar Benchmarks
Ir a **Benchmarks** → usar **Upload** para cargar archivos `.cnf` o **Scan** para importar desde directorio.

### 3. Crear y Ejecutar Experimento
Ir a **Experiments** → **New Experiment** → seleccionar solvers y benchmarks → **Start**.

### 4. Analizar Resultados
Una vez completado el experimento:
- **Analysis** → Explorar las 10 pestañas de análisis estadístico
- **Visualization** → Generar gráficos interactivos
- Exportar resultados como CSV o generar reporte HTML

### 5. Modelar Problemas SAT (opcional)
Ir a **SAT Modeler** → escribir modelo en lenguaje SAT → **Solve** → ver resultados.

---

## 📂 Estructura del Proyecto

```
SAT-Comparation/
└── sat-benchmark-react/
    ├── docker-compose.yml           # Orquestación de servicios
    │
    ├── backend/
    │   ├── Dockerfile               # Python 3.11 + herramientas de compilación
    │   ├── requirements.txt         # Dependencias Python
    │   └── app/
    │       ├── main.py              # FastAPI app + routers
    │       ├── api/                  # Endpoints REST
    │       │   ├── dashboard.py     # Estadísticas generales
    │       │   ├── solvers.py       # Gestión de solvers
    │       │   ├── benchmarks.py    # Gestión de benchmarks
    │       │   ├── experiments.py   # Motor de ejecución
    │       │   ├── analysis.py      # Análisis + visualización
    │       │   ├── rigorous_analysis.py  # Pipeline estadístico completo
    │       │   └── sat_modeler.py   # Tokenizer + Parser + Compiler + Solver
    │       ├── analysis/            # Módulos de análisis
    │       │   ├── statistics.py    # Tests estadísticos (737 líneas)
    │       │   ├── bootstrap.py     # Bootstrap BCa (366 líneas)
    │       │   ├── metrics.py       # PAR-2, VBS, rankings (391 líneas)
    │       │   ├── plots.py         # Gráficos publicables (667 líneas)
    │       │   └── reports.py       # Generación de reportes (572 líneas)
    │       ├── core/
    │       │   ├── database.py      # Esquema SQLite + queries optimizadas
    │       │   └── solver_runner.py # Ejecución de solvers + parsing CDCL
    │       └── utils/
    │           ├── cnf_parser.py    # Parser de archivos DIMACS CNF
    │           └── helpers.py       # Utilidades generales
    │
    ├── frontend/
    │   ├── Dockerfile               # Node 20 Alpine
    │   ├── package.json             # Dependencias npm
    │   └── src/
    │       ├── App.tsx              # Router principal
    │       ├── pages/
    │       │   ├── Dashboard.tsx    # Panel de control
    │       │   ├── Solvers.tsx      # Gestión de solvers
    │       │   ├── Benchmarks.tsx   # Gestión de benchmarks
    │       │   ├── Experiments.tsx  # Lista de experimentos
    │       │   ├── ExperimentDetail.tsx  # Detalle + resultados
    │       │   ├── Analysis.tsx     # 10 pestañas de análisis
    │       │   ├── Visualization.tsx # 5 tipos de gráficos
    │       │   └── SATModeler.tsx   # IDE de modelado SAT
    │       ├── components/
    │       │   └── layout/
    │       │       └── Layout.tsx   # Sidebar + navegación
    │       └── services/
    │           └── api.ts           # Cliente HTTP (axios)
    │
    ├── nginx/
    │   └── nginx.conf               # Reverse proxy + rate limiting
    │
    ├── data/                        # Volumen persistente
    │   ├── experiments.db           # Base de datos SQLite
    │   ├── models/                  # Modelos SAT guardados
    │   └── generated_cnf/           # CNF generados
    │
    ├── solvers/                     # Binarios compilados
    │   ├── kissat/                  # Kissat 4.0.4
    │   └── minisat/                 # MiniSat 2.2.0
    │
    └── benchmarks/                  # Archivos CNF
```

---

## 🌐 API REST

La API está documentada automáticamente en Swagger UI (`http://localhost:8000/docs`). Resumen de endpoints:

| Grupo | Prefijo | Endpoints | Descripción |
|-------|---------|-----------|-------------|
| **Dashboard** | `/api/dashboard` | 2 | Estadísticas y actividad reciente |
| **Solvers** | `/api/solvers` | 8 | CRUD de solvers, test, comparación |
| **Benchmarks** | `/api/benchmarks` | 7 | CRUD, upload, scan, preview |
| **Experiments** | `/api/experiments` | 9 | CRUD, start/stop, WebSocket, progress |
| **Analysis** | `/api/analysis` | 17 | PAR-2, VBS, scatter, ECDF, CDCL, tests |
| **Rigorous** | `/api/rigorous` | 12 | Pipeline completo, bootstrap, reportes |
| **Modeler** | `/api/modeler` | 8 | Parse, compile, solve, examples, models |

**Total: 63+ endpoints REST + 1 WebSocket**

---

## 🧮 Lenguaje del SAT Modeler

El SAT Modeler incluye un lenguaje inspirado en MiniZinc con pipeline completo: **Tokenizer → Parser → AST → Tseitin CNF → DIMACS → Solver**

### Sintaxis

```minizinc
% Declaración de variables booleanas
var bool: x, y, z;

% Restricciones (operadores lógicos)
constraint x /\ y;          % AND
constraint x \/ y;          % OR
constraint not x;            % NOT (también: ~x, !x)
constraint x -> y;           % Implicación
constraint x <-> y;          % Equivalencia
constraint x xor y;          % XOR

% Restricciones de cardinalidad
constraint atmost(2, [x, y, z]);    % A lo más 2 verdaderos
constraint atleast(1, [x, y, z]);   % Al menos 1 verdadero
constraint exactly(1, [x, y, z]);   % Exactamente 1 verdadero

% Resolver
solve satisfy;
```

### Compilación a CNF

La compilación usa la **transformación de Tseitin** para preservar la equivalencia SAT con crecimiento lineal de cláusulas. Las restricciones de cardinalidad se implementan con:
- **Encoding por pares**: Para restricciones pequeñas (k ≤ 5)
- **Sequential counter encoding**: Para restricciones grandes (eficiencia polinómica)

### Ejemplos Incluidos

| Ejemplo | Descripción | Resultado |
|---------|-------------|-----------|
| **Graph Coloring** | 3-coloración de grafo con 4 nodos | SAT |
| **Pigeonhole (3,2)** | 3 palomas en 2 casillas | UNSAT |
| **Logic Puzzle** | Rompecabezas lógico con implicaciones | SAT |
| **N-Queens 4×4** | 4 reinas en tablero 4×4 | SAT |

---

## 📐 Metodología Estadística

### Tests Implementados

| Test | Tipo | Uso |
|------|------|-----|
| **Wilcoxon signed-rank** | No paramétrico, pareado | Comparación de 2 solvers (recomendado) |
| **Mann-Whitney U** | No paramétrico, independiente | Comparación de 2 muestras independientes |
| **Sign test** | No paramétrico, pareado | Alternativa robusta a Wilcoxon |
| **Friedman** | No paramétrico, k muestras | Comparación de k ≥ 3 solvers |
| **Nemenyi post-hoc** | Pairwise tras Friedman | Identificar pares significativos |
| **Conover** | Pairwise tras Friedman | Mayor potencia que Nemenyi |
| **Shapiro-Wilk** | Normalidad | Verificar distribución normal |
| **D'Agostino-Pearson** | Normalidad | Basado en skewness + kurtosis |
| **Anderson-Darling** | Normalidad | Robusto, sensible a colas |

### Correcciones para Comparaciones Múltiples

| Método | Tipo | α ajustado |
|--------|------|-----------|
| **Bonferroni** | FWER | α/m (conservador) |
| **Holm step-down** | FWER | α/(m-i+1) (menos conservador) |
| **Benjamini-Hochberg** | FDR | Control de false discovery rate |

### Tamaños de Efecto

| Medida | Interpretación |
|--------|---------------|
| **Cohen's d** | < 0.2 negligible, 0.2 pequeño, 0.5 medio, 0.8 grande |
| **Vargha-Delaney A** | 0.5 = sin efecto, > 0.71 grande (no paramétrico) |

### Bootstrap

- **Método BCa** (Bias-Corrected and Accelerated): Corrige sesgo y aceleración
- **10,000 réplicas** por defecto (configurable)
- **Seed fijo** (42) para reproducibilidad
- IC al 95% por defecto

---

## 📄 Exportación y Reportes

### CSV Export
10+ tablas exportables:
- `metrics_ranking` — Ranking PAR-2 completo
- `solve_matrix` — Matriz de instancias resueltas
- `normality` — Tests de normalidad
- `pairwise_tests` — Tests pairwise
- `post_hoc_tests` — Tests post-hoc
- `corrections` — Correcciones múltiples
- `effect_sizes` — Tamaños de efecto
- `bootstrap_ci` — Intervalos de confianza
- `pairwise_bootstrap` — Bootstrap pairwise
- `full_statistical_tests` — Todos los tests

### Reportes Automáticos
- **HTML**: Reporte standalone con gráficos base64 embebidos, secciones de resumen ejecutivo, métricas, plots, tests estadísticos y metodología
- **PDF**: Generación via weasyprint (requiere instalación adicional)

---

## 🤝 Contribuciones

Este proyecto es parte de una investigación académica sobre la comparación de solvers SAT. Las contribuciones son bienvenidas:

1. Fork del repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

## 📚 Referencias

- Demšar, J. (2006). *Statistical comparisons of classifiers over multiple data sets*. Journal of Machine Learning Research, 7, 1-30.
- SAT Competition. https://satcompetition.github.io/
- Biere, A., Heule, M., van Maaren, H., & Walsh, T. (Eds.). (2009). *Handbook of Satisfiability*. IOS Press.
- Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.

---

<div align="center">

**SAT Benchmark Suite v2.0** — Desarrollado con ❤️ para la investigación en satisfacibilidad booleana

</div>