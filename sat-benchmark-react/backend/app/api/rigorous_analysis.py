"""
Rigorous Analysis API Endpoint
================================

FastAPI router que integra todos los componentes del análisis estadístico:
- BenchmarkMetrics: PAR-2, PAR-10, VBS, solve matrix, ranking
- StatisticalTestSuite: Wilcoxon, Friedman, Nemenyi, correcciones
- BootstrapEngine: intervalos de confianza BCa
- SATVisualizationEngine: gráficos publication-ready
- ReportGenerator: informes HTML/PDF

Todos los endpoints reciben experiment_id y timeout para configurar el análisis.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from typing import Optional, List
import numpy as np
import pandas as pd
import logging
import math
import io

from app.analysis import (
    StatisticalTestSuite,
    BootstrapEngine,
    BenchmarkMetrics,
    SATVisualizationEngine,
    ReportGenerator,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== HELPERS ====================

def _safe(v):
    """Make value JSON-safe."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, dict):
        return {k: _safe(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_safe(item) for item in v]
    return v


def _normalize_metrics(metrics: dict) -> dict:
    """
    Add compatibility keys to metrics output from BenchmarkMetrics.
    
    BenchmarkMetrics returns:
      - par_scores.par2  → we also add par2_scores (flat dict)
      - par_scores.par10 → we also add par10_scores (flat dict)
      - solve_matrix.unique_solved → we also add solver_totals from summary_per_solver
    
    This ensures ReportGenerator and frontend can find the keys they expect.
    """
    m = dict(metrics)
    
    # par2_scores / par10_scores — flat dicts {solver: score}
    par_scores = m.get("par_scores", {})
    if "par2" in par_scores and "par2_scores" not in m:
        m["par2_scores"] = par_scores["par2"]
    if "par10" in par_scores and "par10_scores" not in m:
        m["par10_scores"] = par_scores["par10"]
    
    # solver_totals in solve_matrix — from summary_per_solver
    sm = m.get("solve_matrix", {})
    if "solver_totals" not in sm and "summary_per_solver" in m:
        totals = {s: info.get("solved", 0) for s, info in m["summary_per_solver"].items()}
        sm["solver_totals"] = totals
        m["solve_matrix"] = sm
    
    # uniquely_solved — already in solve_matrix as unique_solved
    if "uniquely_solved" not in sm and "unique_solved" in sm:
        sm["uniquely_solved"] = sm["unique_solved"]
        m["solve_matrix"] = sm
    
    return m


def _get_experiment_data(db, experiment_id: int, timeout: float) -> dict:
    """
    Fetch experiment runs and build the data structures needed by the analysis engine.
    
    Returns dict with:
      - solver_times: {solver_name: [penalized_time_per_benchmark]}
      - raw_solver_times: {solver_name: [actual_time_per_benchmark]}
      - time_matrix: DataFrame [benchmark × solver]
      - runs: raw runs list from DB
      - normalized_runs: runs with normalized column names for BenchmarkMetrics
      - experiment: experiment info dict
    """
    exp = db.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    
    runs = db.get_runs(experiment_id=experiment_id)
    if not runs:
        raise HTTPException(status_code=404, detail=f"No runs found for experiment {experiment_id}")
    
    # Build solver_times and time_matrix
    solver_times = {}
    benchmark_solver_times = {}  # {benchmark: {solver: time}}
    normalized_runs = []  # For BenchmarkMetrics compatibility
    
    for run in runs:
        solver = run.get("solver_name") or f"solver_{run.get('solver_id', '?')}"
        benchmark = run.get("benchmark_name") or run.get("benchmark_path", f"bench_{run.get('benchmark_id', '?')}")
        # Use the simplest name
        if "/" in benchmark:
            benchmark = benchmark.split("/")[-1]
        
        result = run.get("result", "UNKNOWN")
        wall_time = run.get("wall_time_seconds") or run.get("cpu_time_seconds") or run.get("wall_time") or run.get("cpu_time")
        
        if wall_time is None:
            wall_time = timeout  # treat as unsolved
        
        # Derive benchmark family from name or use existing
        family = run.get("benchmark_family")
        if not family:
            parts = benchmark.replace('.cnf', '').split('_')
            family = parts[0] if parts else "unknown"
        
        # Normalize result to uppercase
        result_upper = result.upper() if result else "UNKNOWN"
        if result_upper in ("SAT", "SATISFIABLE"):
            result_upper = "SAT"
        elif result_upper in ("UNSAT", "UNSATISFIABLE"):
            result_upper = "UNSAT"
        elif result_upper in ("TIMEOUT",):
            result_upper = "TIMEOUT"
        elif result_upper in ("ERROR", "MEMOUT"):
            result_upper = result_upper
        else:
            result_upper = "UNKNOWN"
        
        # Build normalized run for BenchmarkMetrics
        normalized_runs.append({
            "solver_name": solver,
            "benchmark_name": benchmark,
            "benchmark_family": family,
            "result": result_upper,
            "wall_time_seconds": float(wall_time),
        })
        
        # PAR-2 penalization for timeouts/errors
        if result_upper in ("TIMEOUT", "ERROR", "UNKNOWN", "MEMOUT") or float(wall_time) >= timeout:
            time_val = timeout * 2  # PAR-2 penalty
        else:
            time_val = float(wall_time)
        
        if solver not in solver_times:
            solver_times[solver] = []
        solver_times[solver].append(time_val)
        
        if benchmark not in benchmark_solver_times:
            benchmark_solver_times[benchmark] = {}
        benchmark_solver_times[benchmark][solver] = time_val
    
    # Build DataFrame [benchmark × solver]
    solvers = sorted(solver_times.keys())
    benchmarks_list = sorted(benchmark_solver_times.keys())
    
    matrix_data = {}
    for b in benchmarks_list:
        row = {}
        for s in solvers:
            row[s] = benchmark_solver_times.get(b, {}).get(s, timeout * 2)
        matrix_data[b] = row
    
    time_matrix = pd.DataFrame(matrix_data).T  # rows=benchmarks, cols=solvers
    
    # Also build raw times (non-penalized, for visualizations)
    raw_solver_times = {}
    for run in runs:
        solver = run.get("solver_name") or f"solver_{run.get('solver_id', '?')}"
        wall_time = run.get("wall_time_seconds") or run.get("cpu_time_seconds") or run.get("wall_time") or run.get("cpu_time")
        if wall_time is None:
            wall_time = timeout
        if solver not in raw_solver_times:
            raw_solver_times[solver] = []
        raw_solver_times[solver].append(float(wall_time))
    
    return {
        "solver_times": solver_times,
        "raw_solver_times": raw_solver_times,
        "time_matrix": time_matrix,
        "runs": runs,
        "normalized_runs": normalized_runs,
        "experiment": exp,
        "solvers": solvers,
        "benchmarks": benchmarks_list,
    }


# ==================== ENDPOINTS ====================

@router.get("/full-analysis/{experiment_id}")
async def full_analysis(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300, description="Timeout in seconds"),
    bootstrap_n: int = Query(5000, description="Bootstrap replications"),
    alpha: float = Query(0.05, description="Significance level"),
):
    """
    🔬 Análisis estadístico completo para un experimento.
    
    Ejecuta toda la pipeline:
    1. Métricas (PAR-2, PAR-10, VBS, solve matrix, ranking)
    2. Tests estadísticos (Friedman + Nemenyi si k≥3, o Wilcoxon si k=2)
    3. Bootstrap CIs
    4. Correcciones múltiples (Bonferroni, Holm, BH)
    """
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    
    result = {
        "experiment_id": experiment_id,
        "timeout": timeout,
        "n_solvers": len(data["solvers"]),
        "n_benchmarks": len(data["benchmarks"]),
        "solvers": data["solvers"],
    }
    
    # 1. Metrics
    metrics = BenchmarkMetrics(timeout=timeout)
    result["metrics"] = _safe(_normalize_metrics(metrics.compute_all_metrics(data["normalized_runs"])))
    
    # 2. Statistical tests
    test_suite = StatisticalTestSuite()
    
    if len(data["solvers"]) >= 3:
        # Multi-solver analysis
        multi = test_suite.full_multi_solver_analysis(data["time_matrix"])
        result["statistical_tests"] = _safe(multi)
    elif len(data["solvers"]) == 2:
        s1, s2 = data["solvers"]
        t1 = np.array(data["solver_times"][s1])
        t2 = np.array(data["solver_times"][s2])
        n = min(len(t1), len(t2))
        pairwise = test_suite.full_pairwise_analysis(t1[:n], t2[:n], s1, s2)
        result["statistical_tests"] = _safe(pairwise)
    else:
        result["statistical_tests"] = {"message": "Need ≥ 2 solvers for statistical tests"}
    
    # 3. Bootstrap CIs
    bootstrap = BootstrapEngine(n_bootstrap=bootstrap_n)
    try:
        bootstrap_results = _safe(bootstrap.full_solver_bootstrap(
            data["normalized_runs"], timeout=timeout, confidence=1 - alpha
        ))
    except Exception as e:
        bootstrap_results = {"error": str(e)}
    
    result["bootstrap"] = bootstrap_results
    
    return result


