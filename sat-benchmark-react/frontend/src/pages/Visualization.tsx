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
  ReferenceLine
} from 'recharts';
import { 
  BarChart3, 
  ScatterChart as ScatterIcon,
  TrendingUp,
  Thermometer
} from 'lucide-react';
import { analysisApi, experimentsApi } from '@/services/api';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import EmptyState from '@/components/common/EmptyState';

type ChartType = 'cactus' | 'scatter' | 'ecdf' | 'heatmap';

// Colors for different solvers
const SOLVER_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#10b981', // green
  '#f59e0b', // yellow
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
];

export default function Visualization() {
  const [selectedExperiment, setSelectedExperiment] = useState<number | null>(null);
  const [chartType, setChartType] = useState<ChartType>('cactus');
  const [timeout, setTimeout] = useState(5000);

  // Queries
  const { data: experiments } = useQuery({
    queryKey: ['experiments', 'completed'],
    queryFn: () => experimentsApi.getAll('completed'),
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

  const chartTabs = [
    { id: 'cactus' as const, label: 'Cactus Plot', icon: TrendingUp },
    { id: 'scatter' as const, label: 'Scatter Plot', icon: ScatterIcon },
    { id: 'ecdf' as const, label: 'ECDF / Performance Profile', icon: BarChart3 },
    { id: 'heatmap' as const, label: 'Heatmap', icon: Thermometer },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Visualización</h1>
        <p className="text-gray-400 mt-1">
          Gráficos comparativos de rendimiento
        </p>
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
                {experiments?.map((exp) => (
                  <option key={exp.id} value={exp.id}>
                    {exp.name} ({exp.completed_runs} ejecuciones)
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
          description="Elige un experimento completado para visualizar los resultados"
          icon={<BarChart3 className="w-6 h-6 text-gray-400" />}
        />
      ) : (
        <>
          {/* Chart Type Tabs */}
          <div className="border-b border-dark-700">
            <nav className="flex gap-4">
              {chartTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setChartType(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                    chartType === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-400 hover:text-gray-300'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Chart Content */}
          <div className="mt-6">
            {chartType === 'cactus' && (
              <CactusPlot 
                data={cactusData} 
                isLoading={cactusLoading} 
                timeout={timeout}
              />
            )}
            {chartType === 'scatter' && (
              <ScatterPlot 
                data={scatterData} 
                isLoading={scatterLoading}
                timeout={timeout}
              />
            )}
            {chartType === 'ecdf' && (
              <ECDFPlot 
                data={ecdfData} 
                isLoading={ecdfLoading}
              />
            )}
            {chartType === 'heatmap' && (
              <HeatmapPlot 
                experimentId={selectedExperiment}
              />
            )}
          </div>
        </>
      )}
    </div>
  );
}

// Cactus Plot Component
function CactusPlot({ data, isLoading, timeout }: {
  data: any;
  isLoading: boolean;
  timeout: number;
}) {
  if (isLoading) return <LoadingSpinner text="Generando cactus plot..." />;
  if (!data) return null;

  const solvers = Object.keys(data.solvers || {});
  
  // Transform data for Recharts
  const chartData = useMemo(() => {
    if (!data.solvers) return [];
    
    const maxInstances = Math.max(
      ...solvers.map(s => data.solvers[s]?.length || 0)
    );
    
    return Array.from({ length: maxInstances }, (_, i) => {
      const point: any = { instance: i + 1 };
      solvers.forEach(solver => {
        const times = data.solvers[solver] || [];
        point[solver] = times[i] ?? null;
      });
      return point;
    });
  }, [data, solvers]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Cactus Plot</h3>
          <p className="text-sm text-gray-400">
            Instancias resueltas vs tiempo acumulado
          </p>
        </div>
        <div className="card-body">
          <div className="h-[500px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="instance" 
                  label={{ value: 'Instancias resueltas', position: 'bottom' }}
                />
                <YAxis 
                  scale="log"
                  domain={[0.001, timeout]}
                  label={{ value: 'Tiempo (s)', angle: -90, position: 'left' }}
                />
                <Tooltip 
                  formatter={(value: any) => [`${value?.toFixed(3)}s`, '']}
                />
                <Legend />
                <ReferenceLine 
                  y={timeout} 
                  stroke="#ef4444" 
                  strokeDasharray="5 5" 
                  label="Timeout" 
                />
                {solvers.map((solver, i) => (
                  <Line
                    key={solver}
                    type="stepAfter"
                    dataKey={solver}
                    stroke={SOLVER_COLORS[i % SOLVER_COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-800">Interpretación</h4>
        <p className="text-sm text-blue-700 mt-1">
          Un solver es mejor si su curva está más a la derecha y más abajo. 
          Esto indica que resuelve más instancias en menos tiempo.
        </p>
      </div>
    </div>
  );
}

// Scatter Plot Component
function ScatterPlot({ data, isLoading, timeout }: {
  data: any;
  isLoading: boolean;
  timeout: number;
}) {
  const [solver1, setSolver1] = useState('');
  const [solver2, setSolver2] = useState('');

  const solvers = useMemo(() => data?.solvers || [], [data]);

  // Auto-select first two solvers
  useMemo(() => {
    if (solvers.length >= 2) {
      if (!solver1) setSolver1(solvers[0]);
      if (!solver2) setSolver2(solvers[1]);
    }
  }, [solvers, solver1, solver2]);

  const chartData = useMemo(() => {
    if (!data?.points || !solver1 || !solver2) return [];
    
    return data.points
      .filter((p: any) => p.solver1 === solver1 && p.solver2 === solver2)
      .map((p: any) => ({
        x: p.time1,
        y: p.time2,
        benchmark: p.benchmark,
      }));
  }, [data, solver1, solver2]);

  if (isLoading) return <LoadingSpinner text="Generando scatter plot..." />;
  if (!data) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Solver Selection */}
      <div className="card">
        <div className="card-body">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Solver X (horizontal)</label>
              <select
                value={solver1}
                onChange={(e) => setSolver1(e.target.value)}
                className="input"
              >
                {solvers.map((s: string) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Solver Y (vertical)</label>
              <select
                value={solver2}
                onChange={(e) => setSolver2(e.target.value)}
                className="input"
              >
                {solvers.map((s: string) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Scatter Plot */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Scatter Plot: {solver1} vs {solver2}</h3>
        </div>
        <div className="card-body">
          <div className="h-[500px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  type="number" 
                  dataKey="x" 
                  name={solver1}
                  scale="log"
                  domain={[0.001, timeout]}
                  label={{ value: solver1, position: 'bottom' }}
                />
                <YAxis 
                  type="number" 
                  dataKey="y" 
                  name={solver2}
                  scale="log"
                  domain={[0.001, timeout]}
                  label={{ value: solver2, angle: -90, position: 'left' }}
                />
                <Tooltip 
                  formatter={(value: any, name: string) => [`${value?.toFixed(3)}s`, name]}
                  labelFormatter={(_, payload: any) => payload[0]?.payload?.benchmark || ''}
                />
                <ReferenceLine 
                  segment={[{ x: 0.001, y: 0.001 }, { x: timeout, y: timeout }]} 
                  stroke="#9ca3af" 
                  strokeDasharray="5 5"
                />
                <Scatter data={chartData} fill="#3b82f6">
                  {chartData.map((entry: any, index: number) => (
                    <Cell 
                      key={index}
                      fill={entry.x < entry.y ? '#10b981' : entry.x > entry.y ? '#ef4444' : '#9ca3af'}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <h4 className="font-medium text-green-800">Interpretación</h4>
        <p className="text-sm text-green-700 mt-1">
          Puntos <span className="text-green-600 font-medium">verdes</span> debajo de la diagonal: {solver1} es más rápido. 
          Puntos <span className="text-red-600 font-medium">rojos</span> arriba de la diagonal: {solver2} es más rápido.
        </p>
      </div>
    </div>
  );
}

// ECDF / Performance Profile Component
function ECDFPlot({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) return <LoadingSpinner text="Generando ECDF..." />;
  if (!data) return null;

  const solvers = Object.keys(data.profiles || {});

  const chartData = useMemo(() => {
    if (!data.profiles) return [];
    
    const allRatios = new Set<number>();
    solvers.forEach(s => {
      data.profiles[s]?.forEach((p: any) => allRatios.add(p.ratio));
    });
    
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

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Performance Profile (ECDF)</h3>
          <p className="text-sm text-gray-400">
            Probabilidad de resolver dentro de un factor τ del mejor solver
          </p>
        </div>
        <div className="card-body">
          <div className="h-[500px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="ratio"
                  scale="log"
                  domain={[1, 'auto']}
                  label={{ value: 'Factor τ (ratio al mejor)', position: 'bottom' }}
                />
                <YAxis 
                  domain={[0, 1]}
                  label={{ value: 'P(ratio ≤ τ)', angle: -90, position: 'left' }}
                />
                <Tooltip 
                  formatter={(value: any) => [(value * 100).toFixed(1) + '%', '']}
                />
                <Legend />
                {solvers.map((solver, i) => (
                  <Line
                    key={solver}
                    type="stepAfter"
                    dataKey={solver}
                    stroke={SOLVER_COLORS[i % SOLVER_COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <h4 className="font-medium text-purple-800">Interpretación</h4>
        <p className="text-sm text-purple-700 mt-1">
          Curvas más altas y a la izquierda indican mejor rendimiento. 
          En τ=1, el valor muestra qué porcentaje de instancias el solver es el más rápido.
        </p>
      </div>
    </div>
  );
}

// Heatmap Component
function HeatmapPlot({ experimentId }: { experimentId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['visualization', 'heatmap', experimentId],
    queryFn: () => analysisApi.getHeatmapData(experimentId),
  });

  if (isLoading) return <LoadingSpinner text="Generando heatmap..." />;
  if (!data) return null;

  const solvers = data.solvers || [];
  const benchmarks = data.benchmarks || [];
  const matrix = data.matrix || {};

  // Get color based on time
  const getColor = (time: number | null, maxTime: number) => {
    if (time === null) return '#f3f4f6'; // gray for no data
    if (time >= maxTime) return '#ef4444'; // red for timeout
    
    const ratio = Math.log(time + 1) / Math.log(maxTime + 1);
    const r = Math.round(34 + ratio * (239 - 34));
    const g = Math.round(197 - ratio * (197 - 68));
    const b = Math.round(94 - ratio * 94);
    return `rgb(${r},${g},${b})`;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Heatmap de Tiempos</h3>
          <p className="text-sm text-gray-400">
            Tiempos de ejecución por solver y benchmark
          </p>
        </div>
        <div className="card-body overflow-x-auto">
          <div className="inline-block min-w-full">
            <div className="flex">
              {/* Solver headers */}
              <div className="w-48 shrink-0"></div>
              {solvers.map((solver: string) => (
                <div 
                  key={solver}
                  className="w-20 shrink-0 text-center text-xs font-medium text-gray-400 px-1"
                  style={{ writingMode: 'vertical-lr', transform: 'rotate(180deg)', height: '100px' }}
                >
                  {solver}
                </div>
              ))}
            </div>
            
            {/* Benchmark rows */}
            <div className="max-h-[500px] overflow-y-auto">
              {benchmarks.slice(0, 50).map((benchmark: string) => (
                <div key={benchmark} className="flex items-center">
                  <div className="w-48 shrink-0 text-xs text-gray-400 truncate pr-2" title={benchmark}>
                    {benchmark}
                  </div>
                  {solvers.map((solver: string) => {
                    const time = matrix[solver]?.[benchmark];
                    return (
                      <div
                        key={solver}
                        className="w-20 h-6 shrink-0 border border-dark-700"
                        style={{ backgroundColor: getColor(time, data.max_time) }}
                        title={`${solver}: ${time?.toFixed(3)}s`}
                      />
                    );
                  })}
                </div>
              ))}
            </div>

            {/* Legend */}
            <div className="mt-4 flex items-center gap-4">
              <span className="text-sm text-gray-400">Rápido</span>
              <div className="flex">
                {[0, 0.2, 0.4, 0.6, 0.8, 1].map((ratio, i) => (
                  <div
                    key={i}
                    className="w-8 h-4"
                    style={{ 
                      backgroundColor: `rgb(${Math.round(34 + ratio * 205)},${Math.round(197 - ratio * 129)},${Math.round(94 - ratio * 94)})`
                    }}
                  />
                ))}
              </div>
              <span className="text-sm text-gray-400">Lento/Timeout</span>
              <div className="w-8 h-4 bg-dark-600 border border-gray-300" />
              <span className="text-sm text-gray-400">Sin datos</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
