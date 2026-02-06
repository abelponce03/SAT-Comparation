import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Cell,
  ReferenceLine,
  BarChart,
  Bar,
  AreaChart,
  Area,
} from 'recharts';
import {
  BarChart3,
  ScatterChart as ScatterIcon,
  TrendingUp,
  Thermometer,
  Info,
  Layers,
  Timer,
  CheckCircle,
  ArrowRightLeft,
} from 'lucide-react';
import { analysisApi, experimentsApi } from '@/services/api';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import EmptyState from '@/components/common/EmptyState';
import clsx from 'clsx';

type ChartType = 'cactus' | 'scatter' | 'ecdf' | 'bars' | 'heatmap';

const SOLVER_COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b',
  '#8b5cf6', '#ec4899', '#06b6d4', '#f97316',
];

// ==================== HELPERS ====================

function ChartCard({
  title,
  subtitle,
  children,
  info,
  className,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  info?: string;
  className?: string;
}) {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <div className={clsx('bg-dark-800 border border-dark-700 rounded-xl overflow-hidden', className)}>
      <div className="flex items-center justify-between px-5 py-4 border-b border-dark-700">
        <div>
          <h3 className="text-base font-semibold text-white">{title}</h3>
          {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {info && (
          <button
            onClick={() => setShowInfo(!showInfo)}
            className="p-1.5 rounded-lg hover:bg-dark-700 text-gray-400 transition-colors"
            title="Cómo interpretar"
          >
            <Info className="w-4 h-4" />
          </button>
        )}
      </div>
      {showInfo && info && (
        <div className="px-5 py-3 bg-primary-900/20 border-b border-primary-800/30 text-sm text-primary-200/80">
          {info}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

function StatPill({ label, value, icon: Icon, color = 'gray' }: {
  label: string;
  value: string | number;
  icon?: any;
  color?: 'green' | 'red' | 'blue' | 'yellow' | 'gray';
}) {
  const colors: Record<string, string> = {
    green: 'bg-green-900/30 border-green-700/40 text-green-300',
    red: 'bg-red-900/30 border-red-700/40 text-red-300',
    blue: 'bg-blue-900/30 border-blue-700/40 text-blue-300',
    yellow: 'bg-yellow-900/30 border-yellow-700/40 text-yellow-300',
    gray: 'bg-dark-700/50 border-dark-600 text-gray-300',
  };

  return (
    <div className={clsx('flex items-center gap-2 px-3 py-2 rounded-lg border text-sm', colors[color])}>
      {Icon && <Icon className="w-4 h-4 flex-shrink-0 opacity-70" />}
      <span className="text-gray-400">{label}:</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}

// ==================== MAIN COMPONENT ====================

export default function Visualization() {
  const [selectedExperiment, setSelectedExperiment] = useState<number | null>(null);
  const [chartType, setChartType] = useState<ChartType>('cactus');
  const [timeout, setTimeout] = useState(5000);
  const [logScale, setLogScale] = useState(true);

  const { data: experiments } = useQuery({
    queryKey: ['experiments', 'completed'],
    queryFn: () => experimentsApi.getAll('completed'),
  });

  // Prefetch summary for quick stats
  const { data: summary } = useQuery({
    queryKey: ['analysis', 'summary', selectedExperiment],
    queryFn: () => analysisApi.getSummary(selectedExperiment!),
    enabled: !!selectedExperiment,
  });

  const { data: cactusData, isLoading: cactusLoading } = useQuery({
    queryKey: ['visualization', 'cactus', selectedExperiment, timeout],
    queryFn: () => analysisApi.getCactusData(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && chartType === 'cactus',
  });

  const { data: scatterData, isLoading: scatterLoading } = useQuery({
    queryKey: ['visualization', 'scatter', selectedExperiment],
    queryFn: () => analysisApi.getScatterData(selectedExperiment!),
    enabled: !!selectedExperiment && chartType === 'scatter',
  });

  const { data: ecdfData, isLoading: ecdfLoading } = useQuery({
    queryKey: ['visualization', 'ecdf', selectedExperiment],
    queryFn: () => analysisApi.getECDFData(selectedExperiment!),
    enabled: !!selectedExperiment && chartType === 'ecdf',
  });

  const { data: par2Data, isLoading: par2Loading } = useQuery({
    queryKey: ['analysis', 'par2', selectedExperiment, timeout],
    queryFn: () => analysisApi.getPAR2(selectedExperiment!, timeout),
    enabled: !!selectedExperiment && chartType === 'bars',
  });

  const chartTabs = [
    { id: 'cactus' as const, label: 'Cactus Plot', icon: TrendingUp, desc: 'Instancias vs tiempo' },
    { id: 'scatter' as const, label: 'Scatter', icon: ScatterIcon, desc: 'Solver vs solver' },
    { id: 'ecdf' as const, label: 'ECDF', icon: BarChart3, desc: 'Perfil de rendimiento' },
    { id: 'bars' as const, label: 'PAR-2 / Solved', icon: Layers, desc: 'Ranking rápido' },
    { id: 'heatmap' as const, label: 'Heatmap', icon: Thermometer, desc: 'Mapa de calor' },
  ];

  const solverNames = summary?.solvers || [];
  const solvedCounts = summary?.solved_counts || {};

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Visualización Interactiva</h1>
          <p className="text-gray-400 mt-1">
            Gráficos interactivos con zoom, tooltips y escalas configurables
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={logScale}
              onChange={(e) => setLogScale(e.target.checked)}
              className="rounded border-dark-600 bg-dark-700 text-primary-500 focus:ring-primary-500"
            />
            Escala log
          </label>
        </div>
      </div>

      {/* Experiment + Timeout selector */}
      <div className="bg-dark-800 border border-dark-700 rounded-xl">
        <div className="p-5">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Experimento</label>
              <select
                value={selectedExperiment || ''}
                onChange={(e) => setSelectedExperiment(parseInt(e.target.value) || null)}
                className="input"
              >
                <option value="">Selecciona un experimento</option>
                {experiments?.map((exp: any) => (
                  <option key={exp.id} value={exp.id}>
                    {exp.name} — {exp.completed_runs} ejecuciones
                  </option>
                ))}
              </select>
            </div>
            <div className="w-36">
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Timeout (s)</label>
              <input
                type="number"
                value={timeout}
                onChange={(e) => setTimeout(parseInt(e.target.value) || 5000)}
                className="input"
                min={1}
              />
            </div>
          </div>
        </div>

        {/* Quick stats ribbon */}
        {selectedExperiment && solverNames.length > 0 && (
          <div className="border-t border-dark-700 px-5 py-3 flex flex-wrap gap-3">
            <StatPill label="Solvers" value={solverNames.length} icon={Layers} color="blue" />
            {Object.entries(solvedCounts).map(([solver, counts]: any) => (
              <StatPill
                key={solver}
                label={solver}
                value={`${counts.solved}/${counts.total} (${counts.solved_pct}%)`}
                icon={counts.solved_pct === 100 ? CheckCircle : Timer}
                color={counts.solved_pct === 100 ? 'green' : counts.solved_pct > 80 ? 'yellow' : 'red'}
              />
            ))}
          </div>
        )}
      </div>

      {!selectedExperiment ? (
        <EmptyState
          title="Selecciona un experimento"
          description="Elige un experimento completado para visualizar los resultados interactivamente"
          icon={<BarChart3 className="w-6 h-6 text-gray-400" />}
        />
      ) : (
        <>
          {/* Chart Type Tabs */}
          <div className="flex gap-2 overflow-x-auto pb-1">
            {chartTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setChartType(tab.id)}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap',
                  chartType === tab.id
                    ? 'bg-primary-600/20 text-primary-300 border border-primary-600/40'
                    : 'bg-dark-800 text-gray-400 hover:text-gray-300 border border-dark-700 hover:border-dark-600'
                )}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
                <span className="text-xs opacity-60 hidden sm:inline">{tab.desc}</span>
              </button>
            ))}
          </div>

          {/* Chart Content */}
          <div>
            {chartType === 'cactus' && (
              <CactusPlot data={cactusData} isLoading={cactusLoading} timeout={timeout} logScale={logScale} />
            )}
            {chartType === 'scatter' && (
              <ScatterPlot data={scatterData} isLoading={scatterLoading} timeout={timeout} logScale={logScale} />
            )}
            {chartType === 'ecdf' && (
              <ECDFPlot data={ecdfData} isLoading={ecdfLoading} logScale={logScale} />
            )}
            {chartType === 'bars' && (
              <BarSummary data={par2Data} isLoading={par2Loading} solvedCounts={solvedCounts} />
            )}
            {chartType === 'heatmap' && (
              <HeatmapPlot experimentId={selectedExperiment} />
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ==================== CACTUS PLOT ====================

function CactusPlot({ data, isLoading, timeout, logScale }: {
  data: any; isLoading: boolean; timeout: number; logScale: boolean;
}) {
  if (isLoading) return <LoadingSpinner text="Generando cactus plot..." />;
  if (!data) return null;

  const solvers = Object.keys(data.solvers || {});

  const chartData = useMemo(() => {
    if (!data.solvers) return [];
    const maxInstances = Math.max(...solvers.map(s => data.solvers[s]?.length || 0));
    return Array.from({ length: maxInstances }, (_, i) => {
      const point: any = { instance: i + 1 };
      solvers.forEach(solver => {
        const times = data.solvers[solver] || [];
        point[solver] = times[i] ?? null;
      });
      return point;
    });
  }, [data, solvers]);

  const solverStats = useMemo(() =>
    solvers.map(s => {
      const times: number[] = data.solvers[s] || [];
      return {
        name: s,
        solved: times.length,
        fastest: times.length > 0 ? times[0].toFixed(4) : '-',
        median: times.length > 0 ? times[Math.floor(times.length / 2)].toFixed(4) : '-',
        slowest: times.length > 0 ? times[times.length - 1].toFixed(4) : '-',
      };
    }),
  [data, solvers]);

  return (
    <div className="space-y-4">
      <ChartCard
        title="Cactus Plot"
        subtitle="Instancias resueltas (ordenadas por tiempo creciente)"
        info="Un solver es mejor si su curva está más a la derecha (resuelve más instancias) y más abajo (más rápido). La línea roja indica el timeout."
      >
        <div className="h-[520px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="instance"
                stroke="#9ca3af"
                label={{ value: 'Instancias resueltas', position: 'insideBottom', offset: -15, fill: '#9ca3af', fontSize: 12 }}
              />
              <YAxis
                scale={logScale ? 'log' : 'auto'}
                domain={logScale ? [0.001, timeout] : [0, timeout]}
                stroke="#9ca3af"
                tickFormatter={(v: number) => v >= 1 ? v.toFixed(0) : v.toFixed(3)}
                label={{ value: 'Tiempo (s)', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 12 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#d1d5db' }}
                formatter={(value: any, name: string) => [`${value?.toFixed(4)}s`, name]}
                labelFormatter={(label) => `Instancia #${label}`}
              />
              <Legend wrapperStyle={{ paddingTop: 10 }} />
              <ReferenceLine y={timeout} stroke="#ef4444" strokeDasharray="5 5" label={{ value: `Timeout (${timeout}s)`, fill: '#ef4444', fontSize: 11 }} />
              {solvers.map((solver, i) => (
                <Line
                  key={solver}
                  type="stepAfter"
                  dataKey={solver}
                  stroke={SOLVER_COLORS[i % SOLVER_COLORS.length]}
                  strokeWidth={2.5}
                  dot={false}
                  connectNulls
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* Quick stats table */}
      <div className="bg-dark-800 border border-dark-700 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-dark-700">
          <h4 className="text-sm font-medium text-gray-300">Resumen rápido</h4>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-dark-900/50">
            <tr>
              <th className="px-4 py-2 text-left text-gray-400 font-medium">Solver</th>
              <th className="px-4 py-2 text-right text-gray-400 font-medium">Resueltas</th>
              <th className="px-4 py-2 text-right text-gray-400 font-medium">Más rápida</th>
              <th className="px-4 py-2 text-right text-gray-400 font-medium">Mediana</th>
              <th className="px-4 py-2 text-right text-gray-400 font-medium">Más lenta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700">
            {solverStats.map((s, i) => (
              <tr key={s.name} className="hover:bg-dark-700/30 transition-colors">
                <td className="px-4 py-2 font-medium flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: SOLVER_COLORS[i % SOLVER_COLORS.length] }} />
                  <span className="text-white">{s.name}</span>
                </td>
                <td className="px-4 py-2 text-right font-mono text-gray-300">{s.solved}</td>
                <td className="px-4 py-2 text-right font-mono text-green-400">{s.fastest}s</td>
                <td className="px-4 py-2 text-right font-mono text-gray-300">{s.median}s</td>
                <td className="px-4 py-2 text-right font-mono text-yellow-400">{s.slowest}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==================== SCATTER PLOT ====================

function ScatterPlot({ data, isLoading, timeout, logScale }: {
  data: any; isLoading: boolean; timeout: number; logScale: boolean;
}) {
  const [solver1, setSolver1] = useState('');
  const [solver2, setSolver2] = useState('');

  const solvers: string[] = useMemo(() => data?.solvers || [], [data]);

  useMemo(() => {
    if (solvers.length >= 2) {
      if (!solver1) setSolver1(solvers[0]);
      if (!solver2) setSolver2(solvers[1]);
    }
  }, [solvers]);

  const chartData = useMemo(() => {
    if (!data?.points || !solver1 || !solver2) return [];
    return data.points
      .filter((p: any) => p.solver1 === solver1 && p.solver2 === solver2)
      .map((p: any) => ({ x: p.time1, y: p.time2, benchmark: p.benchmark }));
  }, [data, solver1, solver2]);

  const stats = useMemo(() => {
    if (!chartData.length) return null;
    const s1Wins = chartData.filter((p: any) => p.x < p.y).length;
    const s2Wins = chartData.filter((p: any) => p.x > p.y).length;
    const ties = chartData.length - s1Wins - s2Wins;
    return { s1Wins, s2Wins, ties, total: chartData.length };
  }, [chartData]);

  if (isLoading) return <LoadingSpinner text="Generando scatter plot..." />;
  if (!data) return null;

  return (
    <div className="space-y-4">
      {/* Solver selectors with swap button */}
      <div className="bg-dark-800 border border-dark-700 rounded-xl p-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="block text-xs text-gray-400 mb-1">Solver X (horizontal)</label>
            <select value={solver1} onChange={(e) => setSolver1(e.target.value)} className="input">
              {solvers.map((s: string) => (<option key={s} value={s}>{s}</option>))}
            </select>
          </div>
          <button
            onClick={() => { const tmp = solver1; setSolver1(solver2); setSolver2(tmp); }}
            className="mt-4 p-2 rounded-lg bg-dark-700 hover:bg-dark-600 text-gray-400 transition-colors"
            title="Intercambiar ejes"
          >
            <ArrowRightLeft className="w-4 h-4" />
          </button>
          <div className="flex-1">
            <label className="block text-xs text-gray-400 mb-1">Solver Y (vertical)</label>
            <select value={solver2} onChange={(e) => setSolver2(e.target.value)} className="input">
              {solvers.map((s: string) => (<option key={s} value={s}>{s}</option>))}
            </select>
          </div>
        </div>
      </div>

      {/* Win/lose summary */}
      {stats && (
        <div className="flex gap-3 flex-wrap">
          <StatPill label={solver1} value={`${stats.s1Wins} wins`} icon={CheckCircle} color="green" />
          <StatPill label="Empates" value={stats.ties} icon={ArrowRightLeft} color="gray" />
          <StatPill label={solver2} value={`${stats.s2Wins} wins`} icon={CheckCircle} color="blue" />
        </div>
      )}

      <ChartCard
        title={`Scatter: ${solver1} vs ${solver2}`}
        subtitle={`${chartData.length} benchmarks comparados`}
        info={`Puntos debajo de la diagonal: ${solver1} fue más rápido. Puntos encima: ${solver2} fue más rápido. Cuanto más lejos de la diagonal, mayor la diferencia.`}
      >
        <div className="h-[520px]">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 30, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number"
                dataKey="x"
                name={solver1}
                scale={logScale ? 'log' : 'auto'}
                domain={logScale ? [0.001, timeout] : [0, timeout]}
                stroke="#9ca3af"
                tickFormatter={(v: number) => v >= 1 ? v.toFixed(0) : v.toFixed(3)}
                label={{ value: solver1 + ' (s)', position: 'insideBottom', offset: -15, fill: '#9ca3af', fontSize: 12 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name={solver2}
                scale={logScale ? 'log' : 'auto'}
                domain={logScale ? [0.001, timeout] : [0, timeout]}
                stroke="#9ca3af"
                tickFormatter={(v: number) => v >= 1 ? v.toFixed(0) : v.toFixed(3)}
                label={{ value: solver2 + ' (s)', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 12 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                formatter={(value: any, name: string) => [`${value?.toFixed(4)}s`, name]}
                labelFormatter={(_, payload: any) => payload[0]?.payload?.benchmark || ''}
              />
              <ReferenceLine segment={[{ x: 0.001, y: 0.001 }, { x: timeout, y: timeout }]} stroke="#6b7280" strokeDasharray="5 5" />
              <Scatter data={chartData} fill="#3b82f6">
                {chartData.map((entry: any, index: number) => (
                  <Cell
                    key={index}
                    fill={entry.x < entry.y ? '#10b981' : entry.x > entry.y ? '#ef4444' : '#9ca3af'}
                    fillOpacity={0.75}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  );
}

// ==================== ECDF / Performance Profile ====================

function ECDFPlot({ data, isLoading, logScale }: { data: any; isLoading: boolean; logScale: boolean }) {
  if (isLoading) return <LoadingSpinner text="Generando ECDF..." />;
  if (!data) return null;

  const solvers = Object.keys(data.profiles || {});

  const chartData = useMemo(() => {
    if (!data.profiles) return [];
    const allRatios = new Set<number>();
    solvers.forEach(s => data.profiles[s]?.forEach((p: any) => allRatios.add(p.ratio)));
    return Array.from(allRatios)
      .sort((a, b) => a - b)
      .map(ratio => {
        const point: any = { ratio };
        solvers.forEach(solver => {
          const profile = data.profiles[solver] || [];
          const match = profile.find((p: any) => p.ratio === ratio);
          point[solver] = match?.probability ?? null;
        });
        return point;
      });
  }, [data, solvers]);

  const atTau1 = useMemo(() => {
    if (!data.profiles) return [];
    return solvers.map(s => {
      const profile = data.profiles[s] || [];
      const entry = profile.find((p: any) => Math.abs(p.ratio - 1) < 0.01);
      return { name: s, pct: entry ? (entry.probability * 100).toFixed(1) : '0' };
    }).sort((a, b) => parseFloat(b.pct) - parseFloat(a.pct));
  }, [data, solvers]);

  return (
    <div className="space-y-4">
      {atTau1.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {atTau1.map((s, i) => (
            <StatPill
              key={s.name}
              label={s.name}
              value={`${s.pct}% mejor en τ=1`}
              color={i === 0 ? 'green' : 'gray'}
            />
          ))}
        </div>
      )}

      <ChartCard
        title="Performance Profile (ECDF)"
        subtitle="Probabilidad de resolver dentro de un factor τ del mejor solver (Dolan & Moré)"
        info="En τ=1 se muestra qué fracción de instancias el solver es el más rápido. Curvas más altas y a la izquierda = mejor rendimiento global."
      >
        <div className="h-[520px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 30, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="ratio"
                scale={logScale ? 'log' : 'auto'}
                domain={[1, 'auto']}
                stroke="#9ca3af"
                tickFormatter={(v: number) => v.toFixed(1)}
                label={{ value: 'Factor τ (ratio al mejor)', position: 'insideBottom', offset: -15, fill: '#9ca3af', fontSize: 12 }}
              />
              <YAxis
                domain={[0, 1]}
                stroke="#9ca3af"
                tickFormatter={(v: number) => (v * 100).toFixed(0) + '%'}
                label={{ value: 'P(ratio ≤ τ)', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 12 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                formatter={(value: any, name: string) => [(value * 100).toFixed(1) + '%', name]}
                labelFormatter={(label) => `τ = ${parseFloat(label).toFixed(2)}`}
              />
              <Legend wrapperStyle={{ paddingTop: 10 }} />
              <ReferenceLine x={1} stroke="#6b7280" strokeDasharray="3 3" label={{ value: 'τ=1', fill: '#6b7280', fontSize: 10 }} />
              {solvers.map((solver, i) => (
                <Area
                  key={solver}
                  type="stepAfter"
                  dataKey={solver}
                  stroke={SOLVER_COLORS[i % SOLVER_COLORS.length]}
                  fill={SOLVER_COLORS[i % SOLVER_COLORS.length]}
                  fillOpacity={0.08}
                  strokeWidth={2.5}
                  dot={false}
                  connectNulls
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  );
}

// ==================== BAR CHART (PAR-2 + Solved) ====================

function BarSummary({ data, isLoading, solvedCounts }: {
  data: any; isLoading: boolean; solvedCounts: any;
}) {
  if (isLoading) return <LoadingSpinner text="Calculando PAR-2..." />;
  if (!data) return null;

  const par2Scores = data?.par2_scores || {};
  const solvers = Object.keys(par2Scores);

  const barData = useMemo(() =>
    solvers
      .map(s => ({
        solver: s,
        par2: par2Scores[s] || 0,
        solved: solvedCounts[s]?.solved || 0,
        total: solvedCounts[s]?.total || 0,
        solved_pct: solvedCounts[s]?.solved_pct || 0,
      }))
      .sort((a, b) => a.par2 - b.par2),
  [par2Scores, solvedCounts, solvers]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="PAR-2 Score" subtitle="Menor = mejor (penaliza timeouts ×2)" info="PAR-2 asigna 2× el timeout a instancias no resueltas. El solver con menor PAR-2 tiene el mejor rendimiento general.">
          <div className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" stroke="#9ca3af" />
                <YAxis type="category" dataKey="solver" stroke="#9ca3af" width={80} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                  formatter={(value: any) => [`${value.toFixed(4)}s`, 'PAR-2']}
                />
                <Bar dataKey="par2" radius={[0, 6, 6, 0]}>
                  {barData.map((_: any, i: number) => (
                    <Cell key={i} fill={SOLVER_COLORS[i % SOLVER_COLORS.length]} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Instancias resueltas" subtitle="SAT + UNSAT" info="Total de instancias que el solver pudo resolver dentro del timeout.">
          <div className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" stroke="#9ca3af" />
                <YAxis type="category" dataKey="solver" stroke="#9ca3af" width={80} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                  formatter={(value: any) => [value, 'Resueltas']}
                />
                <Bar dataKey="solved" radius={[0, 6, 6, 0]}>
                  {barData.map((_: any, i: number) => (
                    <Cell key={i} fill={SOLVER_COLORS[i % SOLVER_COLORS.length]} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      {/* Ranking table */}
      <div className="bg-dark-800 border border-dark-700 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-dark-700">
          <h4 className="text-sm font-medium text-gray-300">Ranking completo</h4>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-dark-900/50">
            <tr>
              <th className="px-4 py-2 text-left text-gray-400 font-medium">#</th>
              <th className="px-4 py-2 text-left text-gray-400 font-medium">Solver</th>
              <th className="px-4 py-2 text-right text-gray-400 font-medium">PAR-2 (s)</th>
              <th className="px-4 py-2 text-right text-gray-400 font-medium">Resueltas</th>
              <th className="px-4 py-2 text-right text-gray-400 font-medium">% Resueltas</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700">
            {barData.map((row: any, i: number) => (
              <tr key={row.solver} className="hover:bg-dark-700/30 transition-colors">
                <td className="px-4 py-2 text-gray-500">{i + 1}</td>
                <td className="px-4 py-2 font-medium flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: SOLVER_COLORS[i % SOLVER_COLORS.length] }} />
                  <span className="text-white">{row.solver}</span>
                </td>
                <td className="px-4 py-2 text-right font-mono text-gray-300">{row.par2.toFixed(4)}</td>
                <td className="px-4 py-2 text-right font-mono text-gray-300">{row.solved}/{row.total}</td>
                <td className="px-4 py-2 text-right">
                  <span className={clsx(
                    'font-mono px-2 py-0.5 rounded text-xs',
                    row.solved_pct === 100 ? 'bg-green-900/30 text-green-400'
                      : row.solved_pct > 80 ? 'bg-yellow-900/30 text-yellow-400'
                      : 'bg-red-900/30 text-red-400'
                  )}>
                    {row.solved_pct}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==================== HEATMAP ====================

function HeatmapPlot({ experimentId }: { experimentId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['visualization', 'heatmap', experimentId],
    queryFn: () => analysisApi.getHeatmapData(experimentId),
  });

  if (isLoading) return <LoadingSpinner text="Generando heatmap..." />;
  if (!data) return null;

  const solvers: string[] = data.solvers || [];
  const benchmarks: string[] = data.benchmarks || [];
  const matrix = data.matrix || {};
  const maxTime = data.max_time || 5000;

  const getColor = (time: number | null) => {
    if (time === null) return '#1f2937';
    if (time >= maxTime) return '#dc2626';
    const ratio = Math.log(time + 0.001) / Math.log(maxTime + 0.001);
    const clamped = Math.max(0, Math.min(1, ratio));
    if (clamped < 0.5) {
      const t = clamped * 2;
      return `rgb(${Math.round(34 + t * 211)},${Math.round(197 - t * 47)},${Math.round(94 - t * 94)})`;
    }
    const t = (clamped - 0.5) * 2;
    return `rgb(${Math.round(245 - t * 6)},${Math.round(150 - t * 82)},${Math.round(t * 10)})`;
  };

  return (
    <ChartCard
      title="Heatmap de Tiempos"
      subtitle={`${solvers.length} solvers × ${benchmarks.length} benchmarks (top 50)`}
      info="Verde = rápido, rojo = timeout/lento, gris oscuro = sin datos. Permite identificar visualmente instancias difíciles para cada solver."
    >
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          <div className="flex mb-1">
            <div className="w-52 shrink-0" />
            {solvers.map((solver) => (
              <div
                key={solver}
                className="w-24 shrink-0 text-center text-xs font-medium text-gray-400 px-1"
                style={{ writingMode: 'vertical-lr', transform: 'rotate(180deg)', height: '90px' }}
              >
                {solver}
              </div>
            ))}
          </div>

          <div className="max-h-[500px] overflow-y-auto">
            {benchmarks.map((benchmark) => (
              <div key={benchmark} className="flex items-center hover:bg-dark-700/20 transition-colors">
                <div className="w-52 shrink-0 text-xs text-gray-500 truncate pr-3 py-0.5" title={benchmark}>
                  {benchmark}
                </div>
                {solvers.map((solver) => {
                  const time = matrix[solver]?.[benchmark];
                  return (
                    <div
                      key={solver}
                      className="w-24 h-7 shrink-0 border border-dark-800 rounded-sm cursor-default"
                      style={{ backgroundColor: getColor(time) }}
                      title={`${solver}: ${time != null ? time.toFixed(4) + 's' : 'sin datos'}`}
                    />
                  );
                })}
              </div>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-4 text-xs text-gray-400">
            <span>Rápido</span>
            <div className="flex rounded overflow-hidden">
              {[0, 0.15, 0.3, 0.5, 0.7, 0.85, 1].map((ratio, i) => (
                <div key={i} className="w-8 h-4" style={{ backgroundColor: getColor(Math.pow(maxTime, ratio) * 0.001) }} />
              ))}
            </div>
            <span>Lento</span>
            <div className="w-8 h-4 bg-dark-800 border border-dark-600 rounded-sm" />
            <span>Sin datos</span>
          </div>
        </div>
      </div>
    </ChartCard>
  );
}
