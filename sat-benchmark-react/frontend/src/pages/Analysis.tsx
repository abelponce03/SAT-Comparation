import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  BarChart3, 
  Table2, 
  Trophy,
  Scale,
  Download
} from 'lucide-react';
import { analysisApi, experimentsApi } from '@/services/api';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import Badge from '@/components/common/Badge';
import EmptyState from '@/components/common/EmptyState';

type AnalysisTab = 'par2' | 'vbs' | 'pairwise' | 'families';

export default function Analysis() {
  const [selectedExperiment, setSelectedExperiment] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<AnalysisTab>('par2');
  const [timeout, setTimeout] = useState(5000);

  // Queries
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

  const tabs = [
    { id: 'par2' as const, label: 'PAR-2 Score', icon: BarChart3 },
    { id: 'vbs' as const, label: 'Virtual Best Solver', icon: Trophy },
    { id: 'pairwise' as const, label: 'Comparación Pares', icon: Scale },
    { id: 'families' as const, label: 'Por Familia', icon: Table2 },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Análisis Estadístico</h1>
        <p className="text-gray-400 mt-1">
          PAR-2, VBS y comparaciones entre solvers
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
          description="Elige un experimento completado para ver el análisis estadístico"
          icon={<BarChart3 className="w-6 h-6 text-gray-400" />}
        />
      ) : (
        <>
          {/* Tabs */}
          <div className="border-b border-dark-700">
            <nav className="flex gap-4">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
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

          {/* Tab Content */}
          <div className="mt-6">
            {activeTab === 'par2' && (
              <PAR2Analysis data={par2Data} isLoading={par2Loading} timeout={timeout} />
            )}
            {activeTab === 'vbs' && (
              <VBSAnalysis data={vbsData} isLoading={vbsLoading} />
            )}
            {activeTab === 'pairwise' && (
              <PairwiseAnalysis data={pairwiseData} isLoading={pairwiseLoading} />
            )}
            {activeTab === 'families' && (
              <FamilyAnalysis data={familyData} isLoading={familyLoading} />
            )}
          </div>
        </>
      )}
    </div>
  );
}

