import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { 
  Cpu, 
  FileText, 
  FlaskConical, 
  PlayCircle,
  CheckCircle2,
  Clock,
  AlertCircle,
  ArrowRight,
  TrendingUp,
  BarChart3,
  LineChart,
  Zap,
  Target,
  Shield,
  Award,
  Activity,
  Database,
  GitBranch,
  ChevronRight
} from 'lucide-react';
import { dashboardApi } from '@/services/api';
import LoadingSpinner from '@/components/common/LoadingSpinner';

// Pipeline stages configuration
const pipelineStages = [
  {
    id: 'solvers',
    title: 'Solvers Disponibles',
    description: 'Kissat y MiniSat pre-configurados y listos',
    icon: Cpu,
    href: '/solvers',
    color: 'from-violet-600 to-purple-600',
    bgColor: 'bg-violet-600/10',
    borderColor: 'border-violet-600/30',
  },
  {
    id: 'benchmarks',
    title: 'Cargar Benchmarks',
    description: 'Importa instancias CNF para el análisis',
    icon: FileText,
    href: '/benchmarks',
    color: 'from-fuchsia-600 to-pink-600',
    bgColor: 'bg-fuchsia-600/10',
    borderColor: 'border-fuchsia-600/30',
  },
  {
    id: 'experiments',
    title: 'Ejecutar Experimentos',
    description: 'Configura y ejecuta las pruebas de rendimiento',
    icon: FlaskConical,
    href: '/experiments',
    color: 'from-purple-600 to-indigo-600',
    bgColor: 'bg-purple-600/10',
    borderColor: 'border-purple-600/30',
  },
  {
    id: 'analysis',
    title: 'Analizar Resultados',
    description: 'Métricas PAR2, VBS y comparativas estadísticas',
    icon: BarChart3,
    href: '/analysis',
    color: 'from-indigo-600 to-blue-600',
    bgColor: 'bg-indigo-600/10',
    borderColor: 'border-indigo-600/30',
  },
  {
    id: 'visualization',
    title: 'Visualizar Datos',
    description: 'Gráficos cactus, scatter y análisis visual',
    icon: LineChart,
    href: '/visualization',
    color: 'from-blue-600 to-cyan-600',
    bgColor: 'bg-blue-600/10',
    borderColor: 'border-blue-600/30',
  },
];

// Theoretical rigor tests
const rigorTests = [
  {
    id: 'par2',
    title: 'PAR2 Score',
    description: 'Penalized Average Runtime con factor 2 para timeouts',
    formula: 'PAR2 = Σ(tᵢ) + 2·T·|timeouts|',
    icon: Target,
  },
  {
    id: 'vbs',
    title: 'Virtual Best Solver',
    description: 'Mejor tiempo hipotético seleccionando el solver óptimo por instancia',
    formula: 'VBS(i) = min{tₛ(i) : s ∈ Solvers}',
    icon: Award,
  },
  {
    id: 'pairwise',
    title: 'Comparación Pairwise',
    description: 'Análisis directo entre pares de solvers',
    formula: 'W(A,B) = |{i : tₐ(i) < tᵦ(i)}|',
    icon: GitBranch,
  },
  {
    id: 'statistical',
    title: 'Tests Estadísticos',
    description: 'Wilcoxon, Mann-Whitney U, análisis de varianza',
    formula: 'H₀: μₐ = μᵦ vs H₁: μₐ ≠ μᵦ',
    icon: Activity,
  },
];