@router.get("/metrics/{experiment_id}")
async def get_metrics(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300),
):
    """📈 Métricas de rendimiento: PAR-2, PAR-10, VBS, solve matrix, ranking."""
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    
    metrics = BenchmarkMetrics(timeout=timeout)
    return _safe(_normalize_metrics(metrics.compute_all_metrics(data["normalized_runs"])))


@router.get("/statistical-tests/{experiment_id}")
async def get_statistical_tests(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300),
):
    """🧪 Tests estadísticos: Wilcoxon/Friedman + post-hoc + correcciones."""
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    
    test_suite = StatisticalTestSuite()
    
    if len(data["solvers"]) >= 3:
        return _safe(test_suite.full_multi_solver_analysis(data["time_matrix"]))
    elif len(data["solvers"]) == 2:
        s1, s2 = data["solvers"]
        t1 = np.array(data["solver_times"][s1])
        t2 = np.array(data["solver_times"][s2])
        n = min(len(t1), len(t2))
        return _safe(test_suite.full_pairwise_analysis(t1[:n], t2[:n], s1, s2))
    else:
        return {"message": "Need ≥ 2 solvers for statistical tests"}


@router.get("/bootstrap/{experiment_id}")
async def get_bootstrap(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300),
    n_bootstrap: int = Query(5000),
    confidence: float = Query(0.95),
):
    """🔄 Bootstrap confidence intervals (BCa method)."""
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    
    engine = BootstrapEngine(n_bootstrap=n_bootstrap)
    try:
        results = _safe(engine.full_solver_bootstrap(
            data["normalized_runs"], timeout=timeout, confidence=confidence
        ))
    except Exception as e:
        results = {"error": str(e)}
    
    return results


