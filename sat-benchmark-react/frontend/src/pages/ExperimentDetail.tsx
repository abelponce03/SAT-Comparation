import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft, 
  Clock, 
  CheckCircle2, 
  XCircle,
  AlertTriangle,
  Timer,
  Download
} from 'lucide-react';
import { experimentsApi } from '@/services/api';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import { StatusBadge, ResultBadge } from '@/components/common/Badge';

export default function ExperimentDetail() {
  const { id } = useParams();
  const experimentId = parseInt(id || '0');

  const { data: experiment, isLoading } = useQuery({
    queryKey: ['experiment', experimentId],
    queryFn: () => experimentsApi.getById(experimentId),
    refetchInterval: (query) => query.state.data?.status === 'running' ? 2000 : false,
  });

  const { data: runs } = useQuery({
    queryKey: ['experiment-runs', experimentId],
    queryFn: () => experimentsApi.getRuns(experimentId),
    refetchInterval: experiment?.status === 'running' ? 3000 : false,
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" text="Cargando experimento..." />;
  }

  if (!experiment) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">Experimento no encontrado</p>
        <Link to="/experiments" className="text-primary-600 hover:underline">
          Volver a experimentos
        </Link>
      </div>
    );
  }

  const progress = experiment.total_runs > 0 
    ? (experiment.completed_runs / experiment.total_runs * 100) 
    : 0;

  // Group runs by solver
  const runsBySolver = runs?.reduce((acc: Record<string, any[]>, run: any) => {
    const solverName = run.solver_name || 'Unknown';
    if (!acc[solverName]) acc[solverName] = [];
    acc[solverName].push(run);
    return acc;
  }, {}) || {};

  // Calculate stats
  const stats = {
    sat: runs?.filter((r: any) => r.result === 'SAT').length || 0,
    unsat: runs?.filter((r: any) => r.result === 'UNSAT').length || 0,
    timeout: runs?.filter((r: any) => r.result === 'TIMEOUT').length || 0,
    error: runs?.filter((r: any) => r.result === 'ERROR').length || 0,
    pending: runs?.filter((r: any) => r.result === 'PENDING').length || 0,
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link 
          to="/experiments" 
          className="p-2 hover:bg-dark-700 rounded-lg"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-white">{experiment.name}</h1>
            <StatusBadge status={experiment.status} />
          </div>
          {experiment.description && (
            <p className="text-gray-400 mt-1">{experiment.description}</p>
          )}
        </div>
        <button
          onClick={() => window.open(`/api/experiments/${experimentId}/export`)}
          className="btn-secondary"
        >
          <Download className="w-5 h-5 mr-2" />
          Exportar CSV
        </button>
      </div>

      {/* Progress Bar */}
      <div className="card">
        <div className="card-body">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium">Progreso</span>
            <span className="text-gray-400">
              {experiment.completed_runs} / {experiment.total_runs} ejecuciones
            </span>
          </div>
          <div className="h-4 bg-dark-600 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all ${
                experiment.status === 'completed' ? 'bg-green-500' :
                experiment.status === 'running' ? 'bg-blue-500' :
                'bg-gray-400'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-400 mt-2">
            {progress.toFixed(1)}% completado
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard 
          icon={<CheckCircle2 className="w-5 h-5 text-green-600" />}
          label="SAT"
          value={stats.sat}
          color="green"
        />
        <StatCard 
          icon={<XCircle className="w-5 h-5 text-red-600" />}
          label="UNSAT"
          value={stats.unsat}
          color="red"
        />
        <StatCard 
          icon={<Timer className="w-5 h-5 text-yellow-600" />}
          label="Timeout"
          value={stats.timeout}
          color="yellow"
        />
        <StatCard 
          icon={<AlertTriangle className="w-5 h-5 text-orange-600" />}
          label="Error"
          value={stats.error}
          color="orange"
        />
        <StatCard 
          icon={<Clock className="w-5 h-5 text-gray-400" />}
          label="Pendiente"
          value={stats.pending}
          color="gray"
        />
      </div>

      {/* Configuration */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Configuración</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-gray-400">Timeout</p>
              <p className="font-medium">{experiment.timeout_seconds}s</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Memoria</p>
              <p className="font-medium">{experiment.memory_limit_mb}MB</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Jobs paralelos</p>
              <p className="font-medium">{experiment.parallel_jobs}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Creado</p>
              <p className="font-medium">
                {new Date(experiment.created_at).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Results by Solver */}
      {Object.keys(runsBySolver).length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Resultados por Solver</h2>
          </div>
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Solver</th>
                  <th className="text-center">SAT</th>
                  <th className="text-center">UNSAT</th>
                  <th className="text-center">Timeout</th>
                  <th className="text-center">Error</th>
                  <th className="text-center">Resueltos</th>
                  <th>Tiempo promedio</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {Object.entries(runsBySolver).map(([solverName, solverRuns]) => {
                  const sat = solverRuns.filter(r => r.result === 'SAT').length;
                  const unsat = solverRuns.filter(r => r.result === 'UNSAT').length;
                  const timeout = solverRuns.filter(r => r.result === 'TIMEOUT').length;
                  const error = solverRuns.filter(r => r.result === 'ERROR').length;
                  const solved = sat + unsat;
                  const avgTime = solverRuns
                    .filter(r => r.execution_time && r.result !== 'TIMEOUT')
                    .reduce((sum, r) => sum + r.execution_time, 0) / solved || 0;

                  return (
                    <tr key={solverName}>
                      <td className="font-medium">{solverName}</td>
                      <td className="text-center text-green-600">{sat}</td>
                      <td className="text-center text-red-600">{unsat}</td>
                      <td className="text-center text-yellow-600">{timeout}</td>
                      <td className="text-center text-orange-600">{error}</td>
                      <td className="text-center font-bold">{solved}</td>
                      <td className="font-mono text-sm">
                        {avgTime.toFixed(3)}s
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* All Runs Table */}
      {runs && runs.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Todas las ejecuciones</h2>
          </div>
          <div className="overflow-x-auto max-h-96">
            <table>
              <thead className="sticky top-0 bg-white">
                <tr>
                  <th>Solver</th>
                  <th>Benchmark</th>
                  <th>Resultado</th>
                  <th>Tiempo</th>
                  <th>Memoria</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {runs.map((run: any) => (
                  <tr key={run.id}>
                    <td>{run.solver_name}</td>
                    <td className="max-w-xs truncate" title={run.benchmark_filename}>
                      {run.benchmark_filename}
                    </td>
                    <td><ResultBadge result={run.result} /></td>
                    <td className="font-mono text-sm">
                      {run.execution_time?.toFixed(3)}s
                    </td>
                    <td className="font-mono text-sm">
                      {run.memory_used_mb?.toFixed(1)}MB
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  const bgColors: Record<string, string> = {
    green: 'bg-green-50',
    red: 'bg-red-50',
    yellow: 'bg-yellow-50',
    orange: 'bg-orange-50',
    gray: 'bg-dark-800',
  };

  return (
    <div className={`rounded-lg p-4 ${bgColors[color]}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
