import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { 
  Plus, 
  FlaskConical,
  Play,
  Pause,
  Trash2,
  Eye,
  Loader2,
  Clock,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import { experimentsApi, solversApi, benchmarksApi } from '@/services/api';
import type { Experiment, ExperimentCreate } from '@/types';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import { StatusBadge } from '@/components/common/Badge';
import Modal from '@/components/common/Modal';
import EmptyState from '@/components/common/EmptyState';

export default function Experiments() {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Queries
  const { data: experiments, isLoading } = useQuery({
    queryKey: ['experiments'],
    queryFn: () => experimentsApi.getAll(),
    refetchInterval: 5000, // Refresh every 5s for running experiments
  });

  // Mutations
  const deleteMutation = useMutation({
    mutationFn: (id: number) => experimentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
      toast.success('Experimento eliminado');
    },
  });

  const startMutation = useMutation({
    mutationFn: (id: number) => experimentsApi.start(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
      toast.success('Experimento iniciado');
    },
    onError: () => toast.error('Error al iniciar experimento'),
  });

  const stopMutation = useMutation({
    mutationFn: (id: number) => experimentsApi.stop(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
      toast.success('Experimento detenido');
    },
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" text="Cargando experimentos..." />;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Experimentos</h1>
          <p className="text-gray-400 mt-1">
            Crea y ejecuta comparativas entre solvers
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="btn-primary"
        >
          <Plus className="w-5 h-5 mr-2" />
          Nuevo Experimento
        </button>
      </div>

      {/* Experiments List */}
      {!experiments?.length ? (
        <EmptyState
          title="No hay experimentos"
          description="Crea tu primer experimento para comparar solvers"
          icon={<FlaskConical className="w-6 h-6 text-gray-400" />}
          action={
            <button onClick={() => setIsCreateModalOpen(true)} className="btn-primary">
              <Plus className="w-5 h-5 mr-2" />
              Nuevo Experimento
            </button>
          }
        />
      ) : (
        <div className="grid gap-4">
          {experiments.map((experiment) => (
            <ExperimentCard
              key={experiment.id}
              experiment={experiment}
              onStart={() => startMutation.mutate(experiment.id)}
              onStop={() => stopMutation.mutate(experiment.id)}
              onDelete={() => {
                if (confirm('¿Eliminar este experimento y todos sus resultados?')) {
                  deleteMutation.mutate(experiment.id);
                }
              }}
              isStarting={startMutation.isPending}
              isStopping={stopMutation.isPending}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Nuevo Experimento"
        size="xl"
      >
        <CreateExperimentForm
          onSuccess={() => {
            setIsCreateModalOpen(false);
            queryClient.invalidateQueries({ queryKey: ['experiments'] });
          }}
        />
      </Modal>
    </div>
  );
}

// Experiment Card Component
function ExperimentCard({ 
  experiment, 
  onStart, 
  onStop, 
  onDelete,
  isStarting,
  isStopping
}: {
  experiment: Experiment;
  onStart: () => void;
  onStop: () => void;
  onDelete: () => void;
  isStarting: boolean;
  isStopping: boolean;
}) {
  const progress = experiment.total_runs > 0 
    ? (experiment.completed_runs / experiment.total_runs * 100) 
    : 0;

  const _statusIcon = {
    pending: <Clock className="w-5 h-5 text-gray-400" />,
    running: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
    completed: <CheckCircle2 className="w-5 h-5 text-green-500" />,
    stopped: <AlertCircle className="w-5 h-5 text-yellow-500" />,
    error: <AlertCircle className="w-5 h-5 text-red-500" />,
  };

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="card-body">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Info */}
          <div className="flex items-start gap-4">
            <div className="p-3 bg-purple-50 rounded-lg">
              <FlaskConical className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Link 
                  to={`/experiments/${experiment.id}`}
                  className="text-lg font-semibold text-white hover:text-primary-600"
                >
                  {experiment.name}
                </Link>
                <StatusBadge status={experiment.status} />
              </div>
              {experiment.description && (
                <p className="text-gray-400 text-sm mt-1 line-clamp-1">
                  {experiment.description}
                </p>
              )}
              <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
                <span>Timeout: {experiment.timeout_seconds}s</span>
                <span>•</span>
                <span>Memoria: {experiment.memory_limit_mb}MB</span>
                <span>•</span>
                <span>Jobs: {experiment.parallel_jobs}</span>
              </div>
            </div>
          </div>

          {/* Progress & Actions */}
          <div className="flex items-center gap-4">
            {/* Progress */}
            <div className="flex-1 lg:w-48">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Progreso</span>
                <span className="font-medium">
                  {experiment.completed_runs}/{experiment.total_runs}
                </span>
              </div>
              <div className="h-2 bg-dark-600 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all ${
                    experiment.status === 'completed' ? 'bg-green-500' :
                    experiment.status === 'running' ? 'bg-blue-500' :
                    'bg-gray-400'
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              {experiment.status === 'pending' && (
                <button
                  onClick={onStart}
                  disabled={isStarting}
                  className="btn-success text-sm py-2"
                >
                  {isStarting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-1" />
                      Iniciar
                    </>
                  )}
                </button>
              )}
              
              {experiment.status === 'running' && (
                <button
                  onClick={onStop}
                  disabled={isStopping}
                  className="btn-secondary text-sm py-2"
                >
                  {isStopping ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Pause className="w-4 h-4 mr-1" />
                      Detener
                    </>
                  )}
                </button>
              )}

              <Link
                to={`/experiments/${experiment.id}`}
                className="btn-secondary text-sm py-2"
              >
                <Eye className="w-4 h-4 mr-1" />
                Ver
              </Link>

              <button
                onClick={onDelete}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Create Experiment Form
function CreateExperimentForm({ onSuccess }: { onSuccess: () => void }) {
  const _queryClient = useQueryClient();
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    timeout_seconds: 5000,
    memory_limit_mb: 8192,
    parallel_jobs: 1,
    solver_ids: [] as number[],
    benchmark_ids: [] as number[],
  });

  const [step, setStep] = useState(1);

  // Queries
  const { data: solvers } = useQuery({
    queryKey: ['solvers', 'ready'],
    queryFn: () => solversApi.getAll('ready'),
  });

  const { data: benchmarks } = useQuery({
    queryKey: ['benchmarks'],
    queryFn: () => benchmarksApi.getAll(),
  });

  const { data: families } = useQuery({
    queryKey: ['benchmark-families'],
    queryFn: benchmarksApi.getFamilies,
  });

  // Mutation
  const createMutation = useMutation({
    mutationFn: (data: ExperimentCreate) => experimentsApi.create(data),
    onSuccess: () => {
      toast.success('Experimento creado');
      onSuccess();
    },
    onError: () => toast.error('Error al crear experimento'),
  });

  const totalRuns = formData.solver_ids.length * formData.benchmark_ids.length;
  const estimatedTime = (totalRuns * formData.timeout_seconds) / 3600;

  const handleSubmit = () => {
    if (!formData.name) {
      toast.error('Nombre requerido');
      return;
    }
    if (formData.solver_ids.length === 0) {
      toast.error('Selecciona al menos un solver');
      return;
    }
    if (formData.benchmark_ids.length === 0) {
      toast.error('Selecciona al menos un benchmark');
      return;
    }
    createMutation.mutate(formData);
  };

  const selectAllBenchmarksByFamily = (family: string) => {
    const familyBenchmarks = benchmarks?.filter(b => b.family === family) || [];
    const ids = familyBenchmarks.map(b => b.id);
    setFormData(prev => ({
      ...prev,
      benchmark_ids: [...new Set([...prev.benchmark_ids, ...ids])]
    }));
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Step indicators */}
      <div className="flex items-center justify-center gap-4">
        {[1, 2, 3].map((s) => (
          <button
            key={s}
            onClick={() => setStep(s)}
            className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
              step === s 
                ? 'bg-primary-600 text-white' 
                : step > s 
                  ? 'bg-green-500 text-white'
                  : 'bg-dark-600 text-gray-400'
            }`}
          >
            {step > s ? <CheckCircle2 className="w-5 h-5" /> : s}
          </button>
        ))}
      </div>

      {/* Step 1: Basic Info */}
      {step === 1 && (
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Información Básica</h3>
          
          <div>
            <label className="label">Nombre del experimento *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="ej: Comparativa Kissat vs MiniSat"
              className="input"
            />
          </div>

          <div>
            <label className="label">Descripción</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Descripción del experimento..."
              className="input"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">Timeout (s)</label>
              <input
                type="number"
                value={formData.timeout_seconds}
                onChange={(e) => setFormData({ ...formData, timeout_seconds: parseInt(e.target.value) })}
                className="input"
                min={1}
              />
            </div>
            <div>
              <label className="label">Memoria (MB)</label>
              <input
                type="number"
                value={formData.memory_limit_mb}
                onChange={(e) => setFormData({ ...formData, memory_limit_mb: parseInt(e.target.value) })}
                className="input"
                min={128}
              />
            </div>
            <div>
              <label className="label">Jobs paralelos</label>
              <input
                type="number"
                value={formData.parallel_jobs}
                onChange={(e) => setFormData({ ...formData, parallel_jobs: parseInt(e.target.value) })}
                className="input"
                min={1}
                max={16}
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button onClick={() => setStep(2)} className="btn-primary">
              Siguiente
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Select Solvers */}
      {step === 2 && (
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Seleccionar Solvers</h3>
          <p className="text-sm text-gray-400">
            Seleccionados: {formData.solver_ids.length} de {solvers?.length || 0}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
            {solvers?.map((solver) => (
              <label
                key={solver.id}
                className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                  formData.solver_ids.includes(solver.id)
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-dark-700 hover:bg-dark-800'
                }`}
              >
                <input
                  type="checkbox"
                  checked={formData.solver_ids.includes(solver.id)}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setFormData(prev => ({
                      ...prev,
                      solver_ids: checked
                        ? [...prev.solver_ids, solver.id]
                        : prev.solver_ids.filter(id => id !== solver.id)
                    }));
                  }}
                  className="rounded"
                />
                <span className="font-medium">{solver.name}</span>
                {solver.version && <span className="text-xs text-gray-400">v{solver.version}</span>}
              </label>
            ))}
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(1)} className="btn-secondary">
              Anterior
            </button>
            <button onClick={() => setStep(3)} className="btn-primary">
              Siguiente
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Select Benchmarks */}
      {step === 3 && (
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Seleccionar Benchmarks</h3>
          
          {/* Quick select by family */}
          <div>
            <p className="text-sm text-gray-400 mb-2">Selección rápida por familia:</p>
            <div className="flex flex-wrap gap-2">
              {families?.map((f: any) => (
                <button
                  key={f.family}
                  onClick={() => selectAllBenchmarksByFamily(f.family)}
                  className="px-3 py-1 text-sm bg-dark-700 hover:bg-dark-600 rounded-full"
                >
                  {f.family} ({f.count})
                </button>
              ))}
            </div>
          </div>

          <p className="text-sm text-gray-400">
            Seleccionados: {formData.benchmark_ids.length} de {benchmarks?.length || 0}
          </p>

          <div className="max-h-48 overflow-y-auto border rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-dark-800 sticky top-0">
                <tr>
                  <th className="p-2 text-left">
                    <input
                      type="checkbox"
                      checked={benchmarks != null && benchmarks.length > 0 && formData.benchmark_ids.length === benchmarks.length}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setFormData(prev => ({
                          ...prev,
                          benchmark_ids: checked ? (benchmarks?.map(b => b.id) || []) : []
                        }));
                      }}
                    />
                  </th>
                  <th className="p-2 text-left">Archivo</th>
                  <th className="p-2 text-left">Familia</th>
                  <th className="p-2 text-left">Variables</th>
                </tr>
              </thead>
              <tbody>
                {benchmarks?.map((benchmark) => (
                  <tr key={benchmark.id} className="border-t border-dark-700">
                    <td className="p-2">
                      <input
                        type="checkbox"
                        checked={formData.benchmark_ids.includes(benchmark.id)}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setFormData(prev => ({
                            ...prev,
                            benchmark_ids: checked
                              ? [...prev.benchmark_ids, benchmark.id]
                              : prev.benchmark_ids.filter(id => id !== benchmark.id)
                          }));
                        }}
                      />
                    </td>
                    <td className="p-2 truncate max-w-xs">{benchmark.filename}</td>
                    <td className="p-2">{benchmark.family}</td>
                    <td className="p-2">{benchmark.num_variables?.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="bg-dark-800 rounded-lg p-4">
            <h4 className="font-medium mb-2">Resumen</h4>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-400">Total ejecuciones</p>
                <p className="text-xl font-bold">{totalRuns.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-gray-400">Tiempo estimado (peor caso)</p>
                <p className="text-xl font-bold">{estimatedTime.toFixed(1)}h</p>
              </div>
              <div>
                <p className="text-gray-400">Configuración</p>
                <p className="text-sm">
                  {formData.solver_ids.length} solvers × {formData.benchmark_ids.length} benchmarks
                </p>
              </div>
            </div>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="btn-secondary">
              Anterior
            </button>
            <button 
              onClick={handleSubmit} 
              disabled={createMutation.isPending}
              className="btn-primary"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creando...
                </>
              ) : (
                'Crear Experimento'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
