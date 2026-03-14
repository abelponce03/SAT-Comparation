import { useState } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
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
  Package,
  Library,
  Search,
  Filter,
  Info,
  Shield,
  Layers,
  Box,
  ChevronDown,
  ChevronUp,
  X,
  Terminal,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { solversApi } from '@/services/api';
import LoadingSpinner from '@/components/common/LoadingSpinner';

/* ── types ──────────────────────────────────────────── */

interface SolverEntry {
  id: number | null;
  key: string;
  name: string;
  version: string;
  description: string;
  executable_path: string | null;
  status: string;
  features: string[];
  website: string;
  category: string;
  has_plugin: boolean;
  solver_type?: string;
  preprocessing?: boolean;
  inprocessing?: boolean;
  parallel?: boolean;
  incremental?: boolean;
  best_for?: string[];
  performance_class?: string;
  build_system?: string;
  difficulty?: string;
}

interface SolverLibrary {
  installed: SolverEntry[];
  available: SolverEntry[];
  catalog: SolverEntry[];
  stats: {
    installed_count: number;
    available_count: number;
    catalog_count: number;
    total_known: number;
  };
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

type TabId = 'installed' | 'available' | 'catalog' | 'comparison';

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'installed',  label: 'Instalados',  icon: <CheckCircle2 className="w-4 h-4" /> },
  { id: 'available',  label: 'Disponibles', icon: <Download className="w-4 h-4" /> },
  { id: 'catalog',    label: 'Catálogo',    icon: <Library className="w-4 h-4" /> },
  { id: 'comparison', label: 'Comparación', icon: <Trophy className="w-4 h-4" /> },
];

/* ══════════════════════════════════════════════════════
   MAIN PAGE
   ══════════════════════════════════════════════════════ */

