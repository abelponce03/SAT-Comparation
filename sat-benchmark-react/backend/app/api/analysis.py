"""
Analysis API endpoints
Statistical analysis and visualization data
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SCHEMAS ====================

class AnalysisRequest(BaseModel):
    experiment_ids: Optional[List[int]] = None
    solver_ids: Optional[List[int]] = None
    benchmark_families: Optional[List[str]] = None


# ==================== HELPER FUNCTIONS ====================

def calculate_par2(runs: List[Dict], timeout: float = 5000.0) -> Dict:
    """Calculate PAR-2 scores for each solver"""
    if not runs:
        return {}
    
    df = pd.DataFrame(runs)
    
    def par2_time(row):
        if pd.isna(row.get('wall_time_seconds')):
            return 2 * timeout
        if row.get('result') in ['TIMEOUT', 'MEMOUT', 'ERROR', 'UNKNOWN']:
            return 2 * timeout
        return row['wall_time_seconds']
    
    df['par2_time'] = df.apply(par2_time, axis=1)
    
    par2_scores = df.groupby('solver_name')['par2_time'].mean().to_dict()
    return {k: round(v, 2) for k, v in par2_scores.items()}


def calculate_solved_counts(runs: List[Dict]) -> Dict:
    """Count solved instances per solver"""
    if not runs:
        return {}
    
    df = pd.DataFrame(runs)
    
    result = {}
    for solver in df['solver_name'].unique():
        solver_df = df[df['solver_name'] == solver]
        result[solver] = {
            'total': len(solver_df),
            'sat': len(solver_df[solver_df['result'] == 'SAT']),
            'unsat': len(solver_df[solver_df['result'] == 'UNSAT']),
            'timeout': len(solver_df[solver_df['result'] == 'TIMEOUT']),
            'error': len(solver_df[solver_df['result'].isin(['ERROR', 'UNKNOWN', 'MEMOUT'])]),
            'solved': len(solver_df[solver_df['result'].isin(['SAT', 'UNSAT'])])
        }
        result[solver]['solved_pct'] = round(
            result[solver]['solved'] / result[solver]['total'] * 100, 2
        ) if result[solver]['total'] > 0 else 0
    
    return result


# ==================== ENDPOINTS ====================

@router.get("/summary")
async def get_analysis_summary(
    request: Request,
    experiment_id: Optional[int] = None
) -> Dict:
    """Get comprehensive analysis summary"""
    db = request.app.state.db
    
    if experiment_id:
        runs = db.get_runs(experiment_id=experiment_id)
    else:
        runs = db.get_all_runs()
    
    if not runs:
        return {
            "message": "No runs found",
            "par2_scores": {},
            "solved_counts": {},
            "total_runs": 0
        }
    
    return {
        "total_runs": len(runs),
        "par2_scores": calculate_par2(runs),
        "solved_counts": calculate_solved_counts(runs),
        "solvers": list(set(r['solver_name'] for r in runs)),
        "families": list(set(r.get('benchmark_family', 'unknown') for r in runs))
    }


@router.get("/par2")
async def get_par2_analysis(
    request: Request,
    experiment_id: Optional[int] = None,
    timeout: float = 5000.0
) -> Dict:
    """Get PAR-2 analysis with rankings"""
    db = request.app.state.db
    
    if experiment_id:
        runs = db.get_runs(experiment_id=experiment_id)
    else:
        runs = db.get_all_runs()
    
    if not runs:
        return {"rankings": [], "timeout": timeout}
    
    df = pd.DataFrame(runs)
    
    def par2_time(row):
        if pd.isna(row.get('wall_time_seconds')):
            return 2 * timeout
        if row.get('result') in ['TIMEOUT', 'MEMOUT', 'ERROR', 'UNKNOWN']:
            return 2 * timeout
        return row['wall_time_seconds']
    
    df['par2_time'] = df.apply(par2_time, axis=1)
    
    rankings = []
    for solver in df['solver_name'].unique():
        solver_df = df[df['solver_name'] == solver]
        solved = solver_df[solver_df['result'].isin(['SAT', 'UNSAT'])]
        timeouts = solver_df[solver_df['result'] == 'TIMEOUT']
        
        avg_time = solved['wall_time_seconds'].mean() if len(solved) > 0 else 0
        
        rankings.append({
            'solver_name': solver,
            'par2_score': round(solver_df['par2_time'].mean(), 2),
            'solved': len(solved),
            'total': len(solver_df),
            'timeouts': len(timeouts),
            'avg_time': round(avg_time, 3) if pd.notna(avg_time) else 0
        })
    
    # Sort by PAR-2 score
    rankings.sort(key=lambda x: x['par2_score'])
    
    return {
        "rankings": rankings,
        "timeout": timeout,
        "penalty_factor": 2
    }


@router.get("/vbs")
async def get_virtual_best_solver(
    request: Request,
    experiment_id: Optional[int] = None,
    timeout: float = 5000.0
) -> Dict:
    """Calculate Virtual Best Solver (VBS)"""
    db = request.app.state.db
    
    if experiment_id:
        runs = db.get_runs(experiment_id=experiment_id)
    else:
        runs = db.get_all_runs()
    
    if not runs:
        return {"message": "No runs found"}
    
    df = pd.DataFrame(runs)
    
    # Filter only solved instances
    solved_df = df[df['result'].isin(['SAT', 'UNSAT'])]
    
    # Pivot: benchmark x solver
    pivot = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='wall_time_seconds',
        aggfunc='first'
    ).fillna(2 * timeout)  # Penalty for unsolved
    
    if pivot.empty:
        return {"message": "No data"}
    
    # Best time per benchmark
    vbs_times = pivot.min(axis=1)
    vbs_solvers = pivot.idxmin(axis=1)
    
    # Count VBS solved (at least one solver solved it)
    solved_by_any = solved_df.groupby('benchmark_name').size()
    vbs_solved = len(solved_by_any)
    
    # Best single solver
    solver_solved = solved_df.groupby('solver_name')['benchmark_name'].nunique()
    best_single_solver = solver_solved.idxmax() if len(solver_solved) > 0 else None
    best_single_solved = solver_solved.max() if len(solver_solved) > 0 else 0
    
    # Contribution by solver (times each solver is the best)
    contribution = vbs_solvers.value_counts().to_dict()
    total_best_picks = sum(contribution.values())
    
    contributions = []
    for solver, count in sorted(contribution.items(), key=lambda x: -x[1]):
        contributions.append({
            'solver': solver,
            'unique_wins': count,
            'percentage': round(count / total_best_picks * 100, 1) if total_best_picks > 0 else 0
        })
    
    return {
        "vbs_solved": vbs_solved,
        "best_single_solver": best_single_solver,
        "best_single_solved": int(best_single_solved),
        "contributions": contributions,
        "vbs_average_time": round(vbs_times.mean(), 2),
        "total_benchmarks": len(pivot)
    }


@router.get("/pairwise")
async def get_pairwise_comparison(
    request: Request,
    experiment_id: int,
    solver1: Optional[str] = None,
    solver2: Optional[str] = None
) -> Dict:
    """Compare solvers pairwise - returns matrix if no specific solvers specified"""
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        return {"message": "No runs found"}
    
    df = pd.DataFrame(runs)
    solvers = list(df['solver_name'].unique())
    
    # If specific solvers requested, do detailed comparison
    if solver1 and solver2:
        df1 = df[df['solver_name'] == solver1].set_index('benchmark_name')
        df2 = df[df['solver_name'] == solver2].set_index('benchmark_name')
        
        common = df1.index.intersection(df2.index)
        
        if len(common) == 0:
            return {
                "error": "No common benchmarks",
                "solver1": solver1,
                "solver2": solver2
            }
        
        df1 = df1.loc[common]
        df2 = df2.loc[common]
        
        both_solved = (
            df1['result'].isin(['SAT', 'UNSAT']) & 
            df2['result'].isin(['SAT', 'UNSAT'])
        )
        
        wins1 = int((df1.loc[both_solved, 'wall_time_seconds'] < 
                 df2.loc[both_solved, 'wall_time_seconds']).sum())
        wins2 = int((df2.loc[both_solved, 'wall_time_seconds'] < 
                 df1.loc[both_solved, 'wall_time_seconds']).sum())
        
        return {
            "solver1": solver1,
            "solver2": solver2,
            "common_benchmarks": len(common),
            "both_solved": int(both_solved.sum()),
            "wins_1": wins1,
            "wins_2": wins2
        }
    
    # Build comparison matrix
    n = len(solvers)
    matrix = [[0] * n for _ in range(n)]
    
    # Pivot times
    pivot = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='wall_time_seconds',
        aggfunc='first'
    )
    
    # Pivot results
    results = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='result',
        aggfunc='first'
    )
    
    for i, s1 in enumerate(solvers):
        for j, s2 in enumerate(solvers):
            if i == j or s1 not in pivot.columns or s2 not in pivot.columns:
                continue
            
            # Count wins
            wins = 0
            for bench in pivot.index:
                t1 = pivot.loc[bench, s1]
                t2 = pivot.loc[bench, s2]
                r1 = results.loc[bench, s1] if s1 in results.columns else None
                r2 = results.loc[bench, s2] if s2 in results.columns else None
                
                # Only compare if both solved
                if r1 in ['SAT', 'UNSAT'] and r2 in ['SAT', 'UNSAT']:
                    if pd.notna(t1) and pd.notna(t2) and t1 < t2:
                        wins += 1
            
            matrix[i][j] = wins
    
    # Summary
    summary = []
    for i, solver in enumerate(solvers):
        wins = sum(matrix[i])
        losses = sum(matrix[j][i] for j in range(n))
        summary.append({
            'solver': solver,
            'wins': wins,
            'losses': losses
        })
    summary.sort(key=lambda x: -x['wins'])
    
    return {
        "solvers": solvers,
        "matrix": matrix,
        "summary": summary
    }


@router.get("/cactus-data")
async def get_cactus_plot_data(
    request: Request,
    experiment_id: Optional[int] = None,
    solver_ids: Optional[str] = None
) -> Dict:
    """Get data for cactus plot"""
    db = request.app.state.db
    
    if experiment_id:
        runs = db.get_runs(experiment_id=experiment_id)
    else:
        runs = db.get_all_runs()
    
    if not runs:
        return {"series": []}
    
    df = pd.DataFrame(runs)
    
    # Filter solvers if specified
    if solver_ids:
        ids = [int(x) for x in solver_ids.split(',')]
        df = df[df['solver_id'].isin(ids)]
    
    series = []
    
    for solver in df['solver_name'].unique():
        solver_df = df[df['solver_name'] == solver]
        
        # Only solved instances
        solved = solver_df[solver_df['result'].isin(['SAT', 'UNSAT'])]
        times = sorted(solved['wall_time_seconds'].dropna().tolist())
        
        data_points = [
            {"x": i + 1, "y": t}
            for i, t in enumerate(times)
        ]
        
        series.append({
            "name": solver,
            "data": data_points,
            "total_solved": len(times)
        })
    
    return {
        "series": series,
        "x_label": "Number of Solved Instances",
        "y_label": "Time (seconds)",
        "y_scale": "log"
    }


@router.get("/scatter-data")
async def get_scatter_plot_data(
    request: Request,
    solver1: str,
    solver2: str,
    experiment_id: Optional[int] = None
) -> Dict:
    """Get data for scatter comparison plot"""
    db = request.app.state.db
    
    if experiment_id:
        runs = db.get_runs(experiment_id=experiment_id)
    else:
        runs = db.get_all_runs()
    
    if not runs:
        return {"points": []}
    
    df = pd.DataFrame(runs)
    
    # Pivot
    pivot = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='wall_time_seconds',
        aggfunc='first'
    )
    
    if solver1 not in pivot.columns or solver2 not in pivot.columns:
        return {"error": "Solvers not found", "points": []}
    
    # Get result info
    results = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='result',
        aggfunc='first'
    )
    
    points = []
    for benchmark in pivot.index:
        x = pivot.loc[benchmark, solver1]
        y = pivot.loc[benchmark, solver2]
        result = results.loc[benchmark, solver1] if solver1 in results.columns else 'UNKNOWN'
        
        if pd.notna(x) and pd.notna(y):
            points.append({
                "benchmark": benchmark,
                "x": x,
                "y": y,
                "result": result
            })
    
    return {
        "points": points,
        "solver1": solver1,
        "solver2": solver2,
        "x_label": f"{solver1} Time (s)",
        "y_label": f"{solver2} Time (s)"
    }


@router.get("/heatmap-data")
async def get_heatmap_data(
    request: Request,
    experiment_id: Optional[int] = None,
    metric: str = "wall_time_seconds"
) -> Dict:
    """Get data for result heatmap"""
    db = request.app.state.db
    
    if experiment_id:
        runs = db.get_runs(experiment_id=experiment_id)
    else:
        runs = db.get_all_runs()
    
    if not runs:
        return {"data": [], "solvers": [], "benchmarks": []}
    
    df = pd.DataFrame(runs)
    
    # Limit to manageable size
    top_benchmarks = df['benchmark_name'].value_counts().head(50).index.tolist()
    df = df[df['benchmark_name'].isin(top_benchmarks)]
    
    pivot = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values=metric,
        aggfunc='first'
    )
    
    # Convert to format for heatmap
    data = []
    for i, benchmark in enumerate(pivot.index):
        for j, solver in enumerate(pivot.columns):
            value = pivot.loc[benchmark, solver]
            data.append({
                "x": j,
                "y": i,
                "value": float(value) if pd.notna(value) else None,
                "benchmark": benchmark,
                "solver": solver
            })
    
    return {
        "data": data,
        "solvers": list(pivot.columns),
        "benchmarks": list(pivot.index),
        "metric": metric
    }


@router.get("/performance-profile")
async def get_performance_profile(
    request: Request,
    experiment_id: Optional[int] = None,
    max_ratio: float = 10.0
) -> Dict:
    """Get performance profile (ECDF) data"""
    db = request.app.state.db
    
    if experiment_id:
        runs = db.get_runs(experiment_id=experiment_id)
    else:
        runs = db.get_all_runs()
    
    if not runs:
        return {"series": []}
    
    df = pd.DataFrame(runs)
    
    # Get times matrix
    pivot = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='wall_time_seconds',
        aggfunc='first'
    ).fillna(float('inf'))
    
    # Calculate ratios to virtual best
    vbs = pivot.min(axis=1)
    ratios = pivot.div(vbs, axis=0)
    
    # Generate profile points
    tau_values = np.linspace(1, max_ratio, 100)
    series = []
    
    for solver in ratios.columns:
        solver_ratios = ratios[solver].replace([np.inf, -np.inf], max_ratio * 2)
        
        profile = []
        for tau in tau_values:
            fraction = (solver_ratios <= tau).mean()
            profile.append({"x": tau, "y": fraction})
        
        series.append({
            "name": solver,
            "data": profile
        })
    
    return {
        "series": series,
        "x_label": "Performance Ratio τ",
        "y_label": "Fraction of Problems Solved",
        "max_ratio": max_ratio
    }


@router.get("/family-analysis")
async def get_family_analysis(
    request: Request,
    experiment_id: Optional[int] = None
) -> Dict:
    """Analyze performance by benchmark family"""
    db = request.app.state.db
    
    if experiment_id:
        runs = db.get_runs(experiment_id=experiment_id)
    else:
        runs = db.get_all_runs()
    
    if not runs:
        return {"families": {}}
    
    df = pd.DataFrame(runs)
    
    result = {}
    
    for family in df['benchmark_family'].unique():
        family_df = df[df['benchmark_family'] == family]
        
        family_stats = {}
        for solver in family_df['solver_name'].unique():
            solver_df = family_df[family_df['solver_name'] == solver]
            solved = solver_df[solver_df['result'].isin(['SAT', 'UNSAT'])]
            
            family_stats[solver] = {
                'total': len(solver_df),
                'solved': len(solved),
                'solved_pct': round(len(solved) / len(solver_df) * 100, 2) if len(solver_df) > 0 else 0,
                'avg_time': round(solved['wall_time_seconds'].mean(), 2) if len(solved) > 0 else None
            }
        
        result[family] = family_stats
    
    return {"families": result}


# ==================== VISUALIZATION ENDPOINTS ====================

@router.get("/cactus")
async def get_cactus_data(
    request: Request,
    experiment_id: int,
    timeout: float = 5000.0
) -> Dict:
    """Get data for cactus plot - sorted times per solver"""
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        return {"solvers": {}}
    
    df = pd.DataFrame(runs)
    result = {}
    
    for solver in df['solver_name'].unique():
        solver_df = df[df['solver_name'] == solver]
        solved = solver_df[solver_df['result'].isin(['SAT', 'UNSAT'])]
        times = sorted(solved['wall_time_seconds'].dropna().tolist())
        result[solver] = times
    
    return {"solvers": result, "timeout": timeout}


@router.get("/scatter")
async def get_scatter_data(
    request: Request,
    experiment_id: int
) -> Dict:
    """Get data for scatter plot comparison"""
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        return {"solvers": [], "points": []}
    
    df = pd.DataFrame(runs)
    solvers = list(df['solver_name'].unique())
    
    # Create all pairwise points
    pivot = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='wall_time_seconds',
        aggfunc='first'
    )
    
    points = []
    for i, s1 in enumerate(solvers):
        for j, s2 in enumerate(solvers):
            if i >= j or s1 not in pivot.columns or s2 not in pivot.columns:
                continue
            
            for benchmark in pivot.index:
                t1 = pivot.loc[benchmark, s1]
                t2 = pivot.loc[benchmark, s2]
                if pd.notna(t1) and pd.notna(t2):
                    points.append({
                        "benchmark": benchmark,
                        "solver1": s1,
                        "solver2": s2,
                        "time1": float(t1),
                        "time2": float(t2)
                    })
    
    return {"solvers": solvers, "points": points}


@router.get("/ecdf")
async def get_ecdf_data(
    request: Request,
    experiment_id: int,
    max_ratio: float = 100.0
) -> Dict:
    """Get ECDF / performance profile data"""
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        return {"profiles": {}}
    
    df = pd.DataFrame(runs)
    
    # Get times matrix
    pivot = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='wall_time_seconds',
        aggfunc='first'
    ).fillna(float('inf'))
    
    if pivot.empty:
        return {"profiles": {}}
    
    # Calculate ratios to virtual best
    vbs = pivot.min(axis=1)
    vbs = vbs.replace(0, 0.001)  # Avoid division by zero
    ratios = pivot.div(vbs, axis=0)
    
    profiles = {}
    tau_values = np.concatenate([
        np.linspace(1, 2, 20),
        np.linspace(2, 10, 30),
        np.linspace(10, max_ratio, 20)
    ])
    tau_values = sorted(set(tau_values))
    
    for solver in ratios.columns:
        solver_ratios = ratios[solver].replace([np.inf, -np.inf], max_ratio * 2)
        
        profile = []
        for tau in tau_values:
            fraction = float((solver_ratios <= tau).mean())
            profile.append({"ratio": round(tau, 3), "probability": fraction})
        
        profiles[solver] = profile
    
    return {"profiles": profiles}


@router.get("/heatmap")
async def get_heatmap_data_simple(
    request: Request,
    experiment_id: int
) -> Dict:
    """Get data for heatmap visualization"""
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        return {"solvers": [], "benchmarks": [], "matrix": {}}
    
    df = pd.DataFrame(runs)
    
    # Limit benchmarks
    top_benchmarks = df.groupby('benchmark_name')['wall_time_seconds'].count()
    top_benchmarks = top_benchmarks.nlargest(50).index.tolist()
    df = df[df['benchmark_name'].isin(top_benchmarks)]
    
    pivot = df.pivot_table(
        index='benchmark_name',
        columns='solver_name',
        values='wall_time_seconds',
        aggfunc='first'
    )
    
    # Build matrix: solver -> benchmark -> time
    matrix = {}
    for solver in pivot.columns:
        matrix[solver] = {}
        for benchmark in pivot.index:
            val = pivot.loc[benchmark, solver]
            matrix[solver][benchmark] = float(val) if pd.notna(val) else None
    
    max_time = df['wall_time_seconds'].max() if not df.empty else 5000
    
    return {
        "solvers": list(pivot.columns),
        "benchmarks": list(pivot.index),
        "matrix": matrix,
        "max_time": float(max_time) if pd.notna(max_time) else 5000
    }


@router.get("/by-family")
async def get_analysis_by_family(
    request: Request,
    experiment_id: int,
    timeout: float = 5000.0
) -> Dict:
    """Get analysis broken down by benchmark family"""
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        return {"families": []}
    
    df = pd.DataFrame(runs)
    
    families = []
    
    for family in df['benchmark_family'].unique():
        family_df = df[df['benchmark_family'] == family]
        family_count = len(family_df['benchmark_name'].unique())
        
        solvers = []
        for solver in family_df['solver_name'].unique():
            solver_df = family_df[family_df['solver_name'] == solver]
            solved = solver_df[solver_df['result'].isin(['SAT', 'UNSAT'])]
            
            # Calculate PAR-2 for this family
            def par2_time(row):
                if pd.isna(row.get('wall_time_seconds')):
                    return 2 * timeout
                if row.get('result') in ['TIMEOUT', 'MEMOUT', 'ERROR', 'UNKNOWN']:
                    return 2 * timeout
                return row['wall_time_seconds']
            
            solver_df = solver_df.copy()
            solver_df['par2'] = solver_df.apply(par2_time, axis=1)
            
            solvers.append({
                'name': solver,
                'solved': len(solved),
                'par2': round(solver_df['par2'].mean(), 2),
                'avg_time': round(solved['wall_time_seconds'].mean(), 3) if len(solved) > 0 else 0
            })
        
        # Sort by PAR-2
        solvers.sort(key=lambda x: x['par2'])
        
        families.append({
            'name': family,
            'count': family_count,
            'solvers': solvers
        })
    
    return {"families": families}


@router.get("/export")
async def export_results(
    request: Request,
    experiment_id: int,
    format: str = "csv"
):
    """Export experiment results"""
    from fastapi.responses import StreamingResponse
    import io
    
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        raise HTTPException(status_code=404, detail="No results found")
    
    df = pd.DataFrame(runs)
    
    if format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=experiment_{experiment_id}_results.csv"}
        )
    else:
        raise HTTPException(status_code=400, detail="Format not supported")


@router.get("/statistical-tests")
async def get_statistical_tests(
    request: Request,
    experiment_id: int,
    solver1: str,
    solver2: str
) -> Dict:
    """
    Perform comprehensive statistical tests between two solvers.
    Includes: Wilcoxon, Mann-Whitney U, t-test, effect size
    """
    from scipy import stats as scipy_stats
    
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        raise HTTPException(status_code=404, detail="No runs found")
    
    df = pd.DataFrame(runs)
    
    # Get runs for each solver
    df1 = df[df['solver_name'] == solver1]
    df2 = df[df['solver_name'] == solver2]
    
    if len(df1) == 0 or len(df2) == 0:
        raise HTTPException(status_code=404, detail="One or both solvers not found")
    
    # Get common benchmarks where both solved
    solved1 = df1[df1['result'].isin(['SAT', 'UNSAT'])].set_index('benchmark_name')
    solved2 = df2[df2['result'].isin(['SAT', 'UNSAT'])].set_index('benchmark_name')
    
    common = solved1.index.intersection(solved2.index)
    
    if len(common) < 3:
        return {
            "error": "Insufficient common solved benchmarks for statistical tests",
            "common_solved": len(common),
            "solver1_solved": len(solved1),
            "solver2_solved": len(solved2)
        }
    
    times1 = solved1.loc[common, 'wall_time_seconds'].values.astype(float)
    times2 = solved2.loc[common, 'wall_time_seconds'].values.astype(float)
    
    results = {
        "solvers": {"solver1": solver1, "solver2": solver2},
        "sample_sizes": {
            "solver1_total": len(df1),
            "solver2_total": len(df2),
            "solver1_solved": len(solved1),
            "solver2_solved": len(solved2),
            "common_solved": len(common)
        },
        "descriptive_stats": {
            solver1: {
                "mean": float(np.mean(times1)),
                "std": float(np.std(times1)),
                "median": float(np.median(times1)),
                "min": float(np.min(times1)),
                "max": float(np.max(times1)),
                "q1": float(np.percentile(times1, 25)),
                "q3": float(np.percentile(times1, 75)),
                "iqr": float(np.percentile(times1, 75) - np.percentile(times1, 25)),
                "total_time": float(np.sum(times1))
            },
            solver2: {
                "mean": float(np.mean(times2)),
                "std": float(np.std(times2)),
                "median": float(np.median(times2)),
                "min": float(np.min(times2)),
                "max": float(np.max(times2)),
                "q1": float(np.percentile(times2, 25)),
                "q3": float(np.percentile(times2, 75)),
                "iqr": float(np.percentile(times2, 75) - np.percentile(times2, 25)),
                "total_time": float(np.sum(times2))
            }
        },
        "tests": {}
    }
    
    # Wilcoxon signed-rank test (paired, non-parametric)
    try:
        stat, p_value = scipy_stats.wilcoxon(times1, times2)
        results["tests"]["wilcoxon_signed_rank"] = {
            "statistic": float(stat),
            "p_value": float(p_value),
            "significant_005": bool(p_value < 0.05),
            "significant_001": bool(p_value < 0.01),
            "description": "Non-parametric test for paired samples"
        }
    except Exception as e:
        results["tests"]["wilcoxon_signed_rank"] = {"error": str(e)}
    
    # Mann-Whitney U test (unpaired, non-parametric)
    try:
        stat, p_value = scipy_stats.mannwhitneyu(times1, times2, alternative='two-sided')
        results["tests"]["mann_whitney_u"] = {
            "statistic": float(stat),
            "p_value": float(p_value),
            "significant_005": bool(p_value < 0.05),
            "significant_001": bool(p_value < 0.01),
            "description": "Non-parametric test for independent samples"
        }
    except Exception as e:
        results["tests"]["mann_whitney_u"] = {"error": str(e)}
    
    # Paired t-test (parametric)
    try:
        stat, p_value = scipy_stats.ttest_rel(times1, times2)
        results["tests"]["paired_t_test"] = {
            "statistic": float(stat),
            "p_value": float(p_value),
            "significant_005": bool(p_value < 0.05),
            "significant_001": bool(p_value < 0.01),
            "description": "Parametric test for paired samples (assumes normality)"
        }
    except Exception as e:
        results["tests"]["paired_t_test"] = {"error": str(e)}
    
    # Independent t-test
    try:
        stat, p_value = scipy_stats.ttest_ind(times1, times2)
        results["tests"]["independent_t_test"] = {
            "statistic": float(stat),
            "p_value": float(p_value),
            "significant_005": bool(p_value < 0.05),
            "description": "Parametric test for independent samples"
        }
    except Exception as e:
        results["tests"]["independent_t_test"] = {"error": str(e)}
    
    # Effect size (Cohen's d for paired samples)
    try:
        diff = times1 - times2
        cohens_d = np.mean(diff) / np.std(diff, ddof=1)
        
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            interpretation = "negligible"
        elif abs_d < 0.5:
            interpretation = "small"
        elif abs_d < 0.8:
            interpretation = "medium"
        else:
            interpretation = "large"
        
        results["tests"]["effect_size"] = {
            "cohens_d": float(cohens_d),
            "interpretation": interpretation,
            "description": "Standardized mean difference (d<0.2: negligible, d<0.5: small, d<0.8: medium, d>=0.8: large)"
        }
    except Exception as e:
        results["tests"]["effect_size"] = {"error": str(e)}
    
    # Normality tests (Shapiro-Wilk)
    try:
        stat1, p1 = scipy_stats.shapiro(times1[:min(50, len(times1))])
        stat2, p2 = scipy_stats.shapiro(times2[:min(50, len(times2))])
        results["normality_tests"] = {
            solver1: {
                "shapiro_statistic": float(stat1),
                "p_value": float(p1),
                "is_normal_005": bool(p1 > 0.05)
            },
            solver2: {
                "shapiro_statistic": float(stat2),
                "p_value": float(p2),
                "is_normal_005": bool(p2 > 0.05)
            },
            "recommendation": "Use non-parametric tests if either distribution is non-normal"
        }
    except Exception as e:
        results["normality_tests"] = {"error": str(e)}
    
    # Wins/losses analysis
    wins1 = int(np.sum(times1 < times2))
    wins2 = int(np.sum(times2 < times1))
    ties = len(common) - wins1 - wins2
    
    results["pairwise_wins"] = {
        f"{solver1}_faster": wins1,
        f"{solver2}_faster": wins2,
        "ties": ties,
        "speedup_factor": float(np.mean(times2) / np.mean(times1)) if np.mean(times1) > 0 else None
    }
    
    return results


@router.get("/cdcl-metrics")
async def get_cdcl_metrics(
    request: Request,
    experiment_id: int
) -> Dict:
    """
    Get detailed CDCL solver metrics for an experiment.
    Includes conflicts, decisions, propagations, restarts, etc.
    """
    db = request.app.state.db
    runs = db.get_runs(experiment_id=experiment_id)
    
    if not runs:
        raise HTTPException(status_code=404, detail="No runs found")
    
    df = pd.DataFrame(runs)
    
    def safe_float(val, default=0.0):
        """Convert value to float safely, handling NaN/Inf"""
        if pd.isna(val) or np.isinf(val):
            return default
        return float(val)
    
    def safe_int(val, default=0):
        """Convert value to int safely, handling NaN"""
        if pd.isna(val):
            return default
        return int(val)
    
    metrics_by_solver = {}
    for solver in df['solver_name'].unique():
        solver_df = df[df['solver_name'] == solver]
        solved_df = solver_df[solver_df['result'].isin(['SAT', 'UNSAT'])]
        
        # Aggregate CDCL metrics with safe handling
        total_conflicts = solved_df['conflicts'].sum() if 'conflicts' in solved_df.columns else 0
        total_decisions = solved_df['decisions'].sum() if 'decisions' in solved_df.columns else 0
        total_propagations = solved_df['propagations'].sum() if 'propagations' in solved_df.columns else 0
        total_restarts = solved_df['restarts'].sum() if 'restarts' in solved_df.columns else 0
        total_time = solved_df['wall_time_seconds'].sum() if 'wall_time_seconds' in solved_df.columns else 0
        
        metrics_by_solver[solver] = {
            "totals": {
                "conflicts": safe_int(total_conflicts),
                "decisions": safe_int(total_decisions),
                "propagations": safe_int(total_propagations),
                "restarts": safe_int(total_restarts),
                "solve_time": safe_float(total_time)
            },
            "rates": {
                "conflicts_per_second": safe_float(total_conflicts / total_time) if safe_float(total_time) > 0 else 0.0,
                "decisions_per_second": safe_float(total_decisions / total_time) if safe_float(total_time) > 0 else 0.0,
                "propagations_per_second": safe_float(total_propagations / total_time) if safe_float(total_time) > 0 else 0.0,
                "propagations_per_decision": safe_float(total_propagations / total_decisions) if safe_int(total_decisions) > 0 else 0.0,
                "conflicts_per_restart": safe_float(total_conflicts / total_restarts) if safe_int(total_restarts) > 0 else 0.0
            },
            "averages_per_instance": {
                "avg_conflicts": safe_float(solved_df['conflicts'].mean()) if len(solved_df) > 0 and 'conflicts' in solved_df.columns else 0.0,
                "avg_decisions": safe_float(solved_df['decisions'].mean()) if len(solved_df) > 0 and 'decisions' in solved_df.columns else 0.0,
                "avg_propagations": safe_float(solved_df['propagations'].mean()) if len(solved_df) > 0 and 'propagations' in solved_df.columns else 0.0,
                "avg_restarts": safe_float(solved_df['restarts'].mean()) if len(solved_df) > 0 and 'restarts' in solved_df.columns else 0.0
            },
            "solved_instances": len(solved_df)
        }
    
    return {
        "experiment_id": experiment_id,
        "metrics_by_solver": metrics_by_solver
    }


@router.get("/metrics-list")
async def get_available_metrics() -> Dict:
    """List all available metrics and their descriptions for rigorous analysis"""
    return {
        "timing_metrics": {
            "wall_time_seconds": "Total elapsed time (wall clock) - primary performance metric",
            "cpu_time_seconds": "CPU time used by the process",
            "user_time_seconds": "Time spent in user mode",
            "system_time_seconds": "Time spent in kernel mode"
        },
        "result_metrics": {
            "result": "Outcome: SAT (satisfiable), UNSAT (unsatisfiable), TIMEOUT, ERROR, UNKNOWN",
            "exit_code": "Process exit code (standard: 10=SAT, 20=UNSAT)",
            "verified": "Whether result was verified by independent checker"
        },
        "memory_metrics": {
            "max_memory_kb": "Peak memory usage in kilobytes",
            "avg_memory_kb": "Average memory usage during execution"
        },
        "cdcl_metrics": {
            "conflicts": "Number of conflicts detected during search",
            "decisions": "Number of decision variables chosen (branching points)",
            "propagations": "Number of unit propagations performed",
            "restarts": "Number of search restarts triggered",
            "learnt_clauses": "Number of conflict-driven learned clauses",
            "deleted_clauses": "Number of learned clauses deleted (clause database management)"
        },
        "aggregate_metrics": {
            "par2_score": "Penalized Average Runtime with factor 2: PAR2 = avg(t) + 2×timeout×unsolved_fraction",
            "par10_score": "Penalized Average Runtime with factor 10 (harsher penalty)",
            "vbs_time": "Virtual Best Solver time - hypothetical best selection per instance",
            "solve_rate": "Percentage of instances solved within timeout"
        },
        "derived_metrics": {
            "conflicts_per_second": "Conflict detection rate - indicates search efficiency",
            "decisions_per_second": "Decision rate - indicates branching speed",
            "propagations_per_second": "Propagation rate - indicates BCP efficiency",
            "propagations_per_decision": "Propagation yield - higher = better unit propagation",
            "conflicts_per_restart": "Average conflicts before restart - restart policy aggressiveness"
        },
        "statistical_tests": {
            "wilcoxon_signed_rank": "Non-parametric paired test - recommended for SAT solver comparison",
            "mann_whitney_u": "Non-parametric unpaired test - for independent samples",
            "paired_t_test": "Parametric paired test - requires normal distribution assumption",
            "cohens_d": "Effect size measure - quantifies practical significance",
            "shapiro_wilk": "Normality test - validates parametric test assumptions"
        },
        "visualization_data": {
            "cactus_plot": "Number of instances solved vs runtime threshold",
            "scatter_plot": "Pairwise solver comparison on common benchmarks",
            "ecdf": "Empirical Cumulative Distribution Function of runtimes",
            "performance_profile": "Probability of being within factor τ of best solver",
            "heatmap": "Solver performance across benchmark families"
        }
    }