@router.get("/plots/{experiment_id}")
async def get_plots(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300),
):
    """
    📊 Genera todos los gráficos como imágenes base64.
    
    Incluye: cactus, scatter, boxplot, ECDF, performance profile,
    survival, PAR-2 bar chart, heatmap, critical difference diagram.
    """
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    
    viz = SATVisualizationEngine()
    
    # Compute PAR-2 for bar chart
    metrics = BenchmarkMetrics(timeout=timeout)
    all_metrics = _normalize_metrics(metrics.compute_all_metrics(data["normalized_runs"]))
    par2_scores = all_metrics.get("par2_scores", all_metrics.get("par_scores", {}).get("par2", {}))
    
    # Compute ranks for CD diagram
    avg_ranks = None
    cd = None
    
    if len(data["solvers"]) >= 3:
        test_suite = StatisticalTestSuite()
        friedman = test_suite.friedman_test(data["time_matrix"])
        if friedman.significant_005:
            nemenyi = test_suite.nemenyi_post_hoc(data["time_matrix"])
            avg_ranks = nemenyi.get("average_ranks")
            cd = nemenyi.get("critical_difference")
    
    plots = viz.generate_all_plots(
        solver_times=data["raw_solver_times"],
        time_matrix=data["time_matrix"],
        par2_scores=par2_scores,
        avg_ranks=avg_ranks,
        cd=cd,
        timeout=timeout,
    )
    
    return {"plots": plots, "plot_names": list(plots.keys())}