// PAR-2 Analysis Component
function PAR2Analysis({ data, isLoading, timeout }: {
  data: any;
  isLoading: boolean;
  timeout: number;
}) {
  if (isLoading) return <LoadingSpinner text="Calculando PAR-2..." />;
  if (!data) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">PAR-2 Score Ranking</h3>
          <p className="text-sm text-gray-400">
            Penalized Average Runtime con factor 2×timeout para instancias no resueltas
          </p>
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
            <tbody className="divide-y divide-gray-200">
              {data.rankings?.map((row: any, index: number) => (
                <tr key={row.solver_name} className={index === 0 ? 'bg-yellow-50' : ''}>
                  <td>
                    {index === 0 && <Trophy className="w-5 h-5 text-yellow-500 inline mr-1" />}
                    #{index + 1}
                  </td>
                  <td className="font-medium">{row.solver_name}</td>
                  <td className="font-mono">{row.par2_score.toFixed(2)}</td>
                  <td>
                    <span className="text-green-600 font-medium">{row.solved}</span>
                    <span className="text-gray-400">/{row.total}</span>
                  </td>
                  <td className="text-yellow-600">{row.timeouts}</td>
                  <td className="font-mono text-sm">{row.avg_time.toFixed(3)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-800">Sobre PAR-2</h4>
        <p className="text-sm text-blue-700 mt-1">
          PAR-2 (Penalized Average Runtime) asigna 2×timeout ({2 * timeout}s) a las instancias 
          no resueltas. Un score menor indica mejor rendimiento.
        </p>
      </div>
    </div>
  );
}

// VBS Analysis Component
function VBSAnalysis({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) return <LoadingSpinner text="Calculando VBS..." />;
  if (!data) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="card-body text-center">
            <Trophy className="w-12 h-12 mx-auto text-yellow-500 mb-2" />
            <p className="text-gray-400">Mejor Solver</p>
            <p className="text-2xl font-bold">{data.best_single_solver}</p>
            <p className="text-sm text-gray-400">
              Resuelve {data.best_single_solved} instancias
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-body text-center">
            <Scale className="w-12 h-12 mx-auto text-purple-500 mb-2" />
            <p className="text-gray-400">Virtual Best Solver</p>
            <p className="text-2xl font-bold">{data.vbs_solved}</p>
            <p className="text-sm text-gray-400">instancias resueltas</p>
          </div>
        </div>

        <div className="card">
          <div className="card-body text-center">
            <BarChart3 className="w-12 h-12 mx-auto text-green-500 mb-2" />
            <p className="text-gray-400">Ventaja VBS</p>
            <p className="text-2xl font-bold">
              +{data.vbs_solved - data.best_single_solved}
            </p>
            <p className="text-sm text-gray-400">
              instancias adicionales
            </p>
          </div>
        </div>
      </div>

      {/* Contribution by solver */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Contribución al VBS</h3>
        </div>
        <div className="card-body">
          <div className="space-y-3">
            {data.contributions?.map((contrib: any) => (
              <div key={contrib.solver} className="flex items-center gap-4">
                <span className="w-32 font-medium">{contrib.solver}</span>
                <div className="flex-1 h-6 bg-dark-600 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary-500 rounded-full"
                    style={{ width: `${contrib.percentage}%` }}
                  />
                </div>
                <span className="w-24 text-right text-sm text-gray-400">
                  {contrib.unique_wins} ({contrib.percentage.toFixed(1)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <h4 className="font-medium text-purple-800">Sobre VBS</h4>
        <p className="text-sm text-purple-700 mt-1">
          El Virtual Best Solver (VBS) representa el rendimiento teórico óptimo si pudiéramos 
          elegir el mejor solver para cada instancia individual.
        </p>
      </div>
    </div>
  );
}

// Pairwise Comparison Component
function PairwiseAnalysis({ data, isLoading }: { data: any; isLoading: boolean }) {
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
                  <th key={s} className="bg-dark-700 text-center px-4">
                    {s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {solvers.map((s1: string, i: number) => (
                <tr key={s1}>
                  <td className="font-medium bg-dark-800 px-4">{s1}</td>
                  {solvers.map((s2: string, j: number) => {
                    const value = data.matrix[i]?.[j] || 0;
                    const reverseValue = data.matrix[j]?.[i] || 0;
                    const isWinner = value > reverseValue;
                    const isTie = value === reverseValue;
                    
                    return (
                      <td 
                        key={s2} 
                        className={`text-center px-4 py-2 ${
                          i === j ? 'bg-dark-700' :
                          isWinner ? 'bg-green-50 text-green-700 font-medium' :
                          isTie ? 'bg-dark-800' :
                          'bg-red-50 text-red-700'
                        }`}
                      >
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

      {/* Summary */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Resumen de Victorias</h3>
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Solver</th>
                <th>Victorias Totales</th>
                <th>Derrotas Totales</th>
                <th>Ratio</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data.summary?.map((row: any) => (
                <tr key={row.solver}>
                  <td className="font-medium">{row.solver}</td>
                  <td className="text-green-600">{row.wins}</td>
                  <td className="text-red-600">{row.losses}</td>
                  <td className="font-mono">
                    {row.losses > 0 
                      ? (row.wins / row.losses).toFixed(2) 
                      : '∞'}
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

// Family Analysis Component
function FamilyAnalysis({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) return <LoadingSpinner text="Analizando familias..." />;
  if (!data) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      {data.families?.map((family: any) => (
        <div key={family.name} className="card">
          <div className="card-header">
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
              <tbody className="divide-y divide-gray-200">
                {family.solvers?.map((solver: any, index: number) => (
                  <tr key={solver.name} className={index === 0 ? 'bg-yellow-50' : ''}>
                    <td className="font-medium">
                      {index === 0 && <Trophy className="w-4 h-4 text-yellow-500 inline mr-1" />}
                      {solver.name}
                    </td>
                    <td>
                      <span className="text-green-600">{solver.solved}</span>
                      <span className="text-gray-400">/{family.count}</span>
                    </td>
                    <td className="font-mono">{solver.par2.toFixed(2)}</td>
                    <td className="font-mono text-sm">{solver.avg_time.toFixed(3)}s</td>
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
