#!/usr/bin/env python3
"""Generate standalone HTML report with embedded screenshots (base64)."""
import base64
import os
import sys

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.join(REPORT_DIR, "screenshots")
OUTPUT_FILE = os.path.join(REPORT_DIR, "informe_sat_benchmark_suite.html")

def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def screenshot(name, caption):
    path = os.path.join(SCREENSHOTS_DIR, name)
    if not os.path.exists(path):
        return f'<p class="caption">⚠️ Screenshot not found: {name}</p>'
    b64 = img_to_base64(path)
    return f'''<figure>
        <img src="data:image/png;base64,{b64}" alt="{caption}" style="width:100%;border-radius:8px;border:1px solid #333;margin:10px 0;">
        <figcaption class="caption">{caption}</figcaption>
    </figure>'''

html = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Informe Técnico — SAT Benchmark Suite v2.0</title>
<style>
  :root {{ --bg: #0f172a; --surface: #1e293b; --border: #334155; --text: #e2e8f0; --muted: #94a3b8; --accent: #3b82f6; --accent2: #8b5cf6; --green: #22c55e; --orange: #f59e0b; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; line-height:1.7; padding:40px 20px; }}
  .container {{ max-width:1100px; margin:0 auto; }}
  h1 {{ text-align:center; font-size:2.4em; margin-bottom:5px; background: linear-gradient(135deg, var(--accent), var(--accent2)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .subtitle {{ text-align:center; color:var(--muted); font-size:1.1em; margin-bottom:30px; }}
  .meta {{ text-align:center; color:var(--muted); margin-bottom:40px; font-size:0.9em; }}
  h2 {{ color:var(--accent); font-size:1.6em; margin:40px 0 15px; padding-bottom:8px; border-bottom:2px solid var(--border); }}
  h3 {{ color:var(--accent2); font-size:1.2em; margin:25px 0 10px; }}
  h4 {{ color:var(--green); margin:15px 0 8px; }}
  p {{ margin:10px 0; }}
  a {{ color:var(--accent); text-decoration:none; }}
  table {{ width:100%; border-collapse:collapse; margin:15px 0; font-size:0.9em; }}
  th {{ background:var(--surface); color:var(--accent); text-align:left; padding:10px 12px; border:1px solid var(--border); }}
  td {{ padding:8px 12px; border:1px solid var(--border); }}
  tr:nth-child(even) td {{ background:rgba(30,41,59,0.5); }}
  code {{ background:var(--surface); padding:2px 6px; border-radius:4px; font-family:'Fira Code',monospace; font-size:0.88em; color:var(--orange); }}
  pre {{ background:var(--surface); padding:20px; border-radius:8px; overflow-x:auto; margin:15px 0; border:1px solid var(--border); font-family:'Fira Code',monospace; font-size:0.85em; line-height:1.5; color:var(--text); }}
  .caption {{ text-align:center; color:var(--muted); font-style:italic; font-size:0.9em; margin:5px 0 20px; }}
  figure {{ margin:20px 0; }}
  .toc {{ background:var(--surface); padding:25px 30px; border-radius:10px; margin:20px 0 40px; border:1px solid var(--border); }}
  .toc h3 {{ color:var(--accent); margin-top:0; }}
  .toc ol {{ padding-left:20px; }}
  .toc li {{ margin:4px 0; }}
  .toc a {{ color:var(--text); }}
  .toc a:hover {{ color:var(--accent); }}
  .badge {{ display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.8em; font-weight:bold; }}
  .badge-green {{ background:rgba(34,197,94,0.2); color:var(--green); }}
  .badge-blue {{ background:rgba(59,130,246,0.2); color:var(--accent); }}
  .badge-purple {{ background:rgba(139,92,246,0.2); color:var(--accent2); }}
  .badge-orange {{ background:rgba(245,158,11,0.2); color:var(--orange); }}
  .card {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:20px; margin:15px 0; }}
  .pipeline-box {{ background:var(--surface); border-left:4px solid var(--accent); padding:15px 20px; margin:10px 0; border-radius:0 8px 8px 0; }}
  .formula {{ text-align:center; padding:15px; background:var(--surface); border-radius:8px; margin:10px 0; font-family:'Times New Roman',serif; font-size:1.1em; color:var(--orange); }}
  .stat-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:15px; margin:15px 0; }}
  @media (max-width:768px) {{ .stat-grid {{ grid-template-columns:1fr; }} }}
  .divider {{ height:1px; background:var(--border); margin:40px 0; }}
  ul {{ padding-left:25px; }}
  li {{ margin:4px 0; }}
  .emoji {{ font-size:1.2em; }}
  .highlight {{ background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.3); border-radius:8px; padding:15px; margin:10px 0; }}
</style>
</head>
<body>
<div class="container">

<h1>⚡ SAT Benchmark Suite v2.0</h1>
<p class="subtitle">Plataforma Integral para Benchmarking y Análisis Estadístico Riguroso de Solvers SAT</p>
<p class="meta"><strong>Autor:</strong> Abel &nbsp;|&nbsp; <strong>Fecha:</strong> Febrero 2025 &nbsp;|&nbsp; <strong>Versión:</strong> 2.0</p>

<div class="divider"></div>

<!-- TABLE OF CONTENTS -->
<div class="toc">
<h3>📋 Tabla de Contenidos</h3>
<ol>
<li><a href="#intro">Introducción</a></li>
<li><a href="#arch">Arquitectura del Sistema</a></li>
<li><a href="#modules">Módulos de la Aplicación</a></li>
<li><a href="#pipeline">Pipeline de Análisis Estadístico Riguroso</a></li>
<li><a href="#execution">Motor de Ejecución de Experimentos</a></li>
<li><a href="#modeler">SAT Modeler: Lenguaje y Compilador</a></li>
<li><a href="#database">Base de Datos</a></li>
<li><a href="#api">API REST</a></li>
<li><a href="#stack">Stack Tecnológico</a></li>
<li><a href="#deploy">Despliegue</a></li>
<li><a href="#conclusions">Conclusiones y Trabajo Futuro</a></li>
<li><a href="#refs">Referencias</a></li>
</ol>
</div>

<!-- 1. INTRODUCTION -->
<h2 id="intro">1. Introducción</h2>
<p>El <strong>Problema de Satisfacibilidad Booleana (SAT)</strong> es un problema fundamental en ciencias de la computación, siendo el primer problema demostrado NP-completo (Cook, 1971). Su resolución eficiente tiene implicaciones directas en verificación formal, planificación, criptoanálisis, diseño de circuitos y optimización combinatoria.</p>
<p><strong>SAT Benchmark Suite v2.0</strong> es una plataforma web completa que integra todo el ciclo de vida del benchmarking de solvers SAT: desde la gestión de solvers y la importación de instancias CNF, pasando por la ejecución controlada de experimentos, hasta el análisis estadístico con rigor académico siguiendo la metodología de <strong>Demšar (2006)</strong> y las prácticas de la <strong>SAT Competition</strong>.</p>

<div class="highlight">
<h4>✨ Características Principales</h4>
<ul>
<li>🔬 <strong>Pipeline estadístico riguroso:</strong> Friedman, Wilcoxon, Mann-Whitney U, post-hoc Nemenyi/Conover, Bonferroni, Holm, Benjamini-Hochberg</li>
<li>📊 <strong>Métricas estándar:</strong> PAR-2, PAR-10, Virtual Best Solver, tasas de resolución, métricas CDCL</li>
<li>📈 <strong>Visualizaciones publicables:</strong> Cactus plots, ECDF, scatter, heatmaps, critical difference diagrams</li>
<li>🔢 <strong>Bootstrap BCa:</strong> 10,000 réplicas, seed fijo para reproducibilidad</li>
<li>🧮 <strong>SAT Modeler:</strong> IDE integrado con lenguaje inspirado en MiniZinc</li>
<li>🐳 <strong>Docker:</strong> Despliegue con 3 servicios (backend, frontend, nginx)</li>
<li>📄 <strong>Reportes automáticos:</strong> HTML/PDF con gráficos embebidos</li>
<li>⚡ <strong>Tiempo real:</strong> WebSocket para monitoreo de experimentos</li>
</ul>
</div>

<!-- 2. ARCHITECTURE -->
<h2 id="arch">2. Arquitectura del Sistema</h2>
<pre>
┌──────────────────────────────────────────────────────────────────────────┐
│                         SAT Benchmark Suite v2.0                         │
│                                                                          │
│  ┌─────────────────┐    ┌──────────────┐    ┌────────────────────────┐  │
│  │    FRONTEND      │    │    NGINX      │    │       BACKEND          │  │
│  │  React 18        │    │  Reverse     │    │  FastAPI (Python 3.11) │  │
│  │  TypeScript 5.3  │◄──►  Proxy       ◄──►│  SQLite + SQLAlchemy   │  │
│  │  Vite 5          │    │  Rate Limit  │    │  SciPy + Matplotlib    │  │
│  │  TailwindCSS 3.4 │    │  Gzip + SPA  │    │  Bootstrap CI          │  │
│  │  Recharts 2      │    │              │    │                        │  │
│  │  Puerto: 5173    │    │  Puerto: 80  │    │  Puerto: 8000          │  │
│  └─────────────────┘    └──────────────┘    └────────────────────────┘  │
│                                                                          │
│                         Docker Compose                                   │
│  Volúmenes: data/ (SQLite), solvers/ (binarios), benchmarks/ (CNF)      │
└──────────────────────────────────────────────────────────────────────────┘
</pre>

<table>
<tr><th>Servicio</th><th>Imagen</th><th>Puerto</th><th>Propósito</th></tr>
<tr><td>backend</td><td><code>python:3.11-slim</code> + gcc/make</td><td>8000</td><td>API REST + Analysis Engine</td></tr>
<tr><td>frontend</td><td><code>node:20-alpine</code></td><td>5173</td><td>React SPA (dev)</td></tr>
<tr><td>nginx</td><td><code>nginx:alpine</code></td><td>80</td><td>Reverse proxy (prod)</td></tr>
</table>

<!-- 3. MODULES -->
<h2 id="modules">3. Módulos de la Aplicación</h2>
<p>La aplicación cuenta con <strong>7 módulos principales</strong>, cada uno con su propia página y endpoints dedicados.</p>

<h3>3.1 Dashboard</h3>
<p>Panel de control con métricas generales: contadores de solvers/benchmarks/experimentos, distribución de resultados (SAT/UNSAT/TIMEOUT/ERROR) y actividad reciente.</p>
{screenshot("01_dashboard.png", "Figura 1: Dashboard principal — métricas del sistema, distribución de resultados y actividad reciente.")}

<h3>3.2 Solvers</h3>
<p>Catálogo de solvers SAT con detección automática de versión, matriz de comparación de características, y test de ejecutabilidad.</p>
{screenshot("02_solvers.png", "Figura 2: Módulo de Solvers — catálogo con tarjetas informativas y matriz de comparación.")}

<table>
<tr><th>Solver</th><th>Versión</th><th>Estado</th><th>Categoría</th><th>Features</th></tr>
<tr><td><strong>Kissat</strong></td><td>4.0.4</td><td><span class="badge badge-green">✅ Listo</span></td><td>Competition</td><td>CDCL, Preprocessing, Inprocessing, Vivification</td></tr>
<tr><td><strong>MiniSat</strong></td><td>2.2.0</td><td><span class="badge badge-green">✅ Listo</span></td><td>Educational</td><td>CDCL, VSIDS, Two-watched literals</td></tr>
<tr><td><strong>CaDiCaL</strong></td><td>2.1.3</td><td><span class="badge badge-orange">⬚ No instalado</span></td><td>Competition</td><td>CDCL, Chronological backtracking, BVE</td></tr>
<tr><td><strong>CryptoMiniSat</strong></td><td>5.11.22</td><td><span class="badge badge-orange">⬚ No instalado</span></td><td>Competition</td><td>CDCL, XOR reasoning, Gaussian elimination</td></tr>
</table>

<h3>3.3 Benchmarks</h3>
<p>Gestión de instancias CNF con paginación server-side (25/página), filtrado por familia/dificultad, upload drag&amp;drop con auto-clasificación, y estadísticas agregadas calculadas con SQL.</p>
{screenshot("03_benchmarks.png", "Figura 3: Módulo de Benchmarks — paginación, filtrado y estadísticas agregadas.")}

<h3>3.4 Experiments</h3>
<p>Motor de ejecución con creación flexible de experimentos, ejecución en background, monitoreo WebSocket en tiempo real, y métricas CDCL detalladas.</p>
{screenshot("04_experiments.png", "Figura 4: Lista de experimentos con estado y progreso.")}
{screenshot("04b_experiment_detail.png", "Figura 5: Detalle de experimento — configuración, distribución de resultados y tabla de runs.")}

<div class="card">
<h4>Métricas capturadas por run:</h4>
<div class="stat-grid">
<div><strong>Resultado:</strong> SAT / UNSAT / TIMEOUT / ERROR / UNKNOWN</div>
<div><strong>Exit codes:</strong> 10 = SAT, 20 = UNSAT</div>
<div><strong>Tiempos:</strong> Wall, CPU, User, System</div>
<div><strong>Memoria:</strong> Máxima y promedio (KB)</div>
<div><strong>CDCL:</strong> Conflictos, Decisiones, Propagaciones, Restarts</div>
<div><strong>Cláusulas:</strong> Aprendidas, Eliminadas</div>
</div>
</div>

<h3>3.5 Analysis</h3>
<p>Módulo unificado con <strong>10 pestañas</strong> de análisis estadístico riguroso.</p>
{screenshot("05_analysis.png", "Figura 6: Módulo de Analysis — 10 pestañas de análisis estadístico.")}

<table>
<tr><th>#</th><th>Pestaña</th><th>Contenido</th></tr>
<tr><td>1</td><td><strong>Overview</strong></td><td>Ranking PAR-2, solved counts, resumen general</td></tr>
<tr><td>2</td><td><strong>Metrics</strong></td><td>PAR-2, PAR-10, VBS, solve matrix, instancias únicas</td></tr>
<tr><td>3</td><td><strong>Statistical Tests</strong></td><td>Wilcoxon, Mann-Whitney U, Friedman, t-tests</td></tr>
<tr><td>4</td><td><strong>Bootstrap CI</strong></td><td>Intervalos BCa con 10,000 réplicas</td></tr>
<tr><td>5</td><td><strong>Pairwise Comparison</strong></td><td>Comparación detallada entre pares de solvers</td></tr>
<tr><td>6</td><td><strong>Family Analysis</strong></td><td>PAR-2 por familia de benchmarks</td></tr>
<tr><td>7</td><td><strong>CDCL Metrics</strong></td><td>conflicts/s, decisions/s, propagations/decision</td></tr>
<tr><td>8</td><td><strong>Effect Sizes</strong></td><td>Cohen's d, Vargha-Delaney A measure</td></tr>
<tr><td>9</td><td><strong>Normality Tests</strong></td><td>Shapiro-Wilk, D'Agostino, Anderson-Darling</td></tr>
<tr><td>10</td><td><strong>CSV Export</strong></td><td>Exportación de 10+ tablas de datos</td></tr>
</table>

<h3>3.6 Visualization</h3>
<p>5 tipos de gráficos interactivos con tooltips, zoom y selección de solvers.</p>
{screenshot("06_visualization.png", "Figura 7: Módulo de Visualization — gráficos interactivos Recharts.")}

<table>
<tr><th>Gráfico</th><th>Descripción</th></tr>
<tr><td><strong>Cactus Plot</strong></td><td>Instancias resueltas vs. tiempo (curva acumulativa)</td></tr>
<tr><td><strong>Scatter Plot</strong></td><td>Comparación pairwise de tiempos entre solvers</td></tr>
<tr><td><strong>ECDF</strong></td><td>Distribución empírica acumulativa / Performance Profile</td></tr>
<tr><td><strong>PAR-2 / Solved</strong></td><td>Barras de PAR-2 score y número de instancias resueltas</td></tr>
<tr><td><strong>Heatmap</strong></td><td>Matriz solver × benchmark con tiempos por color</td></tr>
</table>

<h3>3.7 SAT Modeler</h3>
<p>IDE integrado con lenguaje propio inspirado en MiniZinc para modelar, compilar y resolver problemas SAT.</p>
{screenshot("07_sat_modeler.png", "Figura 8: SAT Modeler — editor con syntax highlighting, ejemplos y resultados.")}

<div class="card">
<h4>Características del editor:</h4>
<ul>
<li><strong>Syntax highlighting</strong> token-based con 9 categorías de colores</li>
<li><strong>Validación en tiempo real</strong> con debounce de 400ms</li>
<li><strong>4 ejemplos pre-definidos:</strong> Graph Coloring, Pigeonhole (UNSAT), Logic Puzzle, N-Queens</li>
<li><strong>Compilación Tseitin</strong> a DIMACS CNF con sequential counter para cardinalidad</li>
<li><strong>Resolución directa</strong> con Kissat o MiniSat, timeout configurable</li>
<li><strong>Resultados interactivos:</strong> tabla de asignaciones, visor DIMACS, copy/download</li>
</ul>
</div>

<!-- 4. RIGOROUS PIPELINE -->
<h2 id="pipeline">4. Pipeline de Análisis Estadístico Riguroso</h2>
<p>El pipeline sigue las mejores prácticas de la comunidad SAT y la metodología de <strong>Demšar (2006)</strong>.</p>

<h3>4.1 Métricas Base</h3>
<div class="pipeline-box">
<strong>PAR-2 (Penalized Average Runtime ×2):</strong> Métrica estándar de la SAT Competition. Para instancias no resueltas dentro del timeout T, se asigna penalización 2T.
</div>
<div class="formula">PAR-2(s) = (1/n) × Σᵢ tᵢ* , donde tᵢ* = tᵢ si resuelto, 2T si timeout</div>

<div class="pipeline-box">
<strong>Virtual Best Solver (VBS):</strong> Para cada instancia, selecciona el mejor tiempo: VBS(i) = min{{tₛ(i) : s ∈ S}}
</div>

<div class="pipeline-box">
<strong>Solve Matrix:</strong> Descomposición en instancias comunes (resueltas por todos), únicas (resueltas por solo uno), y tasa de resolución por solver.
</div>

<h3>4.2 Tests de Normalidad</h3>
<table>
<tr><th>Test</th><th>Implementación</th><th>Condición</th></tr>
<tr><td><strong>Shapiro-Wilk</strong></td><td><code>scipy.stats.shapiro</code></td><td>N &lt; 5,000</td></tr>
<tr><td><strong>D'Agostino-Pearson</strong></td><td><code>scipy.stats.normaltest</code></td><td>N ≥ 20</td></tr>
<tr><td><strong>Anderson-Darling</strong></td><td><code>scipy.stats.anderson</code></td><td>Robusto, sensible a colas</td></tr>
</table>

<h3>4.3 Tests Estadísticos</h3>
<h4>Para 2 Solvers</h4>
<table>
<tr><th>Test</th><th>Tipo</th><th>H₀</th></tr>
<tr><td><strong>Wilcoxon signed-rank</strong></td><td>No param., pareado</td><td>Medianas de diferencias iguales</td></tr>
<tr><td><strong>Mann-Whitney U</strong></td><td>No param., indep.</td><td>Distribuciones iguales</td></tr>
<tr><td><strong>Sign test</strong></td><td>No param., pareado</td><td>P(X > Y) = 0.5</td></tr>
</table>

<h4>Para k ≥ 3 Solvers</h4>
<table>
<tr><th>Test</th><th>Tipo</th><th>Post-hoc</th></tr>
<tr><td><strong>Friedman</strong></td><td>ANOVA no paramétrico por rangos</td><td>Nemenyi / Conover</td></tr>
<tr><td><strong>Nemenyi</strong></td><td>Post-hoc pairwise (conservador)</td><td>—</td></tr>
<tr><td><strong>Conover</strong></td><td>Post-hoc pairwise (más potente)</td><td>—</td></tr>
</table>

<h3>4.4 Correcciones para Comparaciones Múltiples</h3>
<table>
<tr><th>Método</th><th>Control</th><th>Conservadurismo</th></tr>
<tr><td><strong>Bonferroni</strong></td><td>FWER: α' = α/m</td><td>Alto</td></tr>
<tr><td><strong>Holm step-down</strong></td><td>FWER: α' = α/(m − i + 1)</td><td>Medio</td></tr>
<tr><td><strong>Benjamini-Hochberg</strong></td><td>FDR: p(i) ≤ (i/m) × α</td><td>Bajo</td></tr>
</table>

<h3>4.5 Tamaños de Efecto</h3>
<div class="stat-grid">
<div class="card">
<h4>Cohen's d</h4>
<p>d = (X̄₁ - X̄₂) / sₚ</p>
<ul>
<li>&lt; 0.2 — Negligible</li>
<li>0.2 – 0.5 — Pequeño</li>
<li>0.5 – 0.8 — Medio</li>
<li>&gt; 0.8 — Grande</li>
</ul>
</div>
<div class="card">
<h4>Vargha-Delaney A</h4>
<p>A(X,Y) = P(X > Y) + 0.5 × P(X = Y)</p>
<ul>
<li>≈ 0.50 — Sin efecto</li>
<li>&gt; 0.56 — Pequeño</li>
<li>&gt; 0.64 — Medio</li>
<li>&gt; 0.71 — Grande</li>
</ul>
</div>
</div>

<h3>4.6 Bootstrap BCa</h3>
<div class="card">
<ul>
<li><strong>Método:</strong> BCa (Bias-Corrected and Accelerated) — Efron (1993)</li>
<li><strong>Réplicas:</strong> 10,000 (configurable)</li>
<li><strong>Nivel de confianza:</strong> 95%</li>
<li><strong>Seed:</strong> 42 (reproducibilidad)</li>
<li><strong>Aplicaciones:</strong> IC para PAR-2, diferencias de medias, incertidumbre en ranking</li>
</ul>
</div>

<h3>4.7 Visualizaciones Publicables</h3>
<table>
<tr><th>Gráfico</th><th>Descripción</th><th>Referencia</th></tr>
<tr><td><strong>Cactus Plot</strong></td><td>Instancias resueltas vs. tiempo (log)</td><td>SAT Competition</td></tr>
<tr><td><strong>ECDF / Performance Profile</strong></td><td>Distribución acumulativa vs. VBS</td><td>Dolan & Moré (2002)</td></tr>
<tr><td><strong>Boxplot con CI</strong></td><td>Distribución con intervalos de confianza</td><td>—</td></tr>
<tr><td><strong>Scatter Plot</strong></td><td>Pairwise en escala log-log</td><td>Estándar</td></tr>
<tr><td><strong>Heatmap</strong></td><td>Solver × Familia codificado por color</td><td>—</td></tr>
<tr><td><strong>Critical Difference Diagram</strong></td><td>Tests Nemenyi visualizados</td><td>Demšar (2006)</td></tr>
<tr><td><strong>Survival Analysis</strong></td><td>1 − ECDF</td><td>—</td></tr>
<tr><td><strong>PAR-2 Bar Chart</strong></td><td>Ranking horizontal</td><td>—</td></tr>
</table>

<h3>4.8 Reportes Generados</h3>
<div class="stat-grid">
<div class="card">
<h4>📄 HTML Standalone</h4>
<p>Reporte completo con gráficos base64 embebidos. Secciones: Resumen ejecutivo, métricas, plots, tests, bootstrap, metodología.</p>
</div>
<div class="card">
<h4>📊 CSV Export</h4>
<p>10+ tablas: metrics_ranking, solve_matrix, normality, pairwise_tests, post_hoc, corrections, effect_sizes, bootstrap_ci, pairwise_bootstrap, full_tests.</p>
</div>
</div>

<!-- 5. EXECUTION ENGINE -->
<h2 id="execution">5. Motor de Ejecución</h2>
<pre>
Crear Experimento → Validar Config → Ejecución Asíncrona
  │
  └─── Para cada (solver × benchmark × repetición):
       1. Lanzar subprocess con timeout
       2. Monitorear memoria (psutil)
       3. Capturar stdout/stderr
       4. Parsear resultado (exit code + string matching)
       5. Extraer métricas CDCL (regex)
       6. Calcular PAR-2
       7. Guardar run en SQLite
       8. Emitir progreso via WebSocket
  │
  └─── Marcar experimento "completed"
</pre>

<!-- 6. SAT MODELER -->
<h2 id="modeler">6. SAT Modeler: Lenguaje y Compilador</h2>
<pre>
Código Fuente → TOKENIZER → PARSER → AST → COMPILER (Tseitin) → DIMACS CNF → SOLVER → Resultado
</pre>

<h3>Sintaxis del lenguaje:</h3>
<pre>
% Declaración de variables booleanas
var bool: x, y, z;

% Restricciones (operadores lógicos)
constraint x /\\ y;          % AND
constraint x \\/ y;          % OR
constraint not x;            % NOT (también: ~x, !x)
constraint x -> y;           % Implicación
constraint x <-> y;          % Equivalencia
constraint x xor y;          % XOR

% Restricciones de cardinalidad
constraint atmost(2, [x, y, z]);
constraint atleast(1, [x, y, z]);
constraint exactly(1, [x, y, z]);

% Resolver
solve satisfy;
</pre>

<table>
<tr><th>Ejemplo</th><th>Descripción</th><th>Resultado</th></tr>
<tr><td><strong>Graph Coloring</strong></td><td>3-coloración de grafo con 4 nodos</td><td><span class="badge badge-green">SAT</span></td></tr>
<tr><td><strong>Pigeonhole (3,2)</strong></td><td>3 palomas en 2 casillas</td><td><span class="badge badge-orange">UNSAT</span></td></tr>
<tr><td><strong>Logic Puzzle</strong></td><td>Rompecabezas lógico con implicaciones</td><td><span class="badge badge-green">SAT</span></td></tr>
<tr><td><strong>N-Queens 4×4</strong></td><td>4 reinas en tablero 4×4</td><td><span class="badge badge-green">SAT</span></td></tr>
</table>

<!-- 7. DATABASE -->
<h2 id="database">7. Base de Datos</h2>
<p>SQLite con 4 tablas: <code>solvers</code> (catálogo), <code>benchmarks</code> (instancias CNF), <code>experiments</code> (configuraciones), <code>runs</code> (resultados individuales). Índices optimizados en experiment_id, solver_id, benchmark_id, family.</p>

<!-- 8. API -->
<h2 id="api">8. API REST</h2>
<table>
<tr><th>Grupo</th><th>Prefijo</th><th>Endpoints</th><th>Descripción</th></tr>
<tr><td>Dashboard</td><td><code>/api/dashboard</code></td><td>2</td><td>Estadísticas y actividad</td></tr>
<tr><td>Solvers</td><td><code>/api/solvers</code></td><td>8</td><td>Catálogo, test, comparación</td></tr>
<tr><td>Benchmarks</td><td><code>/api/benchmarks</code></td><td>7</td><td>CRUD, upload, scan</td></tr>
<tr><td>Experiments</td><td><code>/api/experiments</code></td><td>9</td><td>CRUD, start/stop, WebSocket</td></tr>
<tr><td>Analysis</td><td><code>/api/analysis</code></td><td>17</td><td>PAR-2, VBS, scatter, ECDF</td></tr>
<tr><td>Rigorous</td><td><code>/api/rigorous</code></td><td>12</td><td>Pipeline completo, bootstrap</td></tr>
<tr><td>Modeler</td><td><code>/api/modeler</code></td><td>8</td><td>Parse, compile, solve</td></tr>
<tr><td colspan="2"><strong>Total</strong></td><td><strong>63+</strong></td><td><strong>+ 1 WebSocket</strong></td></tr>
</table>

<!-- 9. STACK -->
<h2 id="stack">9. Stack Tecnológico</h2>
<div class="stat-grid">
<div class="card">
<h4>🐍 Backend</h4>
<p>Python 3.11, FastAPI 0.109, SQLAlchemy 2.0, Pandas 2.1, NumPy 1.26, SciPy 1.12, Matplotlib 3.8, Seaborn 0.13, Jinja2 3.1, Pydantic v2, psutil</p>
</div>
<div class="card">
<h4>⚛️ Frontend</h4>
<p>React 18, TypeScript 5.3, Vite 5, TailwindCSS 3.4, Recharts 2, TanStack Query 5, Zustand 4, React Router 6, Lucide React</p>
</div>
</div>

<!-- 10. DEPLOY -->
<h2 id="deploy">10. Despliegue</h2>
<pre>
# Desarrollo
cd sat-benchmark-react
sudo docker-compose up -d

# Producción (con Nginx)
sudo docker-compose --profile production up -d

# Acceso
Frontend:  http://localhost:5173
API:       http://localhost:8000
Swagger:   http://localhost:8000/docs
</pre>

<!-- 11. CONCLUSIONS -->
<h2 id="conclusions">11. Conclusiones y Trabajo Futuro</h2>
<h3>Logros</h3>
<ol>
<li>Gestión completa de solvers, benchmarks y experimentos con interfaz web moderna</li>
<li>Ejecución automatizada con monitoreo WebSocket en tiempo real</li>
<li>Pipeline estadístico riguroso: 9 tests, 3 correcciones, 2 medidas de efecto</li>
<li>Bootstrap BCa para cuantificar incertidumbre</li>
<li>8 tipos de visualizaciones publicables</li>
<li>IDE de modelado SAT con lenguaje propio y compilador Tseitin</li>
<li>Exportación completa: CSV (10+ tablas), HTML, PDF</li>
<li>63+ endpoints REST + WebSocket</li>
</ol>

<h3>Trabajo Futuro</h3>
<ul>
<li>Integración completa de CaDiCaL y CryptoMiniSat</li>
<li>Portfolio solver (meta-solver automático)</li>
<li>Clasificación ML de instancias</li>
<li>Soporte MaxSAT y #SAT</li>
<li>Ejecución distribuida en clusters</li>
<li>Integración con Ollama para asistente AI</li>
</ul>

<!-- 12. REFERENCES -->
<h2 id="refs">12. Referencias</h2>
<ol>
<li><strong>Cook, S. A.</strong> (1971). <em>The complexity of theorem-proving procedures</em>. Proc. 3rd ACM STOC, 151-158.</li>
<li><strong>Demšar, J.</strong> (2006). <em>Statistical comparisons of classifiers over multiple data sets</em>. JMLR, 7, 1-30.</li>
<li><strong>Efron, B. &amp; Tibshirani, R.</strong> (1993). <em>An Introduction to the Bootstrap</em>. Chapman &amp; Hall.</li>
<li><strong>Dolan, E. &amp; Moré, J.</strong> (2002). <em>Benchmarking optimization software with performance profiles</em>. Math. Prog., 91(2), 201-213.</li>
<li><strong>Sinz, C.</strong> (2005). <em>Towards an optimal CNF encoding of Boolean cardinality constraints</em>. CP 2005.</li>
<li><strong>Biere, A. et al.</strong> (Eds.). (2009). <em>Handbook of Satisfiability</em>. IOS Press.</li>
<li><strong>Vargha, A. &amp; Delaney, H.</strong> (2000). <em>A critique of the CL common language effect size statistics</em>. JEBS, 25(2).</li>
<li><strong>Holm, S.</strong> (1979). <em>A simple sequentially rejective multiple test procedure</em>. Scand. J. Stat., 6(2).</li>
<li><strong>Benjamini, Y. &amp; Hochberg, Y.</strong> (1995). <em>Controlling the false discovery rate</em>. JRSS-B, 57(1).</li>
<li><strong>SAT Competition</strong>. <a href="https://satcompetition.github.io/">https://satcompetition.github.io/</a></li>
</ol>

<div class="divider"></div>
<p style="text-align:center; color:var(--muted);">
<em>SAT Benchmark Suite v2.0 — Informe Técnico — Febrero 2025</em>
</p>

</div>
</body>
</html>'''

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Report generated: {OUTPUT_FILE}")
print(f"   Size: {os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB")