@router.get("/plots/{experiment_id}/{plot_name}")
async def get_single_plot(
    request: Request,
    experiment_id: int,
    plot_name: str,
    timeout: float = Query(300),
):
    """📊 Genera un gráfico específico como imagen base64."""
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    
    viz = SATVisualizationEngine()
    
    if plot_name == "cactus":
        img = viz.cactus_plot(data["raw_solver_times"], timeout)
    elif plot_name == "ecdf":
        img = viz.ecdf_plot(data["raw_solver_times"], timeout)
    elif plot_name == "boxplot":
        img = viz.boxplot(data["raw_solver_times"])
    elif plot_name == "performance_profile":
        img = viz.performance_profile(data["raw_solver_times"], timeout)
    elif plot_name == "survival":
        img = viz.survival_plot(data["raw_solver_times"], timeout)
    elif plot_name == "par2_bar":
        metrics = BenchmarkMetrics(timeout=timeout)
        all_metrics = _normalize_metrics(metrics.compute_all_metrics(data["normalized_runs"]))
        img = viz.par2_bar_chart(all_metrics.get("par_scores", {}).get("par2", {}))
    elif plot_name.startswith("scatter_"):
        parts = plot_name.replace("scatter_", "").split("_vs_")
        if len(parts) != 2:
            raise HTTPException(400, "Scatter plot name must be 'scatter_SolverA_vs_SolverB'")
        s1, s2 = parts
        if s1 not in data["solver_times"] or s2 not in data["solver_times"]:
            raise HTTPException(400, f"Solver not found. Available: {data['solvers']}")
        t1 = np.array(data["raw_solver_times"][s1])
        t2 = np.array(data["raw_solver_times"][s2])
        n = min(len(t1), len(t2))
        img = viz.scatter_plot(t1[:n], t2[:n], s1, s2, timeout)
    else:
        raise HTTPException(400, f"Unknown plot: {plot_name}. Available: cactus, ecdf, boxplot, performance_profile, survival, par2_bar, scatter_<A>_vs_<B>")
    
    return {"plot_name": plot_name, "image": img}


@router.get("/report/{experiment_id}", response_class=HTMLResponse)
async def get_report_html(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300),
    bootstrap_n: int = Query(5000),
):
    """
    📄 Genera un informe HTML completo y auto-contenido.
    
    El HTML incluye todos los gráficos embebidos como base64.
    Se puede abrir directamente en un navegador.
    """
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    exp = data["experiment"]
    
    # 1. Metrics
    metrics_engine = BenchmarkMetrics(timeout=timeout)
    metrics = _normalize_metrics(metrics_engine.compute_all_metrics(data["normalized_runs"]))
    
    # 2. Statistical tests
    test_suite = StatisticalTestSuite()
    if len(data["solvers"]) >= 3:
        stat_tests = test_suite.full_multi_solver_analysis(data["time_matrix"])
    elif len(data["solvers"]) == 2:
        s1, s2 = data["solvers"]
        t1 = np.array(data["solver_times"][s1])
        t2 = np.array(data["solver_times"][s2])
        n = min(len(t1), len(t2))
        stat_tests = test_suite.full_pairwise_analysis(t1[:n], t2[:n], s1, s2)
    else:
        stat_tests = {}
    
    # 3. Bootstrap
    bootstrap = BootstrapEngine(n_bootstrap=bootstrap_n)
    try:
        bootstrap_results = bootstrap.full_solver_bootstrap(
            data["normalized_runs"], timeout=timeout, confidence=0.95
        )
    except Exception as e:
        bootstrap_results = {"error": str(e)}
    
    # 4. Plots
    viz = SATVisualizationEngine()
    avg_ranks = None
    cd = None
    if len(data["solvers"]) >= 3 and isinstance(stat_tests, dict):
        nemenyi = stat_tests.get("nemenyi", {})
        avg_ranks = nemenyi.get("average_ranks")
        cd = nemenyi.get("critical_difference")
    
    plots = viz.generate_all_plots(
        solver_times=data["raw_solver_times"],
        par2_scores=metrics.get("par2_scores"),
        avg_ranks=avg_ranks,
        cd=cd,
        timeout=timeout,
    )
    
    # 5. Generate report
    report = ReportGenerator(
        title=f"SAT Solver Comparison — Experiment {experiment_id}"
    )
    
    experiment_info = {
        "Experiment ID": experiment_id,
        "Name": exp.get("name", "N/A"),
        "Description": exp.get("description", "N/A"),
        "Timeout": f"{timeout} seconds",
        "Solvers": ", ".join(data["solvers"]),
        "Benchmarks": len(data["benchmarks"]),
        "Total Runs": len(data["runs"]),
    }
    
    html = report.generate_html(
        metrics=_safe(metrics),
        statistical_tests=_safe(stat_tests),
        bootstrap_results=_safe(bootstrap_results),
        plots=plots,
        experiment_info=experiment_info,
    )
    
    return HTMLResponse(content=html)


