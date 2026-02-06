import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Microscope, BarChart3, FlaskConical, TrendingUp, FileDown, ExternalLink, Loader2, AlertCircle, CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { experimentsApi, rigorousApi } from '../services/api';
import clsx from 'clsx';

// Tab types
type Tab = 'overview' | 'tests' | 'bootstrap' | 'plots' | 'report';

export default function RigorousAnalysis() {
  const [selectedExperiment, setSelectedExperiment] = useState<number | null>(null);
  const [timeout, setTimeout] = useState(300);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['summary']));

  // Fetch experiments
  const { data: experiments } = useQuery({
    queryKey: ['experiments'],
    queryFn: experimentsApi.getAll,
  });

  // Auto-select first completed experiment
  useEffect(() => {
    if (experiments && !selectedExperiment) {
      const completed = experiments.filter((e: any) => e.status === 'completed');
      if (completed.length > 0) {
        setSelectedExperiment(completed[0].id);
      }
    }
  }, [experiments, selectedExperiment]);

  // Full analysis query
  const { data: analysis, isLoading: analysisLoading, error: analysisError } = useQuery({
    queryKey: ['rigorous-analysis', selectedExperiment, timeout],
    queryFn: () => rigorousApi.getFullAnalysis(selectedExperiment!, timeout),
    enabled: !!selectedExperiment,
  });

  // Plots query (separate because it's heavy)
  const { data: plotsData, isLoading: plotsLoading } = useQuery({
    queryKey: ['rigorous-plots', selectedExperiment, timeout],
    queryFn: () => rigorousApi.getPlots(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && activeTab === 'plots',
  });

  const toggleSection = (id: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const tabs = [
    { id: 'overview' as Tab, label: 'Resumen', icon: BarChart3 },
    { id: 'tests' as Tab, label: 'Tests Estadísticos', icon: FlaskConical },
    { id: 'bootstrap' as Tab, label: 'Bootstrap CIs', icon: TrendingUp },
    { id: 'plots' as Tab, label: 'Gráficos', icon: Microscope },
    { id: 'report' as Tab, label: 'Informe', icon: FileDown },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <div className="p-2 bg-primary-600/20 rounded-xl">
              <Microscope className="w-8 h-8 text-primary-400" />
            </div>
            Análisis Riguroso
          </h1>
          <p className="mt-2 text-gray-400">
            Pipeline estadístico completo: Friedman, Nemenyi, Bootstrap, múltiples correcciones
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-300 mb-1">Experimento</label>
            <select
              value={selectedExperiment ?? ''}
              onChange={(e) => setSelectedExperiment(Number(e.target.value))}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">Seleccionar experimento...</option>
              {experiments?.filter((e: any) => e.status === 'completed').map((exp: any) => (
                <option key={exp.id} value={exp.id}>
                  {exp.name} (ID: {exp.id})
                </option>
              ))}
            </select>
          </div>
          <div className="w-32">
            <label className="block text-sm font-medium text-gray-300 mb-1">Timeout (s)</label>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout(Number(e.target.value))}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-primary-500"
            />
          </div>
          {selectedExperiment && (
            <a
              href={rigorousApi.getReportUrl(selectedExperiment, timeout)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Abrir Informe HTML
            </a>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-dark-700">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "flex items-center gap-2 px-4 py-3 font-medium text-sm rounded-t-lg transition-all",
                activeTab === tab.id
                  ? "bg-dark-800 text-primary-400 border-b-2 border-primary-400"
                  : "text-gray-400 hover:text-gray-200 hover:bg-dark-800/50"
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      {!selectedExperiment ? (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-12 text-center">
          <Microscope className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg">Selecciona un experimento completado para iniciar el análisis</p>
        </div>
      ) : analysisLoading ? (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-12 text-center">
          <Loader2 className="w-12 h-12 text-primary-400 mx-auto mb-4 animate-spin" />
          <p className="text-gray-400">Ejecutando pipeline de análisis...</p>
          <p className="text-gray-500 text-sm mt-2">Métricas + Tests + Bootstrap</p>
        </div>
      ) : analysisError ? (
        <div className="bg-dark-800 rounded-xl border border-red-700/50 p-8">
          <AlertCircle className="w-8 h-8 text-red-400 mb-2" />
          <p className="text-red-400">Error: {(analysisError as any)?.message || 'Failed to load analysis'}</p>
        </div>
      ) : (
        <>
          {activeTab === 'overview' && analysis && <OverviewTab data={analysis} expandedSections={expandedSections} toggleSection={toggleSection} />}
          {activeTab === 'tests' && analysis && <StatisticalTestsTab data={analysis.statistical_tests} />}
          {activeTab === 'bootstrap' && analysis && <BootstrapTab data={analysis.bootstrap} />}
          {activeTab === 'plots' && <PlotsTab data={plotsData} loading={plotsLoading} />}
          {activeTab === 'report' && selectedExperiment && <ReportTab experimentId={selectedExperiment} timeout={timeout} />}
        </>
      )}
    </div>
  );
}

// ==================== OVERVIEW TAB ====================

function OverviewTab({ data, expandedSections, toggleSection }: { data: any; expandedSections: Set<string>; toggleSection: (id: string) => void }) {
  const metrics = data.metrics;
  if (!metrics) return <p className="text-gray-400">No metrics available</p>;

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Solvers" value={data.n_solvers} />
        <MetricCard label="Benchmarks" value={data.n_benchmarks} />
        <MetricCard label="Timeout" value={`${data.timeout}s`} />
        <MetricCard label="Best Solver" value={metrics.ranking?.[0]?.solver || metrics.ranking?.[0]?.[0] || '?'} highlight />
      </div>

      {/* PAR-2 Scores */}
      <CollapsibleSection 
        id="par2" title="PAR-2 Scores" 
        expanded={expandedSections.has('par2')} toggle={toggleSection}
        subtitle="Penalized Average Runtime (factor 2). Menor = mejor."
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {metrics.par2_scores && Object.entries(metrics.par2_scores)
            .sort(([,a]: any, [,b]: any) => a - b)
            .map(([solver, score]: any, idx: number) => (
              <div key={solver} className={clsx(
                "p-4 rounded-lg border",
                idx === 0 ? "bg-emerald-900/20 border-emerald-700/50" : "bg-dark-700/50 border-dark-600"
              )}>
                <div className="text-2xl font-bold text-white">{score.toFixed(2)}</div>
                <div className="text-sm text-gray-400">{solver}</div>
                {idx === 0 && <span className="text-xs text-emerald-400 font-semibold">⭐ Best</span>}
              </div>
            ))}
        </div>
      </CollapsibleSection>

      {/* Solve Matrix */}
      <CollapsibleSection
        id="solve" title="Solve Matrix"
        expanded={expandedSections.has('solve')} toggle={toggleSection}
        subtitle="Instancias resueltas por solver"
      >
        {metrics.solve_matrix?.solver_totals && (
          <table className="w-full">
            <thead>
              <tr>
                <th className="text-left text-gray-300 pb-2 border-b border-dark-600">Solver</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Resueltas</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Únicas</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(metrics.solve_matrix.solver_totals).map(([solver, total]: any) => (
                <tr key={solver} className="border-b border-dark-700/50">
                  <td className="py-2 text-white font-medium">{solver}</td>
                  <td className="py-2 text-right text-gray-300">{total}</td>
                  <td className="py-2 text-right text-gray-400">
                    {typeof metrics.solve_matrix.uniquely_solved?.[solver] === 'number' 
                      ? metrics.solve_matrix.uniquely_solved[solver]
                      : metrics.solve_matrix.uniquely_solved?.[solver]?.length ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CollapsibleSection>

      {/* Ranking */}
      <CollapsibleSection
        id="ranking" title="Ranking Compuesto"
        expanded={expandedSections.has('ranking')} toggle={toggleSection}
        subtitle="Basado en PAR-2, tasa de resolución y rango promedio"
      >
        <div className="space-y-2">
          {metrics.ranking?.map((entry: any, idx: number) => {
            const solver = entry.solver || entry[0];
            const par2 = entry.par2;
            const solved = entry.solved;
            const solveRate = entry.solve_rate;
            return (
              <div key={solver} className="flex items-center gap-4 p-3 bg-dark-700/50 rounded-lg">
                <div className={clsx(
                  "w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm",
                  idx === 0 ? "bg-yellow-500 text-black" : idx === 1 ? "bg-gray-300 text-black" : idx === 2 ? "bg-amber-600 text-white" : "bg-dark-600 text-gray-300"
                )}>
                  {entry.rank || idx + 1}
                </div>
                <div className="flex-1">
                  <span className="text-white font-medium">{solver}</span>
                  {solved != null && <span className="text-gray-400 text-sm ml-2">({solved} solved)</span>}
                </div>
                <div className="flex gap-4 text-sm">
                  {par2 != null && <span className="text-gray-300">PAR-2: <strong className="text-white">{par2.toFixed(2)}</strong></span>}
                  {solveRate != null && <span className="text-gray-400">{solveRate}%</span>}
                </div>
              </div>
            );
          })}
        </div>
      </CollapsibleSection>
    </div>
  );
}

// ==================== STATISTICAL TESTS TAB ====================

function StatisticalTestsTab({ data }: { data: any }) {
  if (!data) return <p className="text-gray-400">No statistical test data</p>;

  return (
    <div className="space-y-4">
      {/* Friedman Test (multi-solver) */}
      {data.friedman && (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-primary-400" />
            Friedman Test
          </h3>
          <p className="text-sm text-gray-400 mb-4">
            ANOVA no paramétrico para k ≥ 3 solvers. H0: todos los solvers tienen el mismo rendimiento.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <StatCard label="χ² Statistic" value={data.friedman.statistic?.toFixed(4)} />
            <StatCard label="p-value" value={data.friedman.p_value?.toFixed(6)} />
            <StatCard 
              label="Significativo (α=0.05)" 
              value={data.friedman.significant_005 ? "✅ Sí" : "❌ No"} 
            />
            {data.friedman.effect_size != null && (
              <StatCard label="Kendall's W" value={`${data.friedman.effect_size?.toFixed(4)} (${data.friedman.effect_interpretation})`} />
            )}
          </div>
          {data.friedman.significant_005 && (
            <div className="bg-emerald-900/20 border border-emerald-700/50 rounded-lg p-3 text-sm text-emerald-300">
              ✅ Diferencias significativas detectadas → ver post-hoc Nemenyi abajo
            </div>
          )}
        </div>
      )}

      {/* Nemenyi Post-Hoc */}
      {data.nemenyi && (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-3">Post-Hoc: Nemenyi Test</h3>
          <p className="text-sm text-gray-400 mb-2">
            CD = {data.nemenyi.critical_difference}. Pares con |R_i - R_j| {'>'} CD son significativamente diferentes.
          </p>

          {/* Average ranks */}
          <div className="flex gap-3 mb-4 flex-wrap">
            {data.nemenyi.ranking?.map(([solver, rank]: any, idx: number) => (
              <span key={solver} className={clsx(
                "px-3 py-1 rounded-full text-sm font-medium",
                idx === 0 ? "bg-emerald-900/30 text-emerald-300 border border-emerald-700/50" : "bg-dark-700 text-gray-300"
              )}>
                #{idx + 1} {solver}: {rank.toFixed(3)}
              </span>
            ))}
          </div>

          {/* Pairwise comparisons table */}
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left text-gray-300 pb-2 border-b border-dark-600">Par</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Δ Rangos</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">CD</th>
                <th className="text-center text-gray-300 pb-2 border-b border-dark-600">Significativo</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Mejor</th>
              </tr>
            </thead>
            <tbody>
              {data.nemenyi.comparisons?.map((c: any, i: number) => (
                <tr key={i} className="border-b border-dark-700/50">
                  <td className="py-2 text-white">{c.solver1} vs {c.solver2}</td>
                  <td className="py-2 text-right text-gray-300">{c.rank_difference?.toFixed(3)}</td>
                  <td className="py-2 text-right text-gray-400">{c.critical_difference?.toFixed(3)}</td>
                  <td className="py-2 text-center">
                    {c.significant ? (
                      <CheckCircle className="w-4 h-4 text-emerald-400 inline" />
                    ) : (
                      <XCircle className="w-4 h-4 text-gray-500 inline" />
                    )}
                  </td>
                  <td className="py-2 text-right text-emerald-400 font-medium">{c.better_solver}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Wilcoxon (2-solver) */}
      {data.wilcoxon && (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-3">Wilcoxon Signed-Rank Test</h3>
          <p className="text-sm text-gray-400 mb-4">{data.wilcoxon.description}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Statistic" value={data.wilcoxon.statistic?.toFixed(4)} />
            <StatCard label="p-value" value={data.wilcoxon.p_value?.toFixed(6)} />
            <StatCard label="Significativo" value={data.wilcoxon.significant_005 ? "✅ Sí" : "❌ No"} />
            {data.wilcoxon.effect_size != null && (
              <StatCard label="Effect Size (r)" value={`${data.wilcoxon.effect_size?.toFixed(4)} (${data.wilcoxon.effect_interpretation})`} />
            )}
          </div>
        </div>
      )}

      {/* Multiple corrections */}
      {data.multiple_corrections && (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-3">Correcciones por Comparaciones Múltiples</h3>
          <p className="text-sm text-gray-400 mb-4">
            p-values ajustados para controlar errores por pruebas múltiples.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left text-gray-300 pb-2 border-b border-dark-600">Par</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">p original</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Bonferroni</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Holm</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Benj.-Hoch.</th>
                </tr>
              </thead>
              <tbody>
                {data.multiple_corrections.labels?.map((label: string, i: number) => (
                  <tr key={i} className="border-b border-dark-700/50">
                    <td className="py-2 text-white">{label}</td>
                    <td className="py-2 text-right text-gray-300">
                      {data.multiple_corrections.bonferroni?.original_pvalues?.[i]?.toFixed(6)}
                    </td>
                    <td className={clsx("py-2 text-right", 
                      data.multiple_corrections.bonferroni?.significant_005?.[i] ? "text-emerald-400 font-medium" : "text-gray-400"
                    )}>
                      {data.multiple_corrections.bonferroni?.adjusted_pvalues?.[i]?.toFixed(6)}
                    </td>
                    <td className={clsx("py-2 text-right",
                      data.multiple_corrections.holm?.significant_005?.[i] ? "text-emerald-400 font-medium" : "text-gray-400"
                    )}>
                      {data.multiple_corrections.holm?.adjusted_pvalues?.[i]?.toFixed(6)}
                    </td>
                    <td className={clsx("py-2 text-right",
                      data.multiple_corrections.benjamini_hochberg?.significant_005?.[i] ? "text-emerald-400 font-medium" : "text-gray-400"
                    )}>
                      {data.multiple_corrections.benjamini_hochberg?.adjusted_pvalues?.[i]?.toFixed(6)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-gray-500">
            <div><strong>Bonferroni:</strong> más conservador (FWER)</div>
            <div><strong>Holm:</strong> step-down, más potente (FWER)</div>
            <div><strong>B-H:</strong> controla FDR, menos conservador</div>
          </div>
        </div>
      )}

      {/* Interpretation */}
      {data.interpretation && (
        <div className="bg-primary-900/20 border border-primary-700/50 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-primary-300 mb-2">Interpretación Automática</h3>
          <p className="text-gray-300">{data.interpretation.summary}</p>
        </div>
      )}
    </div>
  );
}

// ==================== BOOTSTRAP TAB ====================

function BootstrapTab({ data }: { data: any }) {
  if (!data) return <p className="text-gray-400">No bootstrap data</p>;

  // data may have structure: { bootstrap_results: {...}, confidence_level, n_bootstrap, method }
  const bootstrapResults = data.bootstrap_results || data;
  const confidenceLevel = data.confidence_level || 0.95;
  const nBootstrap = data.n_bootstrap || '?';

  // Separate solver results from pairwise differences
  const solverEntries = Object.entries(bootstrapResults).filter(
    ([key]) => key !== 'pairwise_differences'
  );
  const pairwiseDiffs = bootstrapResults.pairwise_differences;

  return (
    <div className="space-y-4">
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-2">Bootstrap Confidence Intervals</h3>
        <p className="text-sm text-gray-400 mb-4">
          Método BCa (Bias-Corrected and Accelerated), {nBootstrap} replicaciones, 
          nivel de confianza {(confidenceLevel * 100).toFixed(0)}%.
        </p>

        {/* Per-solver bootstrap results */}
        {solverEntries.map(([solver, results]: any) => (
          <div key={solver} className="mb-6">
            <h4 className="text-md font-semibold text-primary-300 mb-3">{solver}</h4>
            {results.error ? (
              <p className="text-red-400 text-sm">{results.error}</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {Object.entries(results).map(([metric, vals]: any) => {
                  if (!vals || typeof vals !== 'object') return null;
                  // Support both {statistic, ci_lower, ci_upper} and {point_estimate, ci_95}
                  const pointEst = vals.statistic ?? vals.point_estimate;
                  const ciLower = vals.ci_lower ?? (vals.ci_95 || vals.ci || [])[0];
                  const ciUpper = vals.ci_upper ?? (vals.ci_95 || vals.ci || [])[1];
                  if (pointEst == null) return null;
                  return (
                    <div key={metric} className="bg-dark-700/50 rounded-lg p-3 border border-dark-600">
                      <div className="text-xs text-gray-500 uppercase mb-1">{metric.replace(/_/g, ' ')}</div>
                      <div className="text-lg font-bold text-white">{pointEst?.toFixed(4)}</div>
                      {ciLower != null && ciUpper != null && (
                        <div className="text-sm text-gray-400">
                          CI: [{ciLower?.toFixed(4)}, {ciUpper?.toFixed(4)}]
                        </div>
                      )}
                      {vals.method && (
                        <div className="text-xs text-gray-500 mt-1">Method: {vals.method}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}

        {/* Pairwise differences */}
        {pairwiseDiffs && Object.keys(pairwiseDiffs).length > 0 && (
          <div className="mt-6">
            <h4 className="text-md font-semibold text-white mb-3">Pairwise Differences</h4>
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left text-gray-300 pb-2 border-b border-dark-600">Par</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Δ Mean</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">CI Lower</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">CI Upper</th>
                  <th className="text-center text-gray-300 pb-2 border-b border-dark-600">Significativo</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Más rápido</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(pairwiseDiffs).map(([pair, vals]: any) => (
                  <tr key={pair} className="border-b border-dark-700/50">
                    <td className="py-2 text-white">{pair.replace(/_/g, ' ')}</td>
                    <td className="py-2 text-right text-gray-300">{vals.statistic?.toFixed(4)}</td>
                    <td className="py-2 text-right text-gray-400">{vals.ci_lower?.toFixed(4)}</td>
                    <td className="py-2 text-right text-gray-400">{vals.ci_upper?.toFixed(4)}</td>
                    <td className="py-2 text-center">
                      {vals.significant ? (
                        <CheckCircle className="w-4 h-4 text-emerald-400 inline" />
                      ) : (
                        <XCircle className="w-4 h-4 text-gray-500 inline" />
                      )}
                    </td>
                    <td className="py-2 text-right text-emerald-400 font-medium">{vals.faster_solver || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ==================== PLOTS TAB ====================

function PlotsTab({ data, loading }: { data: any; loading: boolean }) {
  if (loading) {
    return (
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-12 text-center">
        <Loader2 className="w-12 h-12 text-primary-400 mx-auto mb-4 animate-spin" />
        <p className="text-gray-400">Generando gráficos publication-ready...</p>
      </div>
    );
  }

  // data is either {cactus: ..., ecdf: ...} directly from /plots endpoint
  // or might have a .plots wrapper
  const plots = data?.plots || data;
  if (!plots || Object.keys(plots).length === 0) return <p className="text-gray-400">No plots available</p>;

  const plotDescriptions: Record<string, string> = {
    cactus: 'Cactus Plot — Instancias resueltas vs tiempo. Curvas más a la derecha = mejor.',
    ecdf: 'ECDF — Fracción acumulada de instancias resueltas.',
    boxplot: 'Boxplot — Distribución de tiempos de ejecución.',
    performance_profile: 'Performance Profile (Dolan & Moré) — ρ(1) = fracción donde es el más rápido.',
    survival: 'Survival Plot — Fracción de instancias NO resueltas.',
    par2_bar: 'PAR-2 Scores — Menor = mejor.',
    heatmap: 'Heatmap — Rendimiento por solver y familia.',
    critical_difference: 'Critical Difference Diagram (Demšar) — Barras conectan solvers sin diferencia significativa.',
  };

  return (
    <div className="space-y-6">
      {Object.entries(plots).map(([name, imgData]: any) => {
        const desc = Object.entries(plotDescriptions).find(([k]) => name.startsWith(k))?.[1] 
          || name.replace(/_/g, ' ');
        return (
          <div key={name} className="bg-dark-800 rounded-xl border border-dark-700 p-4">
            <h3 className="text-md font-semibold text-white mb-1">{name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}</h3>
            <p className="text-sm text-gray-400 mb-3">{desc}</p>
            <div className="bg-white rounded-lg p-2">
              <img src={imgData} alt={name} className="w-full max-w-4xl mx-auto" />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ==================== REPORT TAB ====================

function ReportTab({ experimentId, timeout }: { experimentId: number; timeout: number }) {
  const reportUrl = rigorousApi.getReportUrl(experimentId, timeout);
  
  return (
    <div className="space-y-4">
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-3">Informe Completo</h3>
        <p className="text-gray-400 mb-4">
          El informe incluye métricas, gráficos embebidos, tests estadísticos, intervalos de confianza y metodología.
          Es un HTML auto-contenido que puede abrirse en cualquier navegador.
        </p>
        <div className="flex gap-3">
          <a
            href={reportUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors font-medium"
          >
            <ExternalLink className="w-5 h-5" />
            Abrir Informe HTML
          </a>
        </div>
      </div>
      
      {/* Preview iframe */}
      <div className="bg-dark-800 rounded-xl border border-dark-700 overflow-hidden">
        <div className="p-3 border-b border-dark-700 flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="ml-2 text-sm text-gray-400">Preview</span>
        </div>
        <iframe
          src={reportUrl}
          className="w-full h-[600px] bg-white"
          title="Report Preview"
        />
      </div>
    </div>
  );
}

// ==================== HELPER COMPONENTS ====================

function MetricCard({ label, value, highlight }: { label: string; value: any; highlight?: boolean }) {
  return (
    <div className={clsx(
      "p-4 rounded-xl border",
      highlight ? "bg-primary-900/20 border-primary-700/50" : "bg-dark-800 border-dark-700"
    )}>
      <div className={clsx("text-2xl font-bold", highlight ? "text-primary-400" : "text-white")}>{value}</div>
      <div className="text-sm text-gray-400">{label}</div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: any }) {
  return (
    <div className="bg-dark-700/50 rounded-lg p-3 border border-dark-600">
      <div className="text-xs text-gray-500 uppercase mb-1">{label}</div>
      <div className="text-sm font-semibold text-white">{value}</div>
    </div>
  );
}

function CollapsibleSection({ id, title, subtitle, expanded, toggle, children }: { 
  id: string; title: string; subtitle?: string; expanded: boolean; toggle: (id: string) => void; children: React.ReactNode;
}) {
  return (
    <div className="bg-dark-800 rounded-xl border border-dark-700">
      <button
        onClick={() => toggle(id)}
        className="w-full flex items-center justify-between p-4 hover:bg-dark-700/50 transition-colors rounded-xl"
      >
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
      </button>
      {expanded && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}