export default function Dashboard() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" text="Inicializando sistema..." />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
        <div className="w-16 h-16 rounded-full bg-red-600/10 flex items-center justify-center mb-4">
          <AlertCircle className="w-8 h-8 text-red-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">Error de conexión</h2>
        <p className="text-gray-400 mt-2">No se pudo conectar con el servidor backend</p>
      </div>
    );
  }

  const totalSolved = (stats?.sat_results || 0) + (stats?.unsat_results || 0);
  const solvedRate = stats?.total_runs 
    ? ((totalSolved / stats.total_runs) * 100).toFixed(1) 
    : '0';

  // Determine pipeline progress
  const getPipelineStatus = (stageId: string) => {
    switch (stageId) {
      case 'solvers':
        return (stats?.ready_solvers || 0) > 0 ? 'completed' : 'active';
      case 'benchmarks':
        return (stats?.total_benchmarks || 0) > 0 ? 'completed' : 
               (stats?.ready_solvers || 0) > 0 ? 'active' : 'pending';
      case 'experiments':
        return (stats?.total_experiments || 0) > 0 ? 'completed' :
               (stats?.total_benchmarks || 0) > 0 ? 'active' : 'pending';
      case 'analysis':
        return (stats?.completed_experiments || 0) > 0 ? 'completed' :
               (stats?.total_experiments || 0) > 0 ? 'active' : 'pending';
      case 'visualization':
        return (stats?.completed_experiments || 0) > 0 ? 'active' : 'pending';
      default:
        return 'pending';
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-dark-900 via-dark-800 to-dark-900 border border-dark-700/50 p-8 animate-fade-in">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiM4YjVjZjYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
        <div className="relative">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-600 to-accent-600 flex items-center justify-center shadow-lg shadow-primary-600/30">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">SAT Benchmark Suite</h1>
              <p className="text-gray-400">Sistema de Evaluación Comparativa de Solvers SAT</p>
            </div>
          </div>
          
          {/* Quick Stats Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <QuickStat 
              label="Solvers Activos" 
              value={stats?.ready_solvers || 0}
              total={stats?.total_solvers || 0}
              icon={Cpu}
            />
            <QuickStat 
              label="Benchmarks" 
              value={stats?.total_benchmarks || 0}
              icon={Database}
            />
            <QuickStat 
              label="Experimentos" 
              value={stats?.completed_experiments || 0}
              total={stats?.total_experiments || 0}
              icon={FlaskConical}
            />
            <QuickStat 
              label="Tasa Solución" 
              value={`${solvedRate}%`}
              icon={TrendingUp}
            />
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Pipeline Section - Left 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-primary-400" />
              Pipeline de Trabajo
            </h2>
            <span className="text-sm text-gray-500">
              {pipelineStages.filter(s => getPipelineStatus(s.id) === 'completed').length} / {pipelineStages.length} completados
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pipelineStages.map((stage, index) => (
              <PipelineCard 
                key={stage.id}
                stage={stage}
                status={getPipelineStatus(stage.id)}
                index={index}
              />
            ))}
          </div>
        </div>

        {/* Rigor Tests Section - Right column */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary-400" />
            Rigurosidad Teórica
          </h2>
          
          <div className="space-y-3">
            {rigorTests.map((test, index) => (
              <RigorTestCard key={test.id} test={test} index={index} />
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity & Status Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Status */}
        <div className="card animate-fade-in-up" style={{ animationDelay: '300ms' }}>
          <div className="card-header border-dark-700/50">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary-400" />
              Estado del Sistema
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <SystemStatusRow 
                label="Servidor Backend" 
                status="online" 
                detail="FastAPI v0.104" 
              />
              <SystemStatusRow 
                label="Base de Datos" 
                status="online" 
                detail="SQLite" 
              />
              <SystemStatusRow 
                label="Procesador de Jobs" 
                status={stats?.running_experiments ? 'busy' : 'idle'} 
                detail={stats?.running_experiments ? `${stats.running_experiments} en ejecución` : 'Esperando tareas'} 
              />
            </div>
          </div>
        </div>

        {/* Results Overview */}
        <div className="card animate-fade-in-up" style={{ animationDelay: '400ms' }}>
          <div className="card-header border-dark-700/50">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary-400" />
              Resumen de Resultados
            </h3>
          </div>
          <div className="card-body">
            {stats?.total_runs ? (
              <div className="space-y-4">
                <ResultBar label="SAT" value={stats?.sat_results || 0} total={stats.total_runs} color="bg-green-500" />
                <ResultBar label="UNSAT" value={stats?.unsat_results || 0} total={stats.total_runs} color="bg-blue-500" />
                <ResultBar label="TIMEOUT" value={stats?.timeout_results || 0} total={stats.total_runs} color="bg-yellow-500" />
                <ResultBar label="ERROR" value={stats?.error_results || 0} total={stats.total_runs} color="bg-red-500" />
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">No hay resultados disponibles</p>
                <Link to="/experiments" className="text-primary-400 text-sm hover:underline mt-2 inline-block">
                  Crear primer experimento →
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Quick Stat Component
function QuickStat({ 
  label, 
  value, 
  total, 
  icon: Icon 
}: { 
  label: string; 
  value: number | string; 
  total?: number;
  icon: React.ElementType;
}) {
  return (
    <div className="bg-dark-800/50 rounded-xl p-4 border border-dark-700/30">
      <div className="flex items-center gap-3">
        <Icon className="w-5 h-5 text-primary-400" />
        <div>
          <div className="text-2xl font-bold text-white">
            {value}
            {total !== undefined && <span className="text-gray-500 text-sm font-normal">/{total}</span>}
          </div>
          <div className="text-xs text-gray-500">{label}</div>
        </div>
      </div>
    </div>
  );
}

// Pipeline Card Component
function PipelineCard({ 
  stage, 
  status,
  index 
}: { 
  stage: typeof pipelineStages[0];
  status: 'pending' | 'active' | 'completed';
  index: number;
}) {
  const Icon = stage.icon;
  
  return (
    <Link 
      to={stage.href}
      className="module-card animate-fade-in-up group"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="module-card-header">
        <div className="flex items-start justify-between">
          <div className={`module-icon ${stage.bgColor} border ${stage.borderColor}`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <StatusIndicator status={status} />
        </div>
        <h3 className="text-lg font-semibold text-white mt-4 group-hover:text-primary-300 transition-colors">
          {stage.title}
        </h3>
        <p className="text-sm text-gray-400 mt-1">{stage.description}</p>
      </div>
      <div className="px-6 py-4 bg-dark-900/50 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {status === 'completed' ? 'Completado' : status === 'active' ? 'Disponible' : 'Pendiente'}
        </span>
        <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-primary-400 group-hover:translate-x-1 transition-all" />
      </div>
    </Link>
  );
}

// Status Indicator Component
function StatusIndicator({ status }: { status: 'pending' | 'active' | 'completed' }) {
  if (status === 'completed') {
    return (
      <div className="w-6 h-6 rounded-full bg-green-600/20 flex items-center justify-center">
        <CheckCircle2 className="w-4 h-4 text-green-400" />
      </div>
    );
  }
  if (status === 'active') {
    return (
      <div className="w-6 h-6 rounded-full bg-primary-600/20 flex items-center justify-center animate-pulse-slow">
        <div className="w-2 h-2 rounded-full bg-primary-400" />
      </div>
    );
  }
  return (
    <div className="w-6 h-6 rounded-full bg-dark-700 flex items-center justify-center">
      <Clock className="w-3 h-3 text-gray-500" />
    </div>
  );
}

// Rigor Test Card Component
function RigorTestCard({ test, index }: { test: typeof rigorTests[0]; index: number }) {
  const Icon = test.icon;
  
  return (
    <div 
      className="card p-4 animate-fade-in-up hover:border-primary-600/30 transition-colors"
      style={{ animationDelay: `${index * 100 + 200}ms` }}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary-600/10 border border-primary-600/30 flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-primary-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white">{test.title}</h4>
          <p className="text-xs text-gray-500 mt-0.5">{test.description}</p>
          <code className="text-xs text-primary-300 font-mono mt-2 block bg-dark-800 px-2 py-1 rounded">
            {test.formula}
          </code>
        </div>
      </div>
    </div>
  );
}

// System Status Row Component
function SystemStatusRow({ 
  label, 
  status, 
  detail 
}: { 
  label: string; 
  status: 'online' | 'offline' | 'busy' | 'idle'; 
  detail: string;
}) {
  const statusColors = {
    online: 'bg-green-500',
    offline: 'bg-red-500',
    busy: 'bg-yellow-500 animate-pulse',
    idle: 'bg-gray-500',
  };
  
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full ${statusColors[status]}`} />
        <span className="text-gray-300">{label}</span>
      </div>
      <span className="text-sm text-gray-500">{detail}</span>
    </div>
  );
}

// Result Bar Component
function ResultBar({ 
  label, 
  value, 
  total, 
  color 
}: { 
  label: string; 
  value: number; 
  total: number; 
  color: string;
}) {
  const percentage = total > 0 ? (value / total) * 100 : 0;
  
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-white font-mono">{value} <span className="text-gray-600">({percentage.toFixed(1)}%)</span></span>
      </div>
      <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} rounded-full transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