@router.get("/report/{experiment_id}/pdf")
async def get_report_pdf(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300),
    bootstrap_n: int = Query(5000),
):
    """
    📄 Genera un informe PDF (requiere weasyprint).
    """
    # Generate HTML first
    html_response = await get_report_html(request, experiment_id, timeout, bootstrap_n)
    html_content = html_response.body.decode() if hasattr(html_response, 'body') else str(html_response)
    
    report = ReportGenerator()
    pdf_bytes = report.generate_pdf_bytes(html_content)
    
    if pdf_bytes is None:
        raise HTTPException(
            status_code=500,
            detail="PDF generation failed. Install weasyprint: pip install weasyprint"
        )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=experiment_{experiment_id}_report.pdf"
        }
    )


@router.get("/normality/{experiment_id}")
async def get_normality_tests(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300),
):
    """📐 Tests de normalidad por solver (Shapiro-Wilk, D'Agostino)."""
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    
    test_suite = StatisticalTestSuite()
    results = {}
    
    for solver in data["solvers"]:
        times = np.array(data["solver_times"][solver])
        results[solver] = _safe(test_suite.normality_tests(times, solver))
    
    return results


@router.get("/effect-sizes/{experiment_id}")
async def get_effect_sizes(
    request: Request,
    experiment_id: int,
    timeout: float = Query(300),
):
    """📏 Effect size measures for all pairs (Cohen's d, Vargha-Delaney A)."""
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    
    test_suite = StatisticalTestSuite()
    results = {}
    solvers = data["solvers"]
    
    for i, s1 in enumerate(solvers):
        for j, s2 in enumerate(solvers):
            if i >= j:
                continue
            t1 = np.array(data["solver_times"][s1])
            t2 = np.array(data["solver_times"][s2])
            n = min(len(t1), len(t2))
            results[f"{s1}_vs_{s2}"] = _safe({
                "cohens_d": test_suite.cohens_d(t1[:n], t2[:n]),
                "vargha_delaney": test_suite.vargha_delaney(t1[:n], t2[:n]),
            })
    
    return results


