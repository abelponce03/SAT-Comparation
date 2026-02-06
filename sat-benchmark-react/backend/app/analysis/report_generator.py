"""
Report Generator for SAT Solver Comparison
============================================

Genera informes completos en HTML y PDF con:
- Resumen ejecutivo
- Tablas de métricas (PAR-2, solve rates, etc.)
- Gráficos embebidos (base64)
- Resultados de tests estadísticos con interpretación
- Intervalos de confianza Bootstrap
- Recomendaciones automáticas

El informe sigue la estructura de publicaciones en SAT Competition.
"""

import os
import json
import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Genera informes profesionales de comparación de SAT solvers.
    """
    
    def __init__(self, title: str = "SAT Solver Comparison Report"):
        self.title = title
        self.generated_at = datetime.datetime.now().isoformat()
    
    def generate_html(self, 
                      metrics: Optional[Dict] = None,
                      statistical_tests: Optional[Dict] = None,
                      bootstrap_results: Optional[Dict] = None,
                      plots: Optional[Dict[str, str]] = None,
                      experiment_info: Optional[Dict] = None) -> str:
        """
        Genera un informe HTML completo y auto-contenido.
        
        Los gráficos se embeben como base64, así que el HTML es standalone.
        """
        sections = []
        
        # Header
        sections.append(self._html_header())
        
        # Executive Summary
        sections.append(self._section_executive_summary(metrics, statistical_tests))
        
        # Experiment Info
        if experiment_info:
            sections.append(self._section_experiment_info(experiment_info))
        
        # Metrics tables
        if metrics:
            sections.append(self._section_metrics(metrics))
        
        # Plots
        if plots:
            sections.append(self._section_plots(plots))
        
        # Statistical Tests
        if statistical_tests:
            sections.append(self._section_statistical_tests(statistical_tests))
        
        # Bootstrap CIs
        if bootstrap_results:
            sections.append(self._section_bootstrap(bootstrap_results))
        
        # Methodology
        sections.append(self._section_methodology())
        
        # Footer
        sections.append(self._html_footer())
        
        return "\n".join(sections)
    
    def generate_pdf_bytes(self, html_content: str) -> Optional[bytes]:
        """
        Convierte HTML a PDF usando weasyprint.
        Returns None si weasyprint no está disponible.
        """
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            logger.warning("weasyprint not installed. PDF generation unavailable.")
            return None
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return None
    
    # ==================== HTML SECTIONS ====================
    
    def _html_header(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        :root {{
            --primary: #2563EB;
            --success: #059669;
            --warning: #D97706;
            --danger: #DC2626;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        h1 {{
            font-size: 2rem;
            color: var(--primary);
            border-bottom: 3px solid var(--primary);
            padding-bottom: 0.5rem;
            margin-bottom: 1.5rem;
        }}
        
        h2 {{
            font-size: 1.5rem;
            color: var(--text);
            margin-top: 2rem;
            margin-bottom: 1rem;
            padding-bottom: 0.3rem;
            border-bottom: 1px solid var(--border);
        }}
        
        h3 {{ font-size: 1.2rem; margin: 1rem 0 0.5rem; }}
        
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .badge-success {{ background: #d1fae5; color: #065f46; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-danger  {{ background: #fee2e2; color: #991b1b; }}
        .badge-info    {{ background: #dbeafe; color: #1e40af; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }}
        
        th, td {{
            padding: 0.6rem 0.8rem;
            text-align: left;
            border: 1px solid var(--border);
        }}
        
        th {{
            background: #f1f5f9;
            font-weight: 600;
            color: var(--text);
        }}
        
        tr:nth-child(even) td {{ background: #f8fafc; }}
        tr:hover td {{ background: #eff6ff; }}
        
        .plot-container {{
            text-align: center;
            margin: 1.5rem 0;
        }}
        
        .plot-container img {{
            max-width: 100%;
            border: 1px solid var(--border);
            border-radius: 4px;
        }}
        
        .plot-title {{
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--text-muted);
        }}
        
        .interpretation {{
            background: #eff6ff;
            border-left: 4px solid var(--primary);
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 0 4px 4px 0;
        }}
        
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }}
        
        .metric-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }}
        
        .metric-value {{ font-size: 1.8rem; font-weight: 700; color: var(--primary); }}
        .metric-label {{ font-size: 0.85rem; color: var(--text-muted); }}
        
        .footer {{
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        
        .significant {{ color: var(--success); font-weight: 600; }}
        .not-significant {{ color: var(--text-muted); }}
        
        @media print {{
            body {{ padding: 1rem; }}
            .card {{ box-shadow: none; page-break-inside: avoid; }}
            .plot-container {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>📊 {self.title}</h1>
    <p style="color: var(--text-muted);">Generated: {self.generated_at}</p>
"""
    
    def _html_footer(self) -> str:
        return """
    <div class="footer">
        <p>Generated by SAT Benchmark Suite — Rigorous Analysis Module</p>
        <p>Statistical methodology based on Demšar (2006) and Arcuri & Briand (2011)</p>
    </div>
</div>
</body>
</html>"""
    
    def _section_executive_summary(self, metrics: Optional[Dict], 
                                    tests: Optional[Dict]) -> str:
        html = '<h2>📋 Executive Summary</h2>\n<div class="card">\n'
        
        if metrics and "ranking" in metrics:
            ranking = metrics["ranking"]
            if ranking:
                best = ranking[0] if isinstance(ranking[0], dict) else {"solver": str(ranking[0])}
                solver_name = best.get("solver", "Unknown")
                html += f'<p><strong>Best solver:</strong> <span class="badge badge-success">{solver_name}</span></p>\n'
        
        if metrics:
            if "par2_scores" in metrics:
                scores = metrics["par2_scores"]
                html += '<div class="grid" style="margin-top: 1rem;">\n'
                for solver, score in sorted(scores.items(), key=lambda x: x[1]):
                    html += f"""<div class="metric-card">
                        <div class="metric-value">{score:.1f}</div>
                        <div class="metric-label">{solver} PAR-2</div>
                    </div>\n"""
                html += '</div>\n'
            
            if "solve_matrix" in metrics:
                sm = metrics["solve_matrix"]
                if "solver_totals" in sm:
                    html += '<p style="margin-top: 1rem;"><strong>Instances solved:</strong> '
                    parts = []
                    for s, total in sm["solver_totals"].items():
                        parts.append(f"{s}: {total}")
                    html += ", ".join(parts) + '</p>\n'
        
        if tests:
            if "friedman" in tests:
                f = tests["friedman"]
                p = f.get("p_value", 1.0)
                sig = "significant" if p < 0.05 else "NOT significant"
                css = "significant" if p < 0.05 else "not-significant"
                html += f'<p><strong>Friedman test:</strong> <span class="{css}">{sig} (p = {p:.4f})</span></p>\n'
            
            if "interpretation" in tests:
                interp = tests["interpretation"]
                html += f'<div class="interpretation"><strong>Interpretation:</strong> {interp.get("summary", "")}</div>\n'
        
        html += '</div>\n'
        return html
    
    def _section_experiment_info(self, info: Dict) -> str:
        html = '<h2>🔬 Experiment Details</h2>\n<div class="card">\n<table>\n'
        for key, val in info.items():
            html += f'<tr><th>{key}</th><td>{val}</td></tr>\n'
        html += '</table>\n</div>\n'
        return html
    
    def _section_metrics(self, metrics: Dict) -> str:
        html = '<h2>📈 Performance Metrics</h2>\n'
        
        # PAR-2 Scores
        if "par2_scores" in metrics:
            html += '<div class="card">\n<h3>PAR-2 Scores</h3>\n'
            html += '<p><em>Penalized Average Runtime with factor 2. Lower is better. '
            html += 'Unsolved instances penalized as 2× timeout.</em></p>\n'
            html += '<table><tr><th>Solver</th><th>PAR-2</th></tr>\n'
            for s, v in sorted(metrics["par2_scores"].items(), key=lambda x: x[1]):
                html += f'<tr><td>{s}</td><td>{v:.2f}</td></tr>\n'
            html += '</table></div>\n'
        
        # PAR-10
        if "par10_scores" in metrics:
            html += '<div class="card">\n<h3>PAR-10 Scores</h3>\n'
            html += '<table><tr><th>Solver</th><th>PAR-10</th></tr>\n'
            for s, v in sorted(metrics["par10_scores"].items(), key=lambda x: x[1]):
                html += f'<tr><td>{s}</td><td>{v:.2f}</td></tr>\n'
            html += '</table></div>\n'
        
        # Solve Matrix
        if "solve_matrix" in metrics:
            sm = metrics["solve_matrix"]
            html += '<div class="card">\n<h3>Solve Matrix</h3>\n'
            if "solver_totals" in sm:
                html += '<table><tr><th>Solver</th><th>Total Solved</th></tr>\n'
                for s, v in sm["solver_totals"].items():
                    html += f'<tr><td>{s}</td><td>{v}</td></tr>\n'
                html += '</table>\n'
            
            if "uniquely_solved" in sm:
                html += '<h4>Uniquely Solved Instances</h4>\n'
                html += '<table><tr><th>Solver</th><th>Unique Count</th></tr>\n'
                for s, v in sm["uniquely_solved"].items():
                    html += f'<tr><td>{s}</td><td>{len(v) if isinstance(v, list) else v}</td></tr>\n'
                html += '</table>\n'
            
            html += '</div>\n'
        
        # VBS
        if "vbs" in metrics:
            vbs = metrics["vbs"]
            html += '<div class="card">\n<h3>Virtual Best Solver (VBS)</h3>\n'
            html += '<p><em>The VBS selects the best solver for each instance. '
            html += 'Gap to VBS indicates potential for portfolio approaches.</em></p>\n'
            if isinstance(vbs, dict):
                html += '<table><tr><th>Metric</th><th>Value</th></tr>\n'
                for k, v in vbs.items():
                    if isinstance(v, (int, float)):
                        html += f'<tr><td>{k}</td><td>{v:.4f}</td></tr>\n'
                html += '</table>\n'
            html += '</div>\n'
        
        # Ranking
        if "ranking" in metrics:
            html += '<div class="card">\n<h3>Overall Ranking</h3>\n'
            html += '<table><tr><th>Rank</th><th>Solver</th><th>Score</th></tr>\n'
            for i, entry in enumerate(metrics["ranking"]):
                if isinstance(entry, dict):
                    html += f'<tr><td>{i+1}</td><td>{entry.get("solver", "?")}</td>'
                    html += f'<td>{entry.get("composite_score", entry.get("avg_rank", "?"))}</td></tr>\n'
                elif isinstance(entry, (list, tuple)):
                    html += f'<tr><td>{i+1}</td><td>{entry[0]}</td><td>{entry[1]:.3f}</td></tr>\n'
            html += '</table></div>\n'
        
        return html
    
    def _section_plots(self, plots: Dict[str, str]) -> str:
        html = '<h2>📊 Visualizations</h2>\n'
        
        plot_descriptions = {
            "cactus": ("Cactus Plot", "Shows number of instances solved within a given time. "
                       "Curves further right and lower indicate better performance."),
            "ecdf": ("Empirical CDF", "Fraction of instances solved within a given time limit."),
            "boxplot": ("Runtime Distribution", "Box plots showing median, quartiles and outliers."),
            "performance_profile": ("Performance Profile", 
                                     "Dolan & Moré (2002). Shows P(ratio ≤ τ). "
                                     "Higher curves are better. ρ(1) = fraction of instances where solver is fastest."),
            "survival": ("Survival Plot", "Fraction of instances remaining unsolved over time."),
            "par2_bar": ("PAR-2 Scores", "Penalized Average Runtime scores. Lower is better."),
            "heatmap": ("Performance Heatmap", "Performance by solver and benchmark family."),
            "critical_difference": ("Critical Difference Diagram",
                                     "Demšar (2006). Solvers connected by a bar are NOT significantly different."),
        }
        
        for key, img_data in plots.items():
            desc_title = key.replace("_", " ").title()
            desc_text = ""
            
            # Check for known plot types
            for pattern, (title, text) in plot_descriptions.items():
                if key.startswith(pattern) or key == pattern:
                    desc_title = title
                    desc_text = text
                    break
            
            if key.startswith("scatter_"):
                parts = key.replace("scatter_", "").split("_vs_")
                if len(parts) == 2:
                    desc_title = f"Scatter: {parts[0]} vs {parts[1]}"
                    desc_text = "Points below diagonal: second solver is faster."
            
            html += f"""<div class="card">
    <div class="plot-container">
        <div class="plot-title">{desc_title}</div>
        {f'<p style="color: var(--text-muted); font-size: 0.9rem;">{desc_text}</p>' if desc_text else ''}
        <img src="{img_data}" alt="{desc_title}">
    </div>
</div>\n"""
        
        return html
    
    def _section_statistical_tests(self, tests: Dict) -> str:
        html = '<h2>🧪 Statistical Tests</h2>\n'
        
        # Friedman
        if "friedman" in tests:
            f = tests["friedman"]
            html += '<div class="card">\n<h3>Friedman Test</h3>\n'
            html += '<p><em>Non-parametric ANOVA for comparing k ≥ 3 solvers. '
            html += 'H0: All solvers have equal performance.</em></p>\n'
            html += '<table>\n'
            html += f'<tr><th>Statistic (χ²)</th><td>{f.get("statistic", "N/A")}</td></tr>\n'
            html += f'<tr><th>p-value</th><td>{f.get("p_value", "N/A")}</td></tr>\n'
            
            sig = f.get("significant_005", False)
            badge = "badge-success" if sig else "badge-warning"
            text = "Significant (p < 0.05)" if sig else "Not significant"
            html += f'<tr><th>Result</th><td><span class="badge {badge}">{text}</span></td></tr>\n'
            
            if "effect_size" in f:
                html += f'<tr><th>Kendall\'s W (effect)</th><td>{f["effect_size"]} ({f.get("effect_interpretation", "")})</td></tr>\n'
            html += '</table></div>\n'
        
        # Nemenyi
        if "nemenyi" in tests:
            n = tests["nemenyi"]
            html += '<div class="card">\n<h3>Nemenyi Post-Hoc Test</h3>\n'
            html += '<p><em>Pairwise comparisons after significant Friedman test. '
            html += f'Critical difference (CD) = {n.get("critical_difference", "?")}.</em></p>\n'
            
            if "comparisons" in n:
                html += '<table>\n<tr><th>Pair</th><th>Rank Diff</th><th>CD</th><th>Significant?</th><th>Better</th></tr>\n'
                for c in n["comparisons"]:
                    sig = c.get("significant", False)
                    badge = "badge-success" if sig else "badge-info"
                    text = "Yes" if sig else "No"
                    html += f'<tr><td>{c["solver1"]} vs {c["solver2"]}</td>'
                    html += f'<td>{c["rank_difference"]:.3f}</td>'
                    html += f'<td>{c["critical_difference"]:.3f}</td>'
                    html += f'<td><span class="badge {badge}">{text}</span></td>'
                    html += f'<td>{c.get("better_solver", "")}</td></tr>\n'
                html += '</table>\n'
            html += '</div>\n'
        
        # Pairwise tests
        if "pairwise" in tests:
            for pair_key, pair_data in tests["pairwise"].items():
                html += f'<div class="card">\n<h3>{pair_key}</h3>\n'
                
                if "wilcoxon" in pair_data:
                    w = pair_data["wilcoxon"]
                    html += f'<p><strong>Wilcoxon:</strong> stat={w.get("statistic", "N/A")}, '
                    html += f'p={w.get("p_value", "N/A")}</p>\n'
                
                if "vargha_delaney" in pair_data:
                    vd = pair_data["vargha_delaney"]
                    html += f'<p><strong>Vargha-Delaney A:</strong> {vd.get("A_measure", "N/A")} '
                    html += f'({vd.get("interpretation", "")} effect, {vd.get("direction", "")})</p>\n'
                
                if "interpretation" in pair_data:
                    interp = pair_data["interpretation"]
                    html += f'<div class="interpretation">{interp.get("summary", "")}</div>\n'
                
                html += '</div>\n'
        
        # Multiple corrections
        if "multiple_corrections" in tests:
            mc = tests["multiple_corrections"]
            html += '<div class="card">\n<h3>Multiple Comparison Corrections</h3>\n'
            html += '<p><em>Adjusted p-values to control for multiple testing.</em></p>\n'
            
            labels = mc.get("labels", [])
            html += '<table>\n<tr><th>Pair</th><th>Original p</th>'
            html += '<th>Bonferroni</th><th>Holm</th><th>Benjamini-Hochberg</th></tr>\n'
            
            for i, label in enumerate(labels):
                orig_p = mc.get("bonferroni", {}).get("original_pvalues", [0])[i] if i < len(mc.get("bonferroni", {}).get("original_pvalues", [])) else "?"
                bonf = mc.get("bonferroni", {}).get("adjusted_pvalues", [0])[i] if i < len(mc.get("bonferroni", {}).get("adjusted_pvalues", [])) else "?"
                holm = mc.get("holm", {}).get("adjusted_pvalues", [0])[i] if i < len(mc.get("holm", {}).get("adjusted_pvalues", [])) else "?"
                bh = mc.get("benjamini_hochberg", {}).get("adjusted_pvalues", [0])[i] if i < len(mc.get("benjamini_hochberg", {}).get("adjusted_pvalues", [])) else "?"
                
                html += f'<tr><td>{label}</td><td>{orig_p}</td><td>{bonf}</td><td>{holm}</td><td>{bh}</td></tr>\n'
            
            html += '</table></div>\n'
        
        return html
    
    def _section_bootstrap(self, bootstrap: Dict) -> str:
        html = '<h2>🔄 Bootstrap Confidence Intervals</h2>\n'
        html += '<div class="card">\n'
        html += '<p><em>Non-parametric confidence intervals via BCa bootstrap (10,000 replications). '
        html += 'Intervals that do not contain 0 indicate significant differences.</em></p>\n'
        
        if isinstance(bootstrap, dict):
            for solver, data in bootstrap.items():
                if isinstance(data, dict):
                    html += f'<h3>{solver}</h3>\n<table>\n'
                    html += '<tr><th>Metric</th><th>Point Estimate</th><th>95% CI</th></tr>\n'
                    
                    for metric, values in data.items():
                        if isinstance(values, dict) and "point_estimate" in values:
                            pe = values["point_estimate"]
                            ci = values.get("ci_95", values.get("ci", [None, None]))
                            if isinstance(ci, (list, tuple)) and len(ci) == 2:
                                html += f'<tr><td>{metric}</td><td>{pe:.4f}</td>'
                                html += f'<td>[{ci[0]:.4f}, {ci[1]:.4f}]</td></tr>\n'
                    
                    html += '</table>\n'
        
        html += '</div>\n'
        return html
    
    def _section_methodology(self) -> str:
        return """<h2>📚 Methodology</h2>
<div class="card">
    <h3>Statistical Framework</h3>
    <p>This analysis follows the recommendations of:</p>
    <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
        <li><strong>Demšar (2006)</strong>: "Statistical Comparisons of Classifiers over Multiple Data Sets", JMLR.
            <br>→ Friedman test + Nemenyi post-hoc for k≥3 solvers.</li>
        <li><strong>Arcuri & Briand (2011)</strong>: "A Practical Guide for Using Statistical Tests to Assess Randomized Algorithms in Software Engineering", ICSE.
            <br>→ Vargha-Delaney A measure for effect size.</li>
        <li><strong>García et al. (2010)</strong>: "Advanced nonparametric tests for multiple comparisons in the design of experiments", Information Sciences.
            <br>→ Multiple comparison correction methods.</li>
    </ul>
    
    <h3>Metrics</h3>
    <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
        <li><strong>PAR-k</strong>: Penalized Average Runtime. Unsolved instances penalized as k × timeout.</li>
        <li><strong>VBS</strong>: Virtual Best Solver. Oracle that picks the best solver per instance.</li>
        <li><strong>Bootstrap CI</strong>: BCa (Bias-Corrected and Accelerated) method, 10,000 replications.</li>
    </ul>
    
    <h3>Multiple Comparison Corrections</h3>
    <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
        <li><strong>Bonferroni</strong>: p_adj = p × m. Most conservative.</li>
        <li><strong>Holm</strong>: Step-down Bonferroni. Controls FWER, more powerful.</li>
        <li><strong>Benjamini-Hochberg</strong>: Controls FDR. Least conservative, recommended when many comparisons.</li>
    </ul>
</div>
"""
