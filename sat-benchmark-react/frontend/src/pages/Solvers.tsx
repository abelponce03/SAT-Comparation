import { useQuery, useQueryClient } from '@tanstack/react-query';
import { 
  Cpu, 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink,
  Zap,
  BookOpen,
  Trophy,
  ChevronRight,
  Play,
  Loader2,
  Download,
  Trash2,
  RefreshCw
} from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { solversApi } from '@/services/api';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import { StatusBadge } from '@/components/common/Badge';

interface Solver {
  id: number;
  key?: string;
  name: string;
  version: string;
  description: string;
  executable_path: string;
  status: string;
  features: string[];
  website: string;
  category: string;
}

interface ComparisonSolver {
  name: string;
  type: string;
  preprocessing: boolean;
  inprocessing: boolean;
  parallel: boolean;
  incremental: boolean;
  best_for: string[];
  performance_class: string;
}

export default function Solvers() {
  const queryClient = useQueryClient();

  // Queries
  const { data: solvers, isLoading: loadingSolvers } = useQuery({
    queryKey: ['solvers'],
    queryFn: () => solversApi.getAll(),
  });

  const { data: comparison } = useQuery({
    queryKey: ['solver-comparison'],
    queryFn: () => solversApi.getComparison(),
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => solversApi.test(id),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(`${data.solver_name} funcionando correctamente`);
      } else {
        toast.error(`Error: ${data.error}`);
      }
    },
    onError: () => toast.error('Error al probar solver'),
  });

  const installMutation = useMutation({
    mutationFn: (solverKey: string) => solversApi.install(solverKey),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || 'Solver instalado correctamente');
        queryClient.invalidateQueries({ queryKey: ['solvers'] });
        queryClient.invalidateQueries({ queryKey: ['solver-comparison'] });
      } else {
        toast.error(data.error || data.message || 'Error al instalar solver');
      }
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Error al instalar solver'),
  });

  const uninstallMutation = useMutation({
    mutationFn: (solverKey: string) => solversApi.uninstall(solverKey),
    onSuccess: () => {
      toast.success('Solver desinstalado');
      queryClient.invalidateQueries({ queryKey: ['solvers'] });
      queryClient.invalidateQueries({ queryKey: ['solver-comparison'] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Error al desinstalar'),
  });

  if (loadingSolvers) {
    return <LoadingSpinner size="lg" text="Cargando solvers..." />;
  }

  const readySolvers = solvers?.filter((s: Solver) => s.status === 'ready') || [];
  const unavailableSolvers = solvers?.filter((s: Solver) => s.status !== 'ready') || [];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <div className="p-2 bg-primary-600/20 rounded-xl border border-primary-600/30">
              <Cpu className="w-8 h-8 text-primary-400" />
            </div>
            SAT Solvers
          </h1>
          <p className="text-gray-400 mt-2">
            Sistema de plugins dinámico — instala y gestiona solvers SAT
          </p>
        </div>
        
        {/* Stats */}
        <div className="flex gap-4">
          <div className="bg-dark-800/50 border border-green-600/30 rounded-xl px-4 py-3 text-center">
            <div className="text-2xl font-bold text-green-400">{readySolvers.length}</div>
            <div className="text-xs text-gray-400">Disponibles</div>
          </div>
          <div className="bg-dark-800/50 border border-gray-600/30 rounded-xl px-4 py-3 text-center">
            <div className="text-2xl font-bold text-gray-400">{unavailableSolvers.length}</div>
            <div className="text-xs text-gray-400">No disponibles</div>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-gradient-to-r from-primary-900/30 to-purple-900/30 border border-primary-600/30 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-primary-600/20 rounded-lg">
            <BookOpen className="w-6 h-6 text-primary-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">Sistema de Plugins de Solvers</h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              Los solvers se gestionan mediante un sistema de plugins dinámico.
              Puedes instalar nuevos solvers directamente desde la interfaz con un solo clic.
              Los solvers no instalados pueden compilarse automáticamente desde su código fuente.
              Para añadir un solver personalizado, crea un archivo plugin en <code className="text-primary-300">app/solvers/plugins/</code>.
            </p>
          </div>
        </div>
      </div>

      {/* Solvers Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {solvers?.map((solver: Solver) => (
          <SolverCard 
            key={solver.id} 
            solver={solver}
            onTest={() => testMutation.mutate(solver.id)}
            isTestLoading={testMutation.isPending}
            onInstall={() => solver.key && installMutation.mutate(solver.key)}
            isInstalling={installMutation.isPending}
            onUninstall={() => solver.key && uninstallMutation.mutate(solver.key)}
            isUninstalling={uninstallMutation.isPending}
          />
        ))}
      </div>

      {/* Comparison Matrix */}
      {comparison && (
        <div className="mt-8">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-400" />
            Matriz de Comparación
          </h2>
          
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-dark-900/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">Solver</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">Tipo</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-300">Preprocessing</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-300">Inprocessing</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-300">Paralelo</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-300">Incremental</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">Ideal para</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-700">
                  {comparison.solvers.map((solver: ComparisonSolver) => (
                    <tr key={solver.name} className="hover:bg-dark-700/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-white">{solver.name}</div>
                        <div className="text-xs text-gray-500">{solver.performance_class}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-400">{solver.type}</td>
                      <td className="px-4 py-3 text-center">
                        {solver.preprocessing ? (
                          <CheckCircle2 className="w-5 h-5 text-green-400 mx-auto" />
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {solver.inprocessing ? (
                          <CheckCircle2 className="w-5 h-5 text-green-400 mx-auto" />
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {solver.parallel ? (
                          <CheckCircle2 className="w-5 h-5 text-green-400 mx-auto" />
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {solver.incremental ? (
                          <CheckCircle2 className="w-5 h-5 text-green-400 mx-auto" />
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {solver.best_for.map((use: string) => (
                            <span 
                              key={use}
                              className="px-2 py-0.5 bg-primary-600/20 text-primary-300 text-xs rounded-full"
                            >
                              {use}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Legend */}
            <div className="px-4 py-3 bg-dark-900/30 border-t border-dark-700">
              <h4 className="text-xs font-semibold text-gray-400 mb-2">Leyenda</h4>
              <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                {comparison.legend && Object.entries(comparison.legend).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-gray-400">{key}:</span> {value as string}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detailed Features Comparison */}
      {comparison?.features_comparison && (
        <div className="mt-8">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-400" />
            Comparación Detallada de Técnicas
          </h2>
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-dark-900/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">Técnica</th>
                    {Object.keys(comparison.features_comparison).map((name: string) => (
                      <th key={name} className="px-4 py-3 text-center text-sm font-semibold text-gray-300">
                        {name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-700">
                  {(() => {
                    const solverNames = Object.keys(comparison.features_comparison);
                    const featureKeys = solverNames.length > 0
                      ? Object.keys(comparison.features_comparison[solverNames[0]])
                      : [];
                    return featureKeys.map((feat: string) => (
                      <tr key={feat} className="hover:bg-dark-700/30 transition-colors">
                        <td className="px-4 py-2.5 text-sm text-gray-300 font-medium">
                          {feat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </td>
                        {solverNames.map((sName: string) => (
                          <td key={sName} className="px-4 py-2.5 text-center">
                            {comparison.features_comparison[sName][feat] ? (
                              <CheckCircle2 className="w-4 h-4 text-green-400 mx-auto" />
                            ) : (
                              <span className="text-gray-600">—</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ));
                  })()}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* CDCL Algorithm Info */}
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-400" />
          Algoritmo CDCL (Conflict-Driven Clause Learning)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <p className="text-gray-400 text-sm leading-relaxed">
              CDCL es el algoritmo base de los SAT solvers modernos. Mejora significativamente 
              el algoritmo DPLL original mediante el aprendizaje de cláusulas de conflicto.
            </p>
            <ul className="text-gray-400 text-sm space-y-2">
              <li className="flex items-start gap-2">
                <ChevronRight className="w-4 h-4 text-primary-400 mt-0.5 flex-shrink-0" />
                <span><strong className="text-white">Unit Propagation:</strong> Propaga asignaciones forzadas</span>
              </li>
              <li className="flex items-start gap-2">
                <ChevronRight className="w-4 h-4 text-primary-400 mt-0.5 flex-shrink-0" />
                <span><strong className="text-white">Conflict Analysis:</strong> Analiza conflictos para backtrack inteligente</span>
              </li>
              <li className="flex items-start gap-2">
                <ChevronRight className="w-4 h-4 text-primary-400 mt-0.5 flex-shrink-0" />
                <span><strong className="text-white">Clause Learning:</strong> Aprende cláusulas para evitar conflictos futuros</span>
              </li>
            </ul>
          </div>
          <div className="bg-dark-900/50 rounded-lg p-4 font-mono text-sm">
            <div className="text-gray-500 mb-2">// Pseudocódigo CDCL</div>
            <pre className="text-gray-300 whitespace-pre-wrap">
{`while (!allAssigned) {
  propagate();
  if (conflict) {
    if (level == 0) return UNSAT;
    clause = analyze(conflict);
    learn(clause);
    backtrack(level);
  } else {
    decide();
  }
}
return SAT;`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}

// Solver Card Component
function SolverCard({ 
  solver,
  onTest,
  isTestLoading,
  onInstall,
  isInstalling,
  onUninstall,
  isUninstalling
}: { 
  solver: Solver;
  onTest: () => void;
  isTestLoading: boolean;
  onInstall: () => void;
  isInstalling: boolean;
  onUninstall: () => void;
  isUninstalling: boolean;
}) {
  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'competition':
        return <Trophy className="w-5 h-5 text-yellow-400" />;
      case 'educational':
        return <BookOpen className="w-5 h-5 text-blue-400" />;
      default:
        return <Cpu className="w-5 h-5 text-primary-400" />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'competition':
        return 'from-yellow-900/30 to-orange-900/30 border-yellow-600/30';
      case 'educational':
        return 'from-blue-900/30 to-cyan-900/30 border-blue-600/30';
      default:
        return 'from-primary-900/30 to-purple-900/30 border-primary-600/30';
    }
  };

  return (
    <div className={`bg-gradient-to-br ${getCategoryColor(solver.category)} border rounded-xl p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-lg`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-dark-900/50 rounded-lg border border-dark-700">
            {getCategoryIcon(solver.category)}
          </div>
          <div>
            <h3 className="text-xl font-bold text-white">{solver.name}</h3>
            <p className="text-sm text-gray-400">v{solver.version}</p>
          </div>
        </div>
        <StatusBadge status={solver.status} />
      </div>

      {/* Description */}
      <p className="text-gray-400 text-sm mb-4 leading-relaxed">
        {solver.description}
      </p>

      {/* Features */}
      <div className="mb-4">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Características
        </h4>
        <div className="flex flex-wrap gap-2">
          {solver.features.map((feature) => (
            <span 
              key={feature}
              className="px-2 py-1 bg-dark-900/50 border border-dark-600 text-gray-300 text-xs rounded-md"
            >
              {feature}
            </span>
          ))}
        </div>
      </div>

      {/* Status & Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-dark-700/50">
        <div className="flex items-center gap-2">
          {solver.status === 'ready' ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-sm text-green-400">Listo para usar</span>
            </>
          ) : solver.status === 'not_installed' ? (
            <>
              <Download className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-blue-400">Disponible para instalar</span>
            </>
          ) : solver.status === 'installing' ? (
            <>
              <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
              <span className="text-sm text-yellow-400">Instalando...</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-yellow-400">No disponible</span>
            </>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {/* Install button — shown when solver is not installed */}
          {(solver.status === 'not_installed' || solver.status === 'error' || solver.status === 'unavailable') && solver.key && (
            <button
              onClick={onInstall}
              disabled={isInstalling}
              className="px-3 py-1.5 bg-green-900/50 border border-green-600/50 text-green-300 text-sm rounded-lg hover:bg-green-800/50 transition-colors flex items-center gap-2"
            >
              {isInstalling ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              {isInstalling ? 'Instalando...' : 'Instalar'}
            </button>
          )}

          {/* Test button — shown when ready */}
          {solver.status === 'ready' && (
            <button
              onClick={onTest}
              disabled={isTestLoading}
              className="px-3 py-1.5 bg-dark-900/50 border border-dark-600 text-gray-300 text-sm rounded-lg hover:bg-dark-700 transition-colors flex items-center gap-2"
            >
              {isTestLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Probar
            </button>
          )}

          <a
            href={solver.website}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 bg-dark-900/50 border border-dark-600 text-gray-300 text-sm rounded-lg hover:bg-dark-700 transition-colors flex items-center gap-2"
          >
            <ExternalLink className="w-4 h-4" />
            Web
          </a>
        </div>
      </div>
    </div>
  );
}
