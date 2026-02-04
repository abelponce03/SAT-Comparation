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

