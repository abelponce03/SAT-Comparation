import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import {
  FileText,
  Upload,
  Search,
  Trash2,
  Eye,
  FolderSearch,
  Loader2,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { benchmarksApi } from '@/services/api';
import type { Benchmark, BenchmarkFamily } from '@/types';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import Badge from '@/components/common/Badge';
import Modal from '@/components/common/Modal';
import EmptyState from '@/components/common/EmptyState';

const PAGE_SIZE = 50;

export default function Benchmarks() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [familyFilter, setFamilyFilter] = useState<string>('all');
  const [difficultyFilter, setDifficultyFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [previewBenchmark, setPreviewBenchmark] = useState<Benchmark | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Debounce search
  const handleSearchChange = useCallback((value: string) => {
    setSearchTerm(value);
    const timer = window.setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, []);

  // Paginated query
  const { data: benchmarkData, isLoading, isFetching } = useQuery({
    queryKey: ['benchmarks', familyFilter, difficultyFilter, page, debouncedSearch],
    queryFn: () => benchmarksApi.getPaginated(
      page,
      PAGE_SIZE,
      familyFilter !== 'all' ? familyFilter : undefined,
      difficultyFilter !== 'all' ? difficultyFilter : undefined,
      debouncedSearch || undefined,
    ),
    placeholderData: keepPreviousData,
  });

  const { data: families } = useQuery({
    queryKey: ['benchmark-families'],
    queryFn: benchmarksApi.getFamilies,
  });

  const { data: stats } = useQuery({
    queryKey: ['benchmark-stats'],
    queryFn: benchmarksApi.getStats,
  });

  // Mutations
  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => benchmarksApi.upload(files),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
      queryClient.invalidateQueries({ queryKey: ['benchmark-families'] });
      queryClient.invalidateQueries({ queryKey: ['benchmark-stats'] });
      toast.success(`${data.success.length} benchmarks importados`);
      setIsUploadModalOpen(false);
    },
    onError: () => toast.error('Error al subir benchmarks'),
  });

  const scanMutation = useMutation({
    mutationFn: () => benchmarksApi.scan(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
      queryClient.invalidateQueries({ queryKey: ['benchmark-families'] });
      queryClient.invalidateQueries({ queryKey: ['benchmark-stats'] });
      toast.success(`${data.imported} benchmarks importados de ${data.found} encontrados`);
    },
    onError: () => toast.error('Error al escanear directorio'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => benchmarksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
      queryClient.invalidateQueries({ queryKey: ['benchmark-stats'] });
      toast.success('Benchmark eliminado');
    },
  });

  const benchmarks = benchmarkData?.items || [];
  const totalItems = benchmarkData?.total || 0;
  const totalPages = benchmarkData?.pages || 1;

  if (isLoading && !benchmarkData) {
    return <LoadingSpinner size="lg" text="Cargando benchmarks..." />;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Benchmarks</h1>
          <p className="text-gray-400 mt-1">
            {stats?.total || 0} instancias CNF • {families?.length || 0} familias
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
            className="btn-secondary"
          >
            {scanMutation.isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <FolderSearch className="w-5 h-5 mr-2" />
                Escanear
              </>
            )}
          </button>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="btn-primary"
          >
            <Upload className="w-5 h-5 mr-2" />
            Subir CNF
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Benchmarks" value={stats.total} color="blue" />
          <StatCard label="Variables (promedio)" value={Math.round(stats.avg_variables).toLocaleString()} color="green" />
          <StatCard label="Cláusulas (promedio)" value={Math.round(stats.avg_clauses).toLocaleString()} color="purple" />
          <StatCard label="Familias" value={families?.length || 0} color="yellow" />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar benchmark..."
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="input pl-10"
          />
          {isFetching && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary-400 animate-spin" />
          )}
        </div>

        <select
          value={familyFilter}
          onChange={(e) => { setFamilyFilter(e.target.value); setPage(1); }}
          className="input w-full sm:w-48"
        >
          <option value="all">Todas las familias</option>
          {families?.map((f: BenchmarkFamily) => (
            <option key={f.family} value={f.family}>
              {f.family} ({f.count})
            </option>
          ))}
        </select>

        <select
          value={difficultyFilter}
          onChange={(e) => { setDifficultyFilter(e.target.value); setPage(1); }}
          className="input w-full sm:w-40"
        >
          <option value="all">Dificultad</option>
          <option value="easy">Fácil</option>
          <option value="medium">Media</option>
          <option value="hard">Difícil</option>
        </select>
      </div>

      {/* Family Pills */}
      {families && families.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {families.slice(0, 10).map((f: BenchmarkFamily) => (
            <button
              key={f.family}
              onClick={() => {
                setFamilyFilter(f.family === familyFilter ? 'all' : f.family);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                familyFilter === f.family
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-dark-700 text-gray-400 hover:bg-dark-600'
              }`}
            >
              {f.family} <span className="text-gray-400">({f.count})</span>
            </button>
          ))}
        </div>
      )}

      {/* Benchmarks Table */}
      {benchmarks.length === 0 && !isFetching ? (
        <EmptyState
          title="No hay benchmarks"
          description="Sube archivos CNF o escanea un directorio"
          icon={<FileText className="w-6 h-6 text-gray-400" />}
          action={
            <button onClick={() => setIsUploadModalOpen(true)} className="btn-primary">
              <Upload className="w-5 h-5 mr-2" />
              Subir CNF
            </button>
          }
        />
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Archivo</th>
                  <th>Familia</th>
                  <th>Variables</th>
                  <th>Cláusulas</th>
                  <th>Ratio</th>
                  <th>Dificultad</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {benchmarks.map((benchmark: Benchmark) => (
                  <tr key={benchmark.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-gray-400" />
                        <span className="font-medium truncate max-w-xs" title={benchmark.filename}>
                          {benchmark.filename}
                        </span>
                      </div>
                    </td>
                    <td>
                      <Badge variant="info">{benchmark.family}</Badge>
                    </td>
                    <td className="font-mono text-sm">
                      {benchmark.num_variables?.toLocaleString() || '-'}
                    </td>
                    <td className="font-mono text-sm">
                      {benchmark.num_clauses?.toLocaleString() || '-'}
                    </td>
                    <td className="font-mono text-sm">
                      {benchmark.clause_variable_ratio?.toFixed(2) || '-'}
                    </td>
                    <td>
                      <DifficultyBadge difficulty={benchmark.difficulty} />
                    </td>
                    <td>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setPreviewBenchmark(benchmark)}
                          className="p-1.5 hover:bg-dark-700 rounded"
                          title="Vista previa"
                        >
                          <Eye className="w-4 h-4 text-gray-400" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('¿Eliminar este benchmark?')) {
                              deleteMutation.mutate(benchmark.id);
                            }
                          }}
                          className="p-1.5 hover:bg-red-50 rounded"
                          title="Eliminar"
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="px-6 py-4 border-t border-dark-700 bg-dark-800 flex items-center justify-between">
            <p className="text-sm text-gray-400">
              Mostrando {Math.min((page - 1) * PAGE_SIZE + 1, totalItems)}–{Math.min(page * PAGE_SIZE, totalItems)} de {totalItems} benchmarks
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(1)}
                disabled={page <= 1}
                className="p-1.5 rounded hover:bg-dark-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-400"
                title="Primera página"
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded hover:bg-dark-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-400"
                title="Anterior"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3 py-1 text-sm text-gray-300">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1.5 rounded hover:bg-dark-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-400"
                title="Siguiente"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(totalPages)}
                disabled={page >= totalPages}
                className="p-1.5 rounded hover:bg-dark-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-400"
                title="Última página"
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        title="Subir Benchmarks CNF"
        size="lg"
      >
        <UploadDropzone
          onUpload={(files) => uploadMutation.mutate(files)}
          isLoading={uploadMutation.isPending}
        />
      </Modal>

      {/* Preview Modal */}
      <Modal
        isOpen={!!previewBenchmark}
        onClose={() => setPreviewBenchmark(null)}
        title={previewBenchmark?.filename || 'Preview'}
        size="xl"
      >
        {previewBenchmark && (
          <BenchmarkPreview benchmarkId={previewBenchmark.id} />
        )}
      </Modal>
    </div>
  );
}

// ==================== Helper Components ====================

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-900/30 border border-blue-700/40 text-blue-300',
    green: 'bg-green-900/30 border border-green-700/40 text-green-300',
    purple: 'bg-purple-900/30 border border-purple-700/40 text-purple-300',
    yellow: 'bg-yellow-900/30 border border-yellow-700/40 text-yellow-300',
  };

  return (
    <div className={`rounded-xl p-4 ${colorClasses[color]}`}>
      <p className="text-sm opacity-80">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const variants: Record<string, 'success' | 'warning' | 'error' | 'gray'> = {
    easy: 'success',
    medium: 'warning',
    hard: 'error',
    unknown: 'gray',
  };

  return <Badge variant={variants[difficulty] || 'gray'}>{difficulty}</Badge>;
}

function UploadDropzone({ onUpload, isLoading }: {
  onUpload: (files: File[]) => void;
  isLoading: boolean;
}) {
  const [files, setFiles] = useState<File[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const cnfFiles = acceptedFiles.filter(f => f.name.endsWith('.cnf'));
    setFiles(prev => [...prev, ...cnfFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/plain': ['.cnf'] },
    multiple: true,
  });

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <p className="text-gray-400">
          {isDragActive
            ? 'Suelta los archivos aquí...'
            : 'Arrastra archivos CNF o haz clic para seleccionar'}
        </p>
        <p className="text-sm text-gray-400 mt-2">Solo archivos .cnf</p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-300">
            Archivos seleccionados ({files.length})
          </h4>
          <div className="max-h-48 overflow-y-auto space-y-2">
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-2 bg-dark-800 rounded"
              >
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <span className="text-sm truncate max-w-xs">{file.name}</span>
                  <span className="text-xs text-gray-400">
                    ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="p-1 hover:bg-dark-600 rounded"
                >
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-end gap-3 pt-4">
        <button
          onClick={() => onUpload(files)}
          disabled={files.length === 0 || isLoading}
          className="btn-primary"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Subiendo...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4 mr-2" />
              Subir {files.length} archivos
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function BenchmarkPreview({ benchmarkId }: { benchmarkId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['benchmark-preview', benchmarkId],
    queryFn: () => benchmarksApi.preview(benchmarkId, 100),
  });

  if (isLoading) {
    return <LoadingSpinner text="Cargando..." />;
  }

  return (
    <div>
      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono max-h-96">
        {data?.lines?.join('\n')}
      </pre>
      {data?.truncated && (
        <p className="text-sm text-gray-400 mt-2">
          Mostrando primeras {data.total_lines} líneas...
        </p>
      )}
    </div>
  );
}