export default function Solvers() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabId>('installed');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [installLog, setInstallLog] = useState<{ key: string; log: string } | null>(null);

  /* ── queries ─────────────────────────────────────── */

  const { data: library, isLoading: loadingLib } = useQuery<SolverLibrary>({
    queryKey: ['solver-library'],
    queryFn: () => solversApi.getLibrary(),
    refetchInterval: 10_000,
  });

  const { data: comparison } = useQuery({
    queryKey: ['solver-comparison'],
    queryFn: () => solversApi.getComparison(),
    enabled: activeTab === 'comparison',
  });

  /* ── mutations ───────────────────────────────────── */

  const testMutation = useMutation({
    mutationFn: (id: number) => solversApi.test(id),
    onSuccess: (data) => {
      if (data.success) toast.success(`✅ ${data.solver_name} funciona correctamente`);
      else toast.error(`Error: ${data.error}`);
    },
    onError: () => toast.error('Error al probar solver'),
  });

  const installMutation = useMutation({
    mutationFn: (solverKey: string) => solversApi.install(solverKey),
    onSuccess: (data, solverKey) => {
      if (data.success) {
        toast.success(data.message || 'Solver instalado correctamente');
        queryClient.invalidateQueries({ queryKey: ['solver-library'] });
        queryClient.invalidateQueries({ queryKey: ['solver-comparison'] });
        queryClient.invalidateQueries({ queryKey: ['solvers'] });
        setInstallLog(null);
      } else {
        toast.error(data.message || data.error || 'Error al instalar solver');
        if (data.log) setInstallLog({ key: solverKey, log: data.log });
      }
    },
    onError: (err: any) =>
      toast.error(err?.response?.data?.detail || 'Error al instalar solver'),
  });

  const uninstallMutation = useMutation({
    mutationFn: (solverKey: string) => solversApi.uninstall(solverKey),
    onSuccess: () => {
      toast.success('Solver desinstalado');
      queryClient.invalidateQueries({ queryKey: ['solver-library'] });
      queryClient.invalidateQueries({ queryKey: ['solver-comparison'] });
      queryClient.invalidateQueries({ queryKey: ['solvers'] });
    },
    onError: (err: any) =>
      toast.error(err?.response?.data?.detail || 'Error al desinstalar'),
  });

  /* ── loading ─────────────────────────────────────── */

  if (loadingLib) return <LoadingSpinner size="lg" text="Cargando biblioteca de solvers..." />;

  const stats = library?.stats ?? { installed_count: 0, available_count: 0, catalog_count: 0, total_known: 0 };

  /* ── filtering ───────────────────────────────────── */

  const filterSolvers = (list: SolverEntry[]) => {
    let filtered = list;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.key.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.features.some((f) => f.toLowerCase().includes(q)),
      );
    }
    if (categoryFilter !== 'all') {
      filtered = filtered.filter((s) => s.category === categoryFilter);
    }
    return filtered;
  };

  const allCategories = Array.from(
    new Set([
      ...(library?.installed ?? []).map((s) => s.category),
      ...(library?.available ?? []).map((s) => s.category),
      ...(library?.catalog ?? []).map((s) => s.category),
    ]),
  );

  const currentList =
    activeTab === 'installed'
      ? filterSolvers(library?.installed ?? [])
      : activeTab === 'available'
        ? filterSolvers(library?.available ?? [])
        : activeTab === 'catalog'
          ? filterSolvers(library?.catalog ?? [])
          : [];

  /* ── render ──────────────────────────────────────── */

  return (
    <div className="space-y-6 animate-fade-in">
      {/* header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <div className="p-2 bg-primary-600/20 rounded-xl border border-primary-600/30">
              <Cpu className="w-8 h-8 text-primary-400" />
            </div>
            Biblioteca de SAT Solvers
          </h1>
          <p className="text-gray-400 mt-2">
            Instala, gestiona y compara solvers SAT de bibliotecas oficiales
          </p>
        </div>
        <div className="flex gap-3">
          <StatMini icon={<CheckCircle2 className="w-4 h-4 text-green-400" />} value={stats.installed_count} label="Instalados" border="border-green-600/30" />
          <StatMini icon={<Download className="w-4 h-4 text-blue-400" />} value={stats.available_count} label="Disponibles" border="border-blue-600/30" />
          <StatMini icon={<Library className="w-4 h-4 text-purple-400" />} value={stats.total_known} label="Total conocidos" border="border-purple-600/30" />
        </div>
      </div>

      {/* info banner */}
      <div className="bg-gradient-to-r from-primary-900/30 to-purple-900/30 border border-primary-600/30 rounded-xl p-5">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-primary-600/20 rounded-lg shrink-0">
            <Package className="w-6 h-6 text-primary-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-1">Sistema de Plugins Dinámico</h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              Los solvers se descubren automáticamente desde <code className="text-primary-300 bg-dark-800 px-1.5 py-0.5 rounded">app/solvers/plugins/</code>.
              Puedes <strong className="text-white">instalar</strong> cualquier solver con un clic (se clona y compila desde su repositorio oficial),
              <strong className="text-white"> desinstalar</strong> los que no necesites, y <strong className="text-white">probar</strong> que funcionen correctamente.
              Todos los solvers instalados están disponibles para experimentos y comparaciones.
            </p>
          </div>
        </div>
      </div>

      {/* tabs */}
      <div className="flex items-center gap-1 border-b border-dark-700 pb-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors relative
              ${activeTab === tab.id
                ? 'text-primary-400 bg-dark-800 border border-dark-700 border-b-dark-900 -mb-px'
                : 'text-gray-400 hover:text-gray-200 hover:bg-dark-800/50'}`}
          >
            {tab.icon}
            {tab.label}
            {tab.id === 'installed' && stats.installed_count > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-green-600/20 text-green-400">{stats.installed_count}</span>
            )}
            {tab.id === 'available' && stats.available_count > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-blue-600/20 text-blue-400">{stats.available_count}</span>
            )}
            {tab.id === 'catalog' && stats.catalog_count > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-purple-600/20 text-purple-400">{stats.catalog_count}</span>
            )}
          </button>
        ))}
      </div>

      {/* search & filter */}
      {activeTab !== 'comparison' && (
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar solver por nombre, clave o característica..."
              className="input pl-10 w-full"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="input pl-10 pr-8 appearance-none cursor-pointer"
            >
              <option value="all">Todas las categorías</option>
              {allCategories.map((c) => (
                <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* install log modal */}
      {installLog && (
        <div className="bg-dark-900 border border-red-600/30 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-semibold text-red-400 flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              Log de instalación — {installLog.key}
            </h4>
            <button onClick={() => setInstallLog(null)} className="text-gray-500 hover:text-gray-300">
              <X className="w-4 h-4" />
            </button>
          </div>
          <pre className="text-xs text-gray-400 max-h-48 overflow-auto whitespace-pre-wrap font-mono bg-dark-950 rounded p-3">
            {installLog.log}
          </pre>
        </div>
      )}

      {/* tab content */}
      {activeTab !== 'comparison' ? (
        currentList.length === 0 ? (
          <EmptySection tab={activeTab} searchActive={!!searchQuery || categoryFilter !== 'all'} />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {currentList.map((solver) => (
              <SolverCard
                key={solver.key}
                solver={solver}
                onTest={() => solver.id != null && testMutation.mutate(solver.id)}
                isTestLoading={testMutation.isPending}
                onInstall={() => installMutation.mutate(solver.key)}
                isInstalling={installMutation.isPending && installMutation.variables === solver.key}
                isAnyInstalling={installMutation.isPending}
                onUninstall={() => {
                  if (confirm(`¿Desinstalar ${solver.name}? Se eliminará el código fuente y el binario.`)) {
                    uninstallMutation.mutate(solver.key);
                  }
                }}
                isUninstalling={uninstallMutation.isPending}
              />
            ))}
          </div>
        )
      ) : (
        <ComparisonTab comparison={comparison} />
      )}

      {/* CDCL explainer */}
      <CDCLExplainer />
    </div>
  );
}

/* ══════════════════════════════════════════════════════
   SOLVER CARD
   ══════════════════════════════════════════════════════ */

function SolverCard({
  solver,
  onTest,
  isTestLoading,
  onInstall,
  isInstalling,
  isAnyInstalling,
  onUninstall,
  isUninstalling,
}: {
  solver: SolverEntry;
  onTest: () => void;
  isTestLoading: boolean;
  onInstall: () => void;
  isInstalling: boolean;
  isAnyInstalling: boolean;
  onUninstall: () => void;
  isUninstalling: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  const catColors: Record<string, { border: string; bg: string }> = {
    competition:  { border: 'border-yellow-600/30', bg: 'from-yellow-900/20 to-orange-900/20' },
    educational:  { border: 'border-blue-600/30',   bg: 'from-blue-900/20 to-cyan-900/20' },
    parallel:     { border: 'border-green-600/30',  bg: 'from-green-900/20 to-emerald-900/20' },
    specialized:  { border: 'border-purple-600/30', bg: 'from-purple-900/20 to-pink-900/20' },
  };
  const defaultColors = { border: 'border-dark-700', bg: 'from-dark-800 to-dark-800' };
  const colors = catColors[solver.category] ?? defaultColors;

  const catIcons: Record<string, React.ReactNode> = {
    competition: <Trophy className="w-5 h-5 text-yellow-400" />,
    educational: <BookOpen className="w-5 h-5 text-blue-400" />,
    parallel:    <Layers className="w-5 h-5 text-green-400" />,
    specialized: <Shield className="w-5 h-5 text-purple-400" />,
  };
  const catIcon = catIcons[solver.category] ?? <Box className="w-5 h-5 text-gray-400" />;

  const statusMap: Record<string, { icon: React.ReactNode; text: string; color: string }> = {
    ready:         { icon: <CheckCircle2 className="w-4 h-4 text-green-400" />,            text: 'Listo para usar',      color: 'text-green-400' },
    not_installed: { icon: <Download className="w-4 h-4 text-blue-400" />,                  text: 'Listo para instalar',  color: 'text-blue-400' },
    error:         { icon: <AlertCircle className="w-4 h-4 text-red-400" />,                text: 'Error — reinstalar',   color: 'text-red-400' },
    installing:    { icon: <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />,    text: 'Instalando...',        color: 'text-yellow-400' },
    catalog:       { icon: <Info className="w-4 h-4 text-gray-500" />,                      text: 'Sin plugin (catálogo)', color: 'text-gray-500' },
  };
  const sCfg = statusMap[solver.status] ?? { icon: <AlertCircle className="w-4 h-4 text-yellow-400" />, text: 'No disponible', color: 'text-yellow-400' };

  return (
    <div className={`bg-gradient-to-br ${colors.bg} border ${colors.border} rounded-xl transition-all duration-300 hover:shadow-lg`}>
      {/* header */}
      <div className="p-5 pb-3">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-dark-900/50 rounded-lg border border-dark-700">{catIcon}</div>
            <div>
              <h3 className="text-xl font-bold text-white">{solver.name}</h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-sm text-gray-400">v{solver.version}</span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-dark-700 text-gray-400 capitalize">{solver.category}</span>
                {solver.has_plugin && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-primary-900/30 text-primary-400 border border-primary-600/20">plugin</span>
                )}
              </div>
            </div>
          </div>
          <div className={`flex items-center gap-1.5 text-xs font-medium ${sCfg.color}`}>
            {sCfg.icon}
            <span className="hidden sm:inline">{sCfg.text}</span>
          </div>
        </div>
        <p className="text-gray-400 text-sm leading-relaxed line-clamp-2">{solver.description}</p>
      </div>

      {/* features (expandable) */}
      <div className="px-5">
        <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors mb-2">
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {solver.features.length} características
        </button>
        {expanded && (
          <div className="flex flex-wrap gap-1.5 mb-3 animate-fade-in">
            {solver.features.map((f) => (
              <span key={f} className="px-2 py-0.5 bg-dark-900/50 border border-dark-600 text-gray-300 text-xs rounded-md">{f}</span>
            ))}
            {solver.best_for && solver.best_for.length > 0 && (
              <div className="w-full mt-2 flex flex-wrap gap-1.5">
                <span className="text-xs text-gray-500 mr-1">Ideal para:</span>
                {solver.best_for.map((b) => (
                  <span key={b} className="px-2 py-0.5 bg-primary-600/10 text-primary-300 text-xs rounded-full">{b}</span>
                ))}
              </div>
            )}
            {solver.performance_class && solver.performance_class !== 'Unknown' && (
              <div className="w-full mt-1 text-xs text-gray-500">
                Rendimiento: <span className="text-gray-300">{solver.performance_class}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* actions footer */}
      <div className="px-5 py-3 border-t border-dark-700/50 flex items-center justify-between">
        <div className={`flex items-center gap-1.5 text-sm ${sCfg.color}`}>
          {sCfg.icon}
          <span>{sCfg.text}</span>
        </div>
        <div className="flex items-center gap-2">
          {(solver.status === 'not_installed' || solver.status === 'error' || solver.status === 'unavailable') && solver.has_plugin && (
            <button
              onClick={onInstall}
              disabled={isInstalling || isAnyInstalling}
              className="px-3 py-1.5 bg-green-900/40 border border-green-600/40 text-green-300 text-sm rounded-lg hover:bg-green-800/50 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {isInstalling ? <><Loader2 className="w-4 h-4 animate-spin" /> Compilando...</> : <><Download className="w-4 h-4" /> Instalar</>}
            </button>
          )}
          {solver.status === 'ready' && solver.has_plugin && (
            <button onClick={onUninstall} disabled={isUninstalling} className="px-2 py-1.5 text-red-400/60 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-colors" title="Desinstalar">
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          {solver.status === 'ready' && (
            <button onClick={onTest} disabled={isTestLoading} className="px-3 py-1.5 bg-dark-900/50 border border-dark-600 text-gray-300 text-sm rounded-lg hover:bg-dark-700 transition-colors flex items-center gap-2">
              {isTestLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Probar
            </button>
          )}
          {solver.website && (
            <a href={solver.website} target="_blank" rel="noopener noreferrer" className="px-2 py-1.5 bg-dark-900/50 border border-dark-600 text-gray-300 text-sm rounded-lg hover:bg-dark-700 transition-colors flex items-center gap-1" title="Sitio web">
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════
   COMPARISON TAB
   ══════════════════════════════════════════════════════ */

function ComparisonTab({ comparison }: { comparison: any }) {
  if (!comparison) return <LoadingSpinner text="Cargando comparación..." />;

  return (
    <div className="space-y-8">
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
        <div className="px-5 py-3 bg-dark-900/50 border-b border-dark-700 flex items-center gap-2">
          <Trophy className="w-5 h-5 text-yellow-400" />
          <h3 className="font-semibold text-white">Matriz de Comparación</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-dark-900/30">
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
              {comparison.solvers?.map((s: ComparisonSolver) => (
                <tr key={s.name} className="hover:bg-dark-700/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-white">{s.name}</div>
                    <div className="text-xs text-gray-500">{s.performance_class}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-sm">{s.type}</td>
                  <BoolCell value={s.preprocessing} />
                  <BoolCell value={s.inprocessing} />
                  <BoolCell value={s.parallel} />
                  <BoolCell value={s.incremental} />
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {s.best_for?.map((bf) => (
                        <span key={bf} className="px-2 py-0.5 bg-primary-600/20 text-primary-300 text-xs rounded-full">{bf}</span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {comparison.legend && (
          <div className="px-4 py-3 bg-dark-900/30 border-t border-dark-700">
            <h4 className="text-xs font-semibold text-gray-400 mb-2">Leyenda</h4>
            <div className="flex flex-wrap gap-4 text-xs text-gray-500">
              {Object.entries(comparison.legend).map(([k, v]) => (
                <div key={k}><span className="text-gray-400">{k}:</span> {v as string}</div>
              ))}
            </div>
          </div>
        )}
      </div>

      {comparison.features_comparison && (
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
          <div className="px-5 py-3 bg-dark-900/50 border-b border-dark-700 flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-400" />
            <h3 className="font-semibold text-white">Comparación Detallada de Técnicas</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-dark-900/30">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">Técnica</th>
                  {Object.keys(comparison.features_comparison).map((name: string) => (
                    <th key={name} className="px-4 py-3 text-center text-sm font-semibold text-gray-300">{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700">
                {(() => {
                  const names = Object.keys(comparison.features_comparison);
                  const feats = names.length > 0 ? Object.keys(comparison.features_comparison[names[0]]) : [];
                  return feats.map((feat) => (
                    <tr key={feat} className="hover:bg-dark-700/30 transition-colors">
                      <td className="px-4 py-2.5 text-sm text-gray-300 font-medium">{feat.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</td>
                      {names.map((sn) => (
                        <BoolCell key={sn} value={comparison.features_comparison[sn][feat]} />
                      ))}
                    </tr>
                  ));
                })()}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════
   SMALL COMPONENTS
   ══════════════════════════════════════════════════════ */

function BoolCell({ value }: { value: boolean }) {
  return (
    <td className="px-4 py-2.5 text-center">
      {value ? <CheckCircle2 className="w-4 h-4 text-green-400 mx-auto" /> : <span className="text-gray-700">—</span>}
    </td>
  );
}

function StatMini({ icon, value, label, border }: { icon: React.ReactNode; value: number; label: string; border: string }) {
  return (
    <div className={`bg-dark-800/50 border ${border} rounded-xl px-4 py-3 text-center min-w-[90px]`}>
      <div className="flex items-center justify-center gap-1 mb-1">{icon}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-xs text-gray-400">{label}</div>
    </div>
  );
}

function EmptySection({ tab, searchActive }: { tab: TabId; searchActive: boolean }) {
  if (searchActive) {
    return (
      <div className="text-center py-12 text-gray-500">
        <Search className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-lg">No se encontraron solvers con ese filtro</p>
        <p className="text-sm mt-1">Intenta con otra búsqueda o cambia la categoría</p>
      </div>
    );
  }
  const msgs: Record<string, { title: string; desc: string }> = {
    installed: { title: 'No hay solvers instalados', desc: 'Ve a la pestaña "Disponibles" para instalar solvers desde sus repositorios oficiales.' },
    available: { title: 'Todos los plugins están instalados', desc: '¡Excelente! Todos los solvers disponibles ya están listos para usar.' },
    catalog:   { title: 'Catálogo vacío', desc: 'No hay solvers adicionales en el catálogo.' },
  };
  const m = msgs[tab] ?? { title: '', desc: '' };
  return (
    <div className="text-center py-12 text-gray-500">
      <Package className="w-10 h-10 mx-auto mb-3 opacity-50" />
      <p className="text-lg">{m.title}</p>
      <p className="text-sm mt-1">{m.desc}</p>
    </div>
  );
}

function CDCLExplainer() {
  return (
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
  );
}
