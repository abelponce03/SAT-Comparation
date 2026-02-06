import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  Trophy,
  Scale,
  Table2,
  FlaskConical,
  TrendingUp,
  Microscope,
  FileDown,
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  Download,
  Activity,
  Ruler,
} from 'lucide-react';
import { analysisApi, experimentsApi, rigorousApi } from '@/services/api';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import Badge from '@/components/common/Badge';
import EmptyState from '@/components/common/EmptyState';
import clsx from 'clsx';

type AnalysisTab = 'par2' | 'vbs' | 'pairwise' | 'families' | 'normality' | 'tests' | 'effects' | 'bootstrap' | 'plots' | 'report';

// ==================== CSV DOWNLOAD HELPER ====================

function CsvButton({ experimentId, tableName, timeout, label }: {
  experimentId: number; tableName: string; timeout: number; label?: string;
}) {
  const url = rigorousApi.getCsvUrl(experimentId, tableName, timeout);
  return (
    <a
      href={url}
      download
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg border border-dark-600 transition-colors"
      title={`Descargar ${tableName} como CSV`}
    >
      <Download className="w-3.5 h-3.5" />
      {label || 'CSV'}
    </a>
  );
}

// ==================== MAIN COMPONENT ====================

export default function Analysis() {
  const [selectedExperiment, setSelectedExperiment] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<AnalysisTab>('par2');
  const [timeout, setTimeout] = useState(5000);

  // Queries — existing basic analysis
  const { data: experiments } = useQuery({
    queryKey: ['experiments', 'completed'],
    queryFn: () => experimentsApi.getAll('completed'),
  });

  const { data: par2Data, isLoading: par2Loading } = useQuery({
    queryKey: ['analysis', 'par2', selectedExperiment, timeout],
    queryFn: () => analysisApi.getPAR2(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && activeTab === 'par2',
  });

  const { data: vbsData, isLoading: vbsLoading } = useQuery({
    queryKey: ['analysis', 'vbs', selectedExperiment, timeout],
    queryFn: () => analysisApi.getVBS(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && activeTab === 'vbs',
  });

  const { data: pairwiseData, isLoading: pairwiseLoading } = useQuery({
    queryKey: ['analysis', 'pairwise', selectedExperiment],
    queryFn: () => analysisApi.getPairwise(selectedExperiment!),
    enabled: !!selectedExperiment && activeTab === 'pairwise',
  });

  const { data: familyData, isLoading: familyLoading } = useQuery({
    queryKey: ['analysis', 'family', selectedExperiment],
    queryFn: () => analysisApi.getByFamily(selectedExperiment!),
    enabled: !!selectedExperiment && activeTab === 'families',
  });

  // Queries — rigorous analysis pipeline
  const { data: fullAnalysis, isLoading: analysisLoading, error: analysisError } = useQuery({
    queryKey: ['rigorous-analysis', selectedExperiment, timeout],
    queryFn: () => rigorousApi.getFullAnalysis(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && ['tests', 'bootstrap'].includes(activeTab),
  });

  const { data: normalityData, isLoading: normalityLoading } = useQuery({
    queryKey: ['rigorous-normality', selectedExperiment, timeout],
    queryFn: () => rigorousApi.getNormality(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && activeTab === 'normality',
  });

  const { data: effectData, isLoading: effectLoading } = useQuery({
    queryKey: ['rigorous-effects', selectedExperiment, timeout],
    queryFn: () => rigorousApi.getEffectSizes(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && activeTab === 'effects',
  });

  const { data: plotsData, isLoading: plotsLoading } = useQuery({
    queryKey: ['rigorous-plots', selectedExperiment, timeout],
    queryFn: () => rigorousApi.getPlots(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && activeTab === 'plots',
  });

  const tabs = [
    { id: 'par2' as const, label: 'PAR-2', icon: BarChart3 },
    { id: 'vbs' as const, label: 'VBS', icon: Trophy },
    { id: 'pairwise' as const, label: 'Pares', icon: Scale },
    { id: 'families' as const, label: 'Familias', icon: Table2 },
    { id: 'normality' as const, label: 'Normalidad', icon: Activity },
    { id: 'tests' as const, label: 'Tests', icon: FlaskConical },
    { id: 'effects' as const, label: 'Efecto', icon: Ruler },
    { id: 'bootstrap' as const, label: 'Bootstrap', icon: TrendingUp },
    { id: 'plots' as const, label: 'Gráficos', icon: Microscope },
    { id: 'report' as const, label: 'Informe', icon: FileDown },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Análisis Estadístico</h1>
          <p className="text-gray-400 mt-1">
            PAR-2, VBS, normalidad, Friedman, Nemenyi, correcciones múltiples, Bootstrap, gráficos e informe
          </p>
        </div>
        {selectedExperiment && (
          <a
            href={rigorousApi.getReportUrl(selectedExperiment, timeout)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors text-sm"
          >
            <ExternalLink className="w-4 h-4" />
            Informe HTML
          </a>
        )}
      </div>

      {/* Experiment Selector */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label className="label">Experimento</label>
              <select
                value={selectedExperiment || ''}
                onChange={(e) => setSelectedExperiment(parseInt(e.target.value) || null)}
                className="input"
              >
                <option value="">Selecciona un experimento</option>
                {experiments?.map((exp: any) => (
                  <option key={exp.id} value={exp.id}>
                    {exp.name} ({exp.completed_runs || exp.total_runs || '?'} ejecuciones)
                  </option>
                ))}
              </select>
            </div>
            <div className="w-40">
              <label className="label">Timeout (s)</label>
              <input
                type="number"
                value={timeout}
                onChange={(e) => setTimeout(parseInt(e.target.value))}
                className="input"
                min={1}
              />
            </div>
          </div>
        </div>
      </div>

      {!selectedExperiment ? (
        <EmptyState
          title="Selecciona un experimento"
          description="Elige un experimento completado para ver el análisis estadístico completo"
          icon={<BarChart3 className="w-6 h-6 text-gray-400" />}
        />
      ) : (
        <>
          {/* Tabs */}
          <div className="border-b border-dark-700 overflow-x-auto">
            <nav className="flex gap-1 min-w-max">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={clsx(
                    "flex items-center gap-2 px-3 py-3 font-medium text-sm rounded-t-lg transition-all whitespace-nowrap",
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

          {/* Tab Content */}
          <div className="mt-4">
            {activeTab === 'par2' && (
              <PAR2Tab data={par2Data} isLoading={par2Loading} timeout={timeout} experimentId={selectedExperiment} />
            )}
            {activeTab === 'vbs' && (
              <VBSTab data={vbsData} isLoading={vbsLoading} />
            )}
            {activeTab === 'pairwise' && (
              <PairwiseTab data={pairwiseData} isLoading={pairwiseLoading} />
            )}
            {activeTab === 'families' && (
              <FamilyTab data={familyData} isLoading={familyLoading} />
            )}
            {activeTab === 'normality' && (
              <NormalityTab data={normalityData} isLoading={normalityLoading} experimentId={selectedExperiment} timeout={timeout} />
            )}
            {activeTab === 'tests' && (
              <StatisticalTestsTab data={fullAnalysis?.statistical_tests} isLoading={analysisLoading} error={analysisError} experimentId={selectedExperiment} timeout={timeout} />
            )}
            {activeTab === 'effects' && (
              <EffectSizesTab data={effectData} isLoading={effectLoading} experimentId={selectedExperiment} timeout={timeout} />
            )}
            {activeTab === 'bootstrap' && (
              <BootstrapTab data={fullAnalysis?.bootstrap} isLoading={analysisLoading} error={analysisError} experimentId={selectedExperiment} timeout={timeout} />
            )}
            {activeTab === 'plots' && (
              <PlotsTab data={plotsData} loading={plotsLoading} />
            )}
            {activeTab === 'report' && (
              <ReportTab experimentId={selectedExperiment} timeout={timeout} />
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ==================== PAR-2 TAB ====================

function PAR2Tab({ data, isLoading, timeout, experimentId }: {
  data: any; isLoading: boolean; timeout: number; experimentId: number;
}) {
  if (isLoading) return <LoadingSpinner text="Calculando PAR-2..." />;
  if (!data) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <div>
            <h3 className="card-title">PAR-2 Score Ranking</h3>
            <p className="text-sm text-gray-400">
              Penalized Average Runtime con factor 2×timeout para instancias no resueltas
            </p>
          </div>
          <CsvButton experimentId={experimentId} tableName="par2_scores" timeout={timeout} />
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Solver</th>
                <th>PAR-2 Score</th>
                <th>Resueltos</th>
                <th>Timeout</th>
                <th>Tiempo promedio</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-700">
              {data.rankings?.map((row: any, index: number) => (
                <tr key={row.solver_name} className={index === 0 ? 'bg-emerald-900/20' : ''}>
                  <td>
                    {index === 0 && <Trophy className="w-5 h-5 text-yellow-500 inline mr-1" />}
                    #{index + 1}
                  </td>
                  <td className="font-medium text-white">{row.solver_name}</td>
                  <td className="font-mono text-gray-300">{row.par2_score.toFixed(2)}</td>
                  <td>
                    <span className="text-emerald-400 font-medium">{row.solved}</span>
                    <span className="text-gray-500">/{row.total}</span>
                  </td>
                  <td className="text-yellow-500">{row.timeouts}</td>
                  <td className="font-mono text-sm text-gray-300">{row.avg_time.toFixed(3)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <InfoBox color="blue" title="Sobre PAR-2">
        PAR-2 (Penalized Average Runtime) asigna 2×timeout ({2 * timeout}s) a las instancias
        no resueltas. Un score menor indica mejor rendimiento.
      </InfoBox>
    </div>
  );
}

// ==================== VBS TAB ====================

function VBSTab({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) return <LoadingSpinner text="Calculando VBS..." />;
  if (!data) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <TopMetricCard label="Mejor Solver" value={data.best_single_solver} icon={<Trophy className="w-10 h-10 text-yellow-500" />} sub={`Resuelve ${data.best_single_solved} instancias`} />
        <TopMetricCard label="Virtual Best Solver" value={data.vbs_solved} icon={<Scale className="w-10 h-10 text-purple-500" />} sub="instancias resueltas" />
        <TopMetricCard label="Ventaja VBS" value={`+${data.vbs_solved - data.best_single_solved}`} icon={<BarChart3 className="w-10 h-10 text-emerald-500" />} sub="instancias adicionales" />
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Contribución al VBS</h3>
        </div>
        <div className="card-body">
          <div className="space-y-3">
            {data.contributions?.map((contrib: any) => (
              <div key={contrib.solver} className="flex items-center gap-4">
                <span className="w-32 font-medium text-white">{contrib.solver}</span>
                <div className="flex-1 h-6 bg-dark-600 rounded-full overflow-hidden">
                  <div className="h-full bg-primary-500 rounded-full" style={{ width: `${contrib.percentage}%` }} />
                </div>
                <span className="w-24 text-right text-sm text-gray-400">
                  {contrib.unique_wins} ({contrib.percentage.toFixed(1)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <InfoBox color="purple" title="Sobre VBS">
        El Virtual Best Solver (VBS) representa el rendimiento teórico óptimo si pudiéramos
        elegir el mejor solver para cada instancia individual.
      </InfoBox>
    </div>
  );
}

// ==================== PAIRWISE TAB ====================

function PairwiseTab({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) return <LoadingSpinner text="Calculando comparaciones..." />;
  if (!data || !data.matrix) return null;

  const solvers = data.solvers || [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Matriz de Comparación</h3>
          <p className="text-sm text-gray-400">
            Celda (i,j): veces que solver i es más rápido que solver j
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr>
                <th className="bg-dark-700"></th>
                {solvers.map((s: string) => (
                  <th key={s} className="bg-dark-700 text-center px-4 text-white">{s}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {solvers.map((s1: string, i: number) => (
                <tr key={s1}>
                  <td className="font-medium bg-dark-800 px-4 text-white">{s1}</td>
                  {solvers.map((s2: string, j: number) => {
                    const value = data.matrix[i]?.[j] || 0;
                    const reverseValue = data.matrix[j]?.[i] || 0;
                    const isWinner = value > reverseValue;
                    const isTie = value === reverseValue;
                    return (
                      <td key={s2} className={clsx("text-center px-4 py-2",
                        i === j ? 'bg-dark-700 text-gray-500' :
                        isWinner ? 'bg-emerald-900/20 text-emerald-400 font-medium' :
                        isTie ? 'bg-dark-800 text-gray-400' :
                        'bg-red-900/20 text-red-400'
                      )}>
                        {i === j ? '-' : value}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Resumen de Victorias</h3>
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Solver</th>
                <th>Victorias</th>
                <th>Derrotas</th>
                <th>Ratio</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-700">
              {data.summary?.map((row: any) => (
                <tr key={row.solver}>
                  <td className="font-medium text-white">{row.solver}</td>
                  <td className="text-emerald-400">{row.wins}</td>
                  <td className="text-red-400">{row.losses}</td>
                  <td className="font-mono text-gray-300">
                    {row.losses > 0 ? (row.wins / row.losses).toFixed(2) : '∞'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ==================== FAMILY TAB ====================

function FamilyTab({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) return <LoadingSpinner text="Analizando familias..." />;
  if (!data) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      {data.families?.map((family: any) => (
        <div key={family.name} className="card">
          <div className="card-header flex items-center justify-between">
            <h3 className="card-title">{family.name}</h3>
            <Badge variant="gray">{family.count} instancias</Badge>
          </div>
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Solver</th>
                  <th>Resueltos</th>
                  <th>PAR-2</th>
                  <th>Tiempo promedio</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700">
                {family.solvers?.map((solver: any, index: number) => (
                  <tr key={solver.name} className={index === 0 ? 'bg-emerald-900/10' : ''}>
                    <td className="font-medium text-white">
                      {index === 0 && <Trophy className="w-4 h-4 text-yellow-500 inline mr-1" />}
                      {solver.name}
                    </td>
                    <td>
                      <span className="text-emerald-400">{solver.solved}</span>
                      <span className="text-gray-500">/{family.count}</span>
                    </td>
                    <td className="font-mono text-gray-300">{solver.par2.toFixed(2)}</td>
                    <td className="font-mono text-sm text-gray-300">{solver.avg_time.toFixed(3)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

// ==================== NORMALITY TAB ====================

function NormalityTab({ data, isLoading, experimentId, timeout }: {
  data: any; isLoading: boolean; experimentId: number; timeout: number;
}) {
  if (isLoading) return <LoadingSpinner text="Ejecutando tests de normalidad..." />;
  if (!data) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary-400" />
              Tests de Normalidad por Solver
            </h3>
            <p className="text-sm text-gray-400 mt-1">
              Shapiro-Wilk · D'Agostino-Pearson · Anderson-Darling
            </p>
          </div>
          <CsvButton experimentId={experimentId} tableName="normality" timeout={timeout} />
        </div>

        {Object.entries(data).map(([solver, tests]: any) => (
          <div key={solver} className="mb-6 last:mb-0">
            <h4 className="text-md font-semibold text-primary-300 mb-3 border-b border-dark-600 pb-2">{solver}</h4>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-3">
              {/* Shapiro-Wilk */}
              {tests.shapiro_wilk && !tests.shapiro_wilk.error && (
                <NormalityCard
                  name="Shapiro-Wilk"
                  statistic={tests.shapiro_wilk.statistic}
                  pValue={tests.shapiro_wilk.p_value}
                  isNormal={tests.shapiro_wilk.is_normal}
                  description={tests.shapiro_wilk.description}
                />
              )}
              {/* D'Agostino-Pearson */}
              {tests.dagostino && !tests.dagostino.error && (
                <NormalityCard
                  name="D'Agostino-Pearson"
                  statistic={tests.dagostino.statistic}
                  pValue={tests.dagostino.p_value}
                  isNormal={tests.dagostino.is_normal}
                  description={tests.dagostino.description}
                />
              )}
              {/* Anderson-Darling */}
              {tests.anderson_darling && !tests.anderson_darling.error && (
                <div className={clsx(
                  "p-4 rounded-lg border",
                  tests.anderson_darling.is_normal
                    ? "bg-emerald-900/10 border-emerald-700/50"
                    : "bg-red-900/10 border-red-700/50"
                )}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-white">Anderson-Darling</span>
                    {tests.anderson_darling.is_normal
                      ? <CheckCircle className="w-4 h-4 text-emerald-400" />
                      : <XCircle className="w-4 h-4 text-red-400" />}
                  </div>
                  <div className="text-sm text-gray-300 mb-1">
                    Estadístico: <strong>{tests.anderson_darling.statistic?.toFixed(6)}</strong>
                  </div>
                  <div className="text-xs text-gray-500 space-y-0.5">
                    {tests.anderson_darling.critical_values && Object.entries(tests.anderson_darling.critical_values).map(([level, info]: any) => (
                      <div key={level} className={clsx(info.reject_null ? "text-red-400" : "text-emerald-400")}>
                        α={level}: CV={info.critical_value?.toFixed(4)} {info.reject_null ? '✗ Rechaza' : '✓ No rechaza'}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="flex gap-4 text-sm text-gray-400">
              <span>n = {tests.n}</span>
              <span>Asimetría = {tests.skewness?.toFixed(4)}</span>
              <span>Curtosis = {tests.kurtosis?.toFixed(4)}</span>
            </div>
            {tests.recommendation && (
              <div className={clsx(
                "mt-2 p-3 rounded-lg text-sm",
                tests.recommendation.includes("NOT") || tests.recommendation.includes("no es")
                  ? "bg-yellow-900/20 border border-yellow-700/50 text-yellow-300"
                  : "bg-emerald-900/20 border border-emerald-700/50 text-emerald-300"
              )}>
                {tests.recommendation}
              </div>
            )}
          </div>
        ))}
      </div>

      <InfoBox color="blue" title="Sobre los Tests de Normalidad">
        <strong>Shapiro-Wilk:</strong> Mejor para n {'<'} 50.{' '}
        <strong>D'Agostino-Pearson:</strong> Basado en asimetría y curtosis, n ≥ 20.{' '}
        <strong>Anderson-Darling:</strong> Test general con mayor peso en las colas.
        Si NO es normal → usar tests no paramétricos (Wilcoxon, Friedman).
      </InfoBox>
    </div>
  );
}

function NormalityCard({ name, statistic, pValue, isNormal, description }: {
  name: string; statistic: number; pValue: number; isNormal: boolean; description: string;
}) {
  return (
    <div className={clsx(
      "p-4 rounded-lg border",
      isNormal ? "bg-emerald-900/10 border-emerald-700/50" : "bg-red-900/10 border-red-700/50"
    )}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-white">{name}</span>
        {isNormal ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
      </div>
      <div className="text-sm text-gray-300">
        Estadístico: <strong>{statistic?.toFixed(6)}</strong>
      </div>
      <div className="text-sm text-gray-300">
        p-value: <strong className={isNormal ? "text-emerald-400" : "text-red-400"}>{pValue?.toFixed(6)}</strong>
      </div>
      <div className="text-xs text-gray-500 mt-1">{description}</div>
    </div>
  );
}

// ==================== STATISTICAL TESTS TAB ====================

function StatisticalTestsTab({ data, isLoading, error, experimentId, timeout }: {
  data: any; isLoading: boolean; error: any; experimentId: number; timeout: number;
}) {
  if (isLoading) {
    return (
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-12 text-center">
        <Loader2 className="w-12 h-12 text-primary-400 mx-auto mb-4 animate-spin" />
        <p className="text-gray-400">Ejecutando pipeline de análisis...</p>
        <p className="text-gray-500 text-sm mt-2">Friedman / Wilcoxon + Post-Hoc + Correcciones</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="bg-dark-800 rounded-xl border border-red-700/50 p-8">
        <AlertCircle className="w-8 h-8 text-red-400 mb-2" />
        <p className="text-red-400">Error: {(error as any)?.message || 'Error al cargar'}</p>
      </div>
    );
  }
  if (!data) return <p className="text-gray-400">Sin datos de tests estadísticos</p>;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Friedman Test (k ≥ 3) */}
      {data.friedman && (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <FlaskConical className="w-5 h-5 text-primary-400" />
              Test de Friedman
            </h3>
            <CsvButton experimentId={experimentId} tableName="friedman" timeout={timeout} />
          </div>
          <p className="text-sm text-gray-400 mb-4">
            ANOVA no paramétrico para k ≥ 3 solvers. H0: todos los solvers tienen el mismo rendimiento.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <StatCard label="χ² Statistic" value={data.friedman.statistic?.toFixed(4)} />
            <StatCard label="p-value" value={data.friedman.p_value?.toFixed(6)} />
            <StatCard label="Significativo (α=0.05)" value={data.friedman.significant_005 ? "✅ Sí" : "❌ No"} />
            {data.friedman.effect_size != null && (
              <StatCard label="Kendall's W" value={`${data.friedman.effect_size?.toFixed(4)} (${data.friedman.effect_interpretation})`} />
            )}
          </div>
          {data.friedman.significant_005 && (
            <div className="bg-emerald-900/20 border border-emerald-700/50 rounded-lg p-3 text-sm text-emerald-300">
              ✅ Diferencias significativas → ver Nemenyi y correcciones abajo
            </div>
          )}
        </div>
      )}

      {/* Nemenyi Post-Hoc */}
      {data.nemenyi && (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white">Post-Hoc: Test de Nemenyi</h3>
            <CsvButton experimentId={experimentId} tableName="nemenyi" timeout={timeout} />
          </div>
          <p className="text-sm text-gray-400 mb-2">
            CD = {data.nemenyi.critical_difference?.toFixed(3)}. Pares con |R_i − R_j| {'>'} CD son significativamente diferentes.
          </p>
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
          <div className="overflow-x-auto">
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
                      {c.significant ? <CheckCircle className="w-4 h-4 text-emerald-400 inline" /> : <XCircle className="w-4 h-4 text-gray-500 inline" />}
                    </td>
                    <td className="py-2 text-right text-emerald-400 font-medium">{c.better_solver}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Wilcoxon Signed-Rank (2-solver) */}
      {data.wilcoxon && (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white">Test de Wilcoxon Signed-Rank</h3>
            <CsvButton experimentId={experimentId} tableName="full_statistical_tests" timeout={timeout} />
          </div>
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

      {/* Multiple Comparison Corrections */}
      {data.multiple_corrections && (
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white">Correcciones por Comparaciones Múltiples</h3>
            <CsvButton experimentId={experimentId} tableName="corrections" timeout={timeout} />
          </div>
          <p className="text-sm text-gray-400 mb-4">
            p-values de Wilcoxon ajustados con Bonferroni, Holm-Bonferroni y Benjamini-Hochberg (FDR).
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left text-gray-300 pb-2 border-b border-dark-600">Par (Wilcoxon)</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">p original</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Bonferroni</th>
                  <th className="text-center text-gray-300 pb-2 border-b border-dark-600">Sig.</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Holm</th>
                  <th className="text-center text-gray-300 pb-2 border-b border-dark-600">Sig.</th>
                  <th className="text-right text-gray-300 pb-2 border-b border-dark-600">B-H (FDR)</th>
                  <th className="text-center text-gray-300 pb-2 border-b border-dark-600">Sig.</th>
                </tr>
              </thead>
              <tbody>
                {data.multiple_corrections.labels?.map((label: string, i: number) => (
                  <tr key={i} className="border-b border-dark-700/50">
                    <td className="py-2 text-white">{label}</td>
                    <td className="py-2 text-right font-mono text-gray-300">
                      {data.multiple_corrections.bonferroni?.original_pvalues?.[i]?.toFixed(6)}
                    </td>
                    <td className={clsx("py-2 text-right font-mono",
                      data.multiple_corrections.bonferroni?.significant_005?.[i] ? "text-emerald-400" : "text-gray-400"
                    )}>
                      {data.multiple_corrections.bonferroni?.adjusted_pvalues?.[i]?.toFixed(6)}
                    </td>
                    <td className="py-2 text-center">
                      {data.multiple_corrections.bonferroni?.significant_005?.[i]
                        ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400 inline" />
                        : <XCircle className="w-3.5 h-3.5 text-gray-500 inline" />}
                    </td>
                    <td className={clsx("py-2 text-right font-mono",
                      data.multiple_corrections.holm?.significant_005?.[i] ? "text-emerald-400" : "text-gray-400"
                    )}>
                      {data.multiple_corrections.holm?.adjusted_pvalues?.[i]?.toFixed(6)}
                    </td>
                    <td className="py-2 text-center">
                      {data.multiple_corrections.holm?.significant_005?.[i]
                        ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400 inline" />
                        : <XCircle className="w-3.5 h-3.5 text-gray-500 inline" />}
                    </td>
                    <td className={clsx("py-2 text-right font-mono",
                      data.multiple_corrections.benjamini_hochberg?.significant_005?.[i] ? "text-emerald-400" : "text-gray-400"
                    )}>
                      {data.multiple_corrections.benjamini_hochberg?.adjusted_pvalues?.[i]?.toFixed(6)}
                    </td>
                    <td className="py-2 text-center">
                      {data.multiple_corrections.benjamini_hochberg?.significant_005?.[i]
                        ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400 inline" />
                        : <XCircle className="w-3.5 h-3.5 text-gray-500 inline" />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-gray-500">
            <div><strong className="text-gray-400">Bonferroni:</strong> más conservador (FWER)</div>
            <div><strong className="text-gray-400">Holm-Bonferroni:</strong> step-down, más potente (FWER)</div>
            <div><strong className="text-gray-400">Benj.-Hochberg:</strong> controla FDR, menos conservador</div>
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

// ==================== EFFECT SIZES TAB ====================

function EffectSizesTab({ data, isLoading, experimentId, timeout }: {
  data: any; isLoading: boolean; experimentId: number; timeout: number;
}) {
  if (isLoading) return <LoadingSpinner text="Calculando tamaños de efecto..." />;
  if (!data) return null;

  const pairs = Object.entries(data);

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Ruler className="w-5 h-5 text-primary-400" />
              Tamaños de Efecto (Effect Sizes)
            </h3>
            <p className="text-sm text-gray-400 mt-1">
              Cohen's d y Vargha-Delaney A para cada par de solvers
            </p>
          </div>
          <CsvButton experimentId={experimentId} tableName="effect_sizes" timeout={timeout} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left text-gray-300 pb-2 border-b border-dark-600">Par</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Cohen's d</th>
                <th className="text-center text-gray-300 pb-2 border-b border-dark-600">Magnitud</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Dirección</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">V-D A</th>
                <th className="text-center text-gray-300 pb-2 border-b border-dark-600">Magnitud</th>
                <th className="text-right text-gray-300 pb-2 border-b border-dark-600">Dirección</th>
              </tr>
            </thead>
            <tbody>
              {pairs.map(([pair, values]: any) => (
                <tr key={pair} className="border-b border-dark-700/50">
                  <td className="py-2 text-white font-medium">{pair.replace(/_vs_/g, ' vs ')}</td>
                  <td className="py-2 text-right font-mono text-gray-300">{values.cohens_d?.cohens_d?.toFixed(4)}</td>
                  <td className="py-2 text-center"><EffectBadge interpretation={values.cohens_d?.interpretation} /></td>
                  <td className="py-2 text-right text-gray-400 text-xs">{values.cohens_d?.direction}</td>
                  <td className="py-2 text-right font-mono text-gray-300">{values.vargha_delaney?.A_measure?.toFixed(4)}</td>
                  <td className="py-2 text-center"><EffectBadge interpretation={values.vargha_delaney?.interpretation} /></td>
                  <td className="py-2 text-right text-gray-400 text-xs">{values.vargha_delaney?.direction}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <InfoBox color="blue" title="Sobre los Tamaños de Efecto">
        <strong>Cohen's d:</strong> |d| {'<'} 0.2: negligible, {'<'} 0.5: pequeño, {'<'} 0.8: mediano, ≥ 0.8: grande.
        {' '}<strong>Vargha-Delaney A:</strong> P(solver1 {'<'} solver2). A = 0.5 = sin diferencia. Recomendado por Arcuri & Briand (2011).
      </InfoBox>
    </div>
  );
}

function EffectBadge({ interpretation }: { interpretation?: string }) {
  const colors: Record<string, string> = {
    negligible: 'bg-gray-700 text-gray-300',
    small: 'bg-blue-900/30 text-blue-300 border border-blue-700/50',
    medium: 'bg-yellow-900/30 text-yellow-300 border border-yellow-700/50',
    large: 'bg-red-900/30 text-red-300 border border-red-700/50',
  };
  return (
    <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", colors[interpretation || ''] || 'bg-dark-700 text-gray-400')}>
      {interpretation || '?'}
    </span>
  );
}

// ==================== BOOTSTRAP TAB ====================

function BootstrapTab({ data, isLoading, error, experimentId, timeout }: {
  data: any; isLoading: boolean; error: any; experimentId: number; timeout: number;
}) {
  if (isLoading) {
    return (
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-12 text-center">
        <Loader2 className="w-12 h-12 text-primary-400 mx-auto mb-4 animate-spin" />
        <p className="text-gray-400">Ejecutando bootstrap...</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="bg-dark-800 rounded-xl border border-red-700/50 p-8">
        <AlertCircle className="w-8 h-8 text-red-400 mb-2" />
        <p className="text-red-400">Error: {(error as any)?.message || 'Error al cargar'}</p>
      </div>
    );
  }
  if (!data) return <p className="text-gray-400">Sin datos de bootstrap</p>;

  const bootstrapResults = data.bootstrap_results || data;
  const confidenceLevel = data.confidence_level || 0.95;
  const nBootstrap = data.n_bootstrap || '?';

  const solverEntries = Object.entries(bootstrapResults).filter(([key]) => key !== 'pairwise_differences');
  const pairwiseDiffs = bootstrapResults.pairwise_differences;

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary-400" />
              Bootstrap Confidence Intervals
            </h3>
            <p className="text-sm text-gray-400 mt-1">
              BCa (Bias-Corrected and Accelerated), {nBootstrap} replicaciones, CI {(confidenceLevel * 100).toFixed(0)}%.
            </p>
          </div>
          <CsvButton experimentId={experimentId} tableName="bootstrap" timeout={timeout} />
        </div>

        {solverEntries.map(([solver, results]: any) => (
          <div key={solver} className="mb-6">
            <h4 className="text-md font-semibold text-primary-300 mb-3">{solver}</h4>
            {results.error ? (
              <p className="text-red-400 text-sm">{results.error}</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {Object.entries(results).map(([metric, vals]: any) => {
                  if (!vals || typeof vals !== 'object') return null;
                  const pointEst = vals.statistic ?? vals.point_estimate;
                  const ciLower = vals.ci_lower ?? (vals.ci_95 || vals.ci || [])[0];
                  const ciUpper = vals.ci_upper ?? (vals.ci_95 || vals.ci || [])[1];
                  if (pointEst == null) return null;
                  return (
                    <div key={metric} className="bg-dark-700/50 rounded-lg p-3 border border-dark-600">
                      <div className="text-xs text-gray-500 uppercase mb-1">{metric.replace(/_/g, ' ')}</div>
                      <div className="text-lg font-bold text-white">{pointEst?.toFixed(4)}</div>
                      {ciLower != null && ciUpper != null && (
                        <div className="text-sm text-gray-400">CI: [{ciLower?.toFixed(4)}, {ciUpper?.toFixed(4)}]</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}

        {pairwiseDiffs && Object.keys(pairwiseDiffs).length > 0 && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-md font-semibold text-white">Diferencias Pairwise (Bootstrap)</h4>
              <CsvButton experimentId={experimentId} tableName="pairwise_bootstrap" timeout={timeout} />
            </div>
            <div className="overflow-x-auto">
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
                      <td className="py-2 text-right font-mono text-gray-300">{vals.statistic?.toFixed(4)}</td>
                      <td className="py-2 text-right font-mono text-gray-400">{vals.ci_lower?.toFixed(4)}</td>
                      <td className="py-2 text-right font-mono text-gray-400">{vals.ci_upper?.toFixed(4)}</td>
                      <td className="py-2 text-center">
                        {vals.significant ? <CheckCircle className="w-4 h-4 text-emerald-400 inline" /> : <XCircle className="w-4 h-4 text-gray-500 inline" />}
                      </td>
                      <td className="py-2 text-right text-emerald-400 font-medium">{vals.faster_solver || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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

  const plots = data?.plots || data;
  if (!plots || Object.keys(plots).length === 0) return <p className="text-gray-400">Sin gráficos disponibles</p>;

  const plotDescriptions: Record<string, string> = {
    cactus: 'Cactus Plot — Instancias resueltas vs tiempo.',
    ecdf: 'ECDF — Fracción acumulada de instancias resueltas.',
    boxplot: 'Boxplot — Distribución de tiempos de ejecución.',
    performance_profile: 'Performance Profile (Dolan & Moré).',
    survival: 'Survival Plot — Fracción NO resuelta.',
    par2_bar: 'PAR-2 Scores — Menor = mejor.',
    heatmap: 'Heatmap — Rendimiento por solver y familia.',
    critical_difference: 'Critical Difference Diagram (Demšar).',
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {Object.entries(plots).map(([name, imgData]: any) => {
        const desc = Object.entries(plotDescriptions).find(([k]) => name.startsWith(k))?.[1] || name.replace(/_/g, ' ');
        return (
          <div key={name} className="bg-dark-800 rounded-xl border border-dark-700 p-4">
            <h3 className="text-md font-semibold text-white mb-1">
              {name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
            </h3>
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
    <div className="space-y-4 animate-fade-in">
      <div className="bg-dark-800 rounded-xl border border-dark-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-3">Informe Completo</h3>
        <p className="text-gray-400 mb-4">
          HTML auto-contenido con métricas, gráficos embebidos, tests estadísticos e intervalos de confianza.
        </p>
        <a
          href={reportUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors font-medium"
        >
          <ExternalLink className="w-5 h-5" />
          Abrir Informe HTML
        </a>
      </div>
      <div className="bg-dark-800 rounded-xl border border-dark-700 overflow-hidden">
        <div className="p-3 border-b border-dark-700 flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="ml-2 text-sm text-gray-400">Vista previa</span>
        </div>
        <iframe src={reportUrl} className="w-full h-[600px] bg-white" title="Report Preview" />
      </div>
    </div>
  );
}

// ==================== HELPERS ====================

function TopMetricCard({ label, value, icon, sub }: { label: string; value: any; icon: React.ReactNode; sub?: string }) {
  return (
    <div className="card">
      <div className="card-body text-center">
        <div className="mx-auto mb-2">{icon}</div>
        <p className="text-gray-400">{label}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
        {sub && <p className="text-sm text-gray-400">{sub}</p>}
      </div>
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

function InfoBox({ color, title, children }: { color: string; title: string; children: React.ReactNode }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-900/20 border-blue-700/50 text-blue-300',
    purple: 'bg-purple-900/20 border-purple-700/50 text-purple-300',
    green: 'bg-emerald-900/20 border-emerald-700/50 text-emerald-300',
  };
  return (
    <div className={clsx("border rounded-lg p-4", colors[color] || colors.blue)}>
      <h4 className="font-medium mb-1">{title}</h4>
      <div className="text-sm opacity-90">{children}</div>
    </div>
  );
}