@router.get("/csv/{experiment_id}/{table_name}")
async def export_csv(
    request: Request,
    experiment_id: int,
    table_name: str,
    timeout: float = Query(300),
):
    """
    📥 Export any analysis table as CSV.
    
    table_name options:
      - metrics_ranking: Solver ranking (PAR-2, solved, solve rate)
      - par2_scores: PAR-2 scores
      - normality: Normality tests (Shapiro-Wilk, D'Agostino, Anderson-Darling) per solver
      - friedman: Friedman test result
      - nemenyi: Nemenyi post-hoc comparisons
      - corrections: Multiple comparison corrections (Bonferroni, Holm, BH)
      - effect_sizes: Cohen's d and Vargha-Delaney per pair
      - bootstrap: Bootstrap CIs per solver
      - pairwise_bootstrap: Pairwise bootstrap differences
      - full_statistical_tests: Full pairwise Wilcoxon analysis (2-solver)
    """
    db = request.app.state.db
    data = _get_experiment_data(db, experiment_id, timeout)
    output = io.StringIO()
    
    if table_name == "metrics_ranking":
        metrics_engine = BenchmarkMetrics(timeout=timeout)
        metrics = _normalize_metrics(metrics_engine.compute_all_metrics(data["normalized_runs"]))
        ranking = metrics.get("ranking", [])
        rows = []
        for entry in ranking:
            rows.append({
                "rank": entry.get("rank", ""),
                "solver": entry.get("solver", ""),
                "par2": entry.get("par2", ""),
                "solved": entry.get("solved", ""),
                "solve_rate": entry.get("solve_rate", ""),
                "avg_rank": entry.get("avg_rank", ""),
            })
        pd.DataFrame(rows).to_csv(output, index=False)

    elif table_name == "par2_scores":
        metrics_engine = BenchmarkMetrics(timeout=timeout)
        metrics = _normalize_metrics(metrics_engine.compute_all_metrics(data["normalized_runs"]))
        par2 = metrics.get("par2_scores", {})
        par10 = metrics.get("par10_scores", {})
        rows = []
        for solver in par2:
            rows.append({"solver": solver, "par2": par2.get(solver, ""), "par10": par10.get(solver, "")})
        pd.DataFrame(rows).to_csv(output, index=False)

    elif table_name == "normality":
        test_suite = StatisticalTestSuite()
        rows = []
        for solver in data["solvers"]:
            times = np.array(data["solver_times"][solver])
            norm = test_suite.normality_tests(times, solver)
            sw = norm.get("shapiro_wilk", {})
            dag = norm.get("dagostino", {})
            ad = norm.get("anderson_darling", {})
            rows.append({
                "solver": solver,
                "n": norm.get("n", ""),
                "shapiro_wilk_stat": sw.get("statistic", ""),
                "shapiro_wilk_p": sw.get("p_value", ""),
                "shapiro_wilk_normal": sw.get("is_normal", ""),
                "dagostino_stat": dag.get("statistic", ""),
                "dagostino_p": dag.get("p_value", ""),
                "dagostino_normal": dag.get("is_normal", ""),
                "anderson_darling_stat": ad.get("statistic", ""),
                "anderson_darling_normal": ad.get("is_normal", ""),
                "skewness": norm.get("skewness", ""),
                "kurtosis": norm.get("kurtosis", ""),
                "recommendation": norm.get("recommendation", ""),
            })
        pd.DataFrame(rows).to_csv(output, index=False)

    elif table_name == "friedman":
        if len(data["solvers"]) < 3:
            raise HTTPException(400, "Friedman requires ≥ 3 solvers")
        test_suite = StatisticalTestSuite()
        friedman = test_suite.friedman_test(data["time_matrix"])
        fd = friedman.to_dict()
        rows = [fd]
        pd.DataFrame(rows).to_csv(output, index=False)

    elif table_name == "nemenyi":
        if len(data["solvers"]) < 3:
            raise HTTPException(400, "Nemenyi requires ≥ 3 solvers")
        test_suite = StatisticalTestSuite()
        friedman = test_suite.friedman_test(data["time_matrix"])
        if not friedman.significant_005:
            raise HTTPException(400, "Friedman not significant; Nemenyi not applicable")
        nemenyi = test_suite.nemenyi_post_hoc(data["time_matrix"])
        comps = nemenyi.get("comparisons", [])
        pd.DataFrame(comps).to_csv(output, index=False)

    elif table_name == "corrections":
        if len(data["solvers"]) < 3:
            raise HTTPException(400, "Corrections require ≥ 3 solvers for pairwise tests")
        test_suite = StatisticalTestSuite()
        multi = test_suite.full_multi_solver_analysis(data["time_matrix"])
        mc = multi.get("multiple_corrections", {})
        if not mc:
            raise HTTPException(400, "No multiple corrections available")
        labels = mc.get("labels", [])
        bonf = mc.get("bonferroni", {})
        holm = mc.get("holm", {})
        bh = mc.get("benjamini_hochberg", {})
        rows = []
        for i, label in enumerate(labels):
            rows.append({
                "pair": label,
                "p_original": bonf.get("original_pvalues", [None]*len(labels))[i],
                "bonferroni_adjusted": bonf.get("adjusted_pvalues", [None]*len(labels))[i],
                "bonferroni_significant": bonf.get("significant_005", [None]*len(labels))[i],
                "holm_adjusted": holm.get("adjusted_pvalues", [None]*len(labels))[i],
                "holm_significant": holm.get("significant_005", [None]*len(labels))[i],
                "bh_adjusted": bh.get("adjusted_pvalues", [None]*len(labels))[i],
                "bh_significant": bh.get("significant_005", [None]*len(labels))[i],
            })
        pd.DataFrame(rows).to_csv(output, index=False)

    elif table_name == "effect_sizes":
        test_suite = StatisticalTestSuite()
        rows = []
        solvers = data["solvers"]
        for i, s1 in enumerate(solvers):
            for j, s2 in enumerate(solvers):
                if i >= j:
                    continue
                t1 = np.array(data["solver_times"][s1])
                t2 = np.array(data["solver_times"][s2])
                n = min(len(t1), len(t2))
                cd = test_suite.cohens_d(t1[:n], t2[:n])
                vd = test_suite.vargha_delaney(t1[:n], t2[:n])
                rows.append({
                    "pair": f"{s1} vs {s2}",
                    "cohens_d": cd.get("cohens_d", ""),
                    "cohens_d_interpretation": cd.get("interpretation", ""),
                    "cohens_d_direction": cd.get("direction", ""),
                    "vargha_delaney_A": vd.get("A_measure", ""),
                    "vd_interpretation": vd.get("interpretation", ""),
                    "vd_direction": vd.get("direction", ""),
                })
        pd.DataFrame(rows).to_csv(output, index=False)

    elif table_name == "bootstrap":
        engine = BootstrapEngine(n_bootstrap=5000)
        try:
            results = engine.full_solver_bootstrap(data["normalized_runs"], timeout=timeout, confidence=0.95)
        except Exception as e:
            raise HTTPException(500, f"Bootstrap failed: {e}")
        br = results.get("bootstrap_results", results)
        rows = []
        for solver, metrics_data in br.items():
            if solver in ("pairwise_differences",):
                continue
            if isinstance(metrics_data, dict):
                row = {"solver": solver}
                for metric_name, vals in metrics_data.items():
                    if isinstance(vals, dict):
                        row[f"{metric_name}_point"] = vals.get("statistic", vals.get("point_estimate", ""))
                        ci = vals.get("ci_95", vals.get("ci", []))
                        row[f"{metric_name}_ci_lower"] = vals.get("ci_lower", ci[0] if len(ci) >= 2 else "")
                        row[f"{metric_name}_ci_upper"] = vals.get("ci_upper", ci[1] if len(ci) >= 2 else "")
                rows.append(row)
        pd.DataFrame(rows).to_csv(output, index=False)

    elif table_name == "pairwise_bootstrap":
        engine = BootstrapEngine(n_bootstrap=5000)
        try:
            results = engine.full_solver_bootstrap(data["normalized_runs"], timeout=timeout, confidence=0.95)
        except Exception as e:
            raise HTTPException(500, f"Bootstrap failed: {e}")
        pd_data = results.get("pairwise_differences", {})
        rows = []
        for pair, vals in pd_data.items():
            if isinstance(vals, dict):
                rows.append({
                    "pair": pair.replace("_", " "),
                    "mean_difference": vals.get("statistic", ""),
                    "ci_lower": vals.get("ci_lower", ""),
                    "ci_upper": vals.get("ci_upper", ""),
                    "significant": vals.get("significant", ""),
                    "faster_solver": vals.get("faster_solver", ""),
                })
        pd.DataFrame(rows).to_csv(output, index=False)

    elif table_name == "full_statistical_tests":
        test_suite = StatisticalTestSuite()
        if len(data["solvers"]) >= 3:
            multi = test_suite.full_multi_solver_analysis(data["time_matrix"])
            # Export ranking + friedman + corrections as multi-sheet workaround
            rows = []
            for r in multi.get("ranking", []):
                rows.append(r)
            pd.DataFrame(rows).to_csv(output, index=False)
        elif len(data["solvers"]) == 2:
            s1, s2 = data["solvers"]
            t1 = np.array(data["solver_times"][s1])
            t2 = np.array(data["solver_times"][s2])
            n = min(len(t1), len(t2))
            pairwise = test_suite.full_pairwise_analysis(t1[:n], t2[:n], s1, s2)
            # Flatten for CSV
            flat = {
                "solver1": s1, "solver2": s2,
                "wilcoxon_stat": pairwise.get("wilcoxon", {}).get("statistic"),
                "wilcoxon_p": pairwise.get("wilcoxon", {}).get("p_value"),
                "wilcoxon_significant": pairwise.get("wilcoxon", {}).get("significant_005"),
                "mann_whitney_stat": pairwise.get("mann_whitney", {}).get("statistic"),
                "mann_whitney_p": pairwise.get("mann_whitney", {}).get("p_value"),
                "cohens_d": pairwise.get("cohens_d", {}).get("cohens_d"),
                "vargha_delaney_A": pairwise.get("vargha_delaney", {}).get("A_measure"),
            }
            pd.DataFrame([flat]).to_csv(output, index=False)
        else:
            raise HTTPException(400, "Need ≥ 2 solvers")

    else:
        raise HTTPException(400, f"Unknown table: {table_name}. Available: metrics_ranking, par2_scores, normality, friedman, nemenyi, corrections, effect_sizes, bootstrap, pairwise_bootstrap, full_statistical_tests")

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={table_name}_exp{experiment_id}.csv"
        }
    )


@router.get("/available-analyses")
async def list_available_analyses():
    """📋 Lista todos los análisis disponibles con descripciones."""
    return {
        "endpoints": [
            {
                "path": "/api/rigorous/full-analysis/{experiment_id}",
                "method": "GET",
                "description": "Complete analysis pipeline (metrics + tests + bootstrap)",
                "params": ["timeout", "bootstrap_n", "alpha"]
            },
            {
                "path": "/api/rigorous/metrics/{experiment_id}",
                "method": "GET", 
                "description": "Performance metrics: PAR-2, PAR-10, VBS, solve matrix, ranking"
            },
            {
                "path": "/api/rigorous/statistical-tests/{experiment_id}",
                "method": "GET",
                "description": "Statistical tests: Friedman/Wilcoxon + post-hoc + corrections"
            },
            {
                "path": "/api/rigorous/bootstrap/{experiment_id}",
                "method": "GET",
                "description": "Bootstrap confidence intervals (BCa method)"
            },
            {
                "path": "/api/rigorous/plots/{experiment_id}",
                "method": "GET",
                "description": "All plots as base64 images"
            },
            {
                "path": "/api/rigorous/plots/{experiment_id}/{plot_name}",
                "method": "GET",
                "description": "Single plot. Names: cactus, ecdf, boxplot, performance_profile, survival, par2_bar, scatter_<A>_vs_<B>"
            },
            {
                "path": "/api/rigorous/report/{experiment_id}",
                "method": "GET",
                "description": "Full HTML report (standalone, with embedded charts)"
            },
            {
                "path": "/api/rigorous/report/{experiment_id}/pdf",
                "method": "GET",
                "description": "PDF report (requires weasyprint)"
            },
            {
                "path": "/api/rigorous/normality/{experiment_id}",
                "method": "GET",
                "description": "Normality tests (Shapiro-Wilk, D'Agostino-Pearson)"
            },
            {
                "path": "/api/rigorous/effect-sizes/{experiment_id}",
                "method": "GET",
                "description": "Effect sizes for all pairs (Cohen's d, Vargha-Delaney A)"
            }
        ]
    }
