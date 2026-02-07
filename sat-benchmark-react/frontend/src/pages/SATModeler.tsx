import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Code2,
  Play,
  FileCode,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  BookOpen,
  Save,
  Trash2,
  Download,
  ChevronRight,
  Loader2,
  AlertTriangle,
  Lightbulb,
  Copy,
  Check,
  HelpCircle,
  Braces,
  Layers,
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import LoadingSpinner from '@/components/common/LoadingSpinner';

// ─── API helpers ────────────────────────────────────────────────
const BASE = '/api/modeler';
const api = {
  getExamples: async () => (await fetch(`${BASE}/examples`)).json(),
  parse: async (code: string) => {
    const r = await fetch(`${BASE}/parse`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    return r.json();
  },
  compile: async (code: string) => {
    const r = await fetch(`${BASE}/compile`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Compilation error'); }
    return r.json();
  },
  solve: async (code: string, solver?: string, timeout?: number) => {
    const r = await fetch(`${BASE}/solve`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, solver, timeout }),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Solve error'); }
    return r.json();
  },
  getSolvers: async () => (await fetch(`${BASE}/solvers`)).json(),
  getReference: async () => (await fetch(`${BASE}/language-reference`)).json(),
  getModels: async () => (await fetch(`${BASE}/models`)).json(),
  saveModel: async (name: string, description: string, code: string) => {
    const r = await fetch(`${BASE}/models`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description, code }),
    });
    return r.json();
  },
  deleteModel: async (id: string) => {
    await fetch(`${BASE}/models/${id}`, { method: 'DELETE' });
  },
};

// ─── Types ──────────────────────────────────────────────────────
interface ParseResult { valid: boolean; error?: string; variables?: string[]; constraints?: number; tokens?: number }
interface SolveResult { result: string; solver: string; time_seconds: number; assignment: Record<string, boolean> | null; dimacs_stats: any; solver_output: string }
interface CompileResult { success: boolean; dimacs: string; variable_map: Record<string, number>; num_variables: number; num_clauses: number; header: string }

// ─── Syntax-highlight (simple) ──────────────────────────────────
// ─── Syntax token types & colors (VS Code–inspired dark theme) ──
const enum TK {
  Comment,     // gray italic
  Keyword,     // purple bold       (var, bool, constraint, solve, satisfy)
  Builtin,     // cyan              (atmost, atleast, exactly, xor)
  LogicOp,     // magenta/pink      (not, and, or)
  Boolean,     // green             (true, false)
  Operator,    // yellow            (/\, \/, ->, <->, ~, !)
  Number,      // orange
  Ident,       // sky-blue
  Punctuation, // gray-300          (; : , ( ) [ ])
  Plain,
}

const TK_CLASS: Record<number, string> = {
  [TK.Comment]:     'color:#6b7280;font-style:italic',           // gray-500
  [TK.Keyword]:     'color:#c084fc;font-weight:600',             // purple-400 bold
  [TK.Builtin]:     'color:#22d3ee;font-weight:500',             // cyan-400
  [TK.LogicOp]:     'color:#f472b6;font-weight:600',             // pink-400 bold
  [TK.Boolean]:     'color:#4ade80;font-weight:600',             // green-400 bold
  [TK.Operator]:    'color:#facc15',                             // yellow-400
  [TK.Number]:      'color:#fb923c',                             // orange-400
  [TK.Ident]:       'color:#7dd3fc',                             // sky-300
  [TK.Punctuation]: 'color:#9ca3af',                             // gray-400
  [TK.Plain]:       'color:#d1d5db',                             // gray-300
};

const _KW_MAP: Record<string, number> = {
  var: TK.Keyword, bool: TK.Keyword, constraint: TK.Keyword,
  solve: TK.Keyword, satisfy: TK.Keyword,
  atmost: TK.Builtin, atleast: TK.Builtin, exactly: TK.Builtin,
  xor: TK.Builtin,
  not: TK.LogicOp, and: TK.LogicOp, or: TK.LogicOp,
  true: TK.Boolean, false: TK.Boolean,
};

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function highlightCode(code: string): string {
  const out: string[] = [];
  let i = 0;
  const n = code.length;

  const emit = (text: string, tk: number) => {
    const escaped = esc(text);
    if (tk === TK.Plain) { out.push(escaped); return; }
    out.push(`<span style="${TK_CLASS[tk]}">${escaped}</span>`);
  };

  while (i < n) {
    const ch = code[i];

    // ── Newline ──
    if (ch === '\n') { out.push('\n'); i++; continue; }

    // ── Comments: % … | // … ──
    if (ch === '%' || (ch === '/' && code[i + 1] === '/')) {
      let end = i;
      while (end < n && code[end] !== '\n') end++;
      emit(code.slice(i, end), TK.Comment);
      i = end;
      continue;
    }

    // ── Multi-char operators ──
    if (ch === '/' && code[i + 1] === '\\') { emit('/\\', TK.Operator); i += 2; continue; }
    if (ch === '\\' && code[i + 1] === '/') { emit('\\/', TK.Operator); i += 2; continue; }
    if (ch === '<' && code[i + 1] === '-' && code[i + 2] === '>') { emit('<->', TK.Operator); i += 3; continue; }
    if (ch === '-' && code[i + 1] === '>') { emit('->', TK.Operator); i += 2; continue; }

    // ── Single-char operators ──
    if (ch === '~' || ch === '!') { emit(ch, TK.Operator); i++; continue; }

    // ── Punctuation ──
    if (';:,()[]'.includes(ch)) { emit(ch, TK.Punctuation); i++; continue; }

    // ── Numbers ──
    if (ch >= '0' && ch <= '9') {
      let end = i;
      while (end < n && code[end] >= '0' && code[end] <= '9') end++;
      emit(code.slice(i, end), TK.Number);
      i = end;
      continue;
    }

    // ── Words (identifiers / keywords) ──
    if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || ch === '_') {
      let end = i;
      while (end < n && (/[a-zA-Z0-9_]/).test(code[end])) end++;
      const word = code.slice(i, end);
      const tk = _KW_MAP[word.toLowerCase()] ?? TK.Ident;
      emit(word, tk);
      i = end;
      continue;
    }

    // ── Whitespace / other ──
    out.push(esc(ch));
    i++;
  }

  return out.join('');
}

// ─── Tab type ───────────────────────────────────────────────────
type SideTab = 'examples' | 'models' | 'reference';

// ================================================================
// Main component
// ================================================================
export default function SATModeler() {
  const queryClient = useQueryClient();

  // Code state
  const [code, setCode] = useState<string>(
`% Mi primer modelo SAT
var bool: x, y, z;

constraint x \\/ y;
constraint not(x) \\/ z;
constraint y -> z;

solve satisfy;
`);
  const [selectedSolver, setSelectedSolver] = useState<string>('');
  const [timeout, setTimeout] = useState(30);
  const [sideTab, setSideTab] = useState<SideTab>('examples');
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [solveResult, setSolveResult] = useState<SolveResult | null>(null);
  const [compileResult, setCompileResult] = useState<CompileResult | null>(null);
  const [showDimacs, setShowDimacs] = useState(false);
  const [showOutput, setShowOutput] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [showSave, setShowSave] = useState(false);
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightRef = useRef<HTMLPreElement>(null);

  // Queries
  const { data: examples } = useQuery({ queryKey: ['modeler-examples'], queryFn: api.getExamples });
  const { data: solvers } = useQuery({ queryKey: ['modeler-solvers'], queryFn: api.getSolvers });
  const { data: reference } = useQuery({ queryKey: ['modeler-reference'], queryFn: api.getReference });
  const { data: savedModels, refetch: refetchModels } = useQuery({ queryKey: ['modeler-models'], queryFn: api.getModels });

  // Mutations
  const solveMut = useMutation({
    mutationFn: () => api.solve(code, selectedSolver || undefined, timeout),
    onSuccess: (data) => { setSolveResult(data); setCompileResult(null); toast.success(`Resultado: ${data.result}`); },
    onError: (err: any) => toast.error(err.message || 'Error al resolver'),
  });

  const compileMut = useMutation({
    mutationFn: () => api.compile(code),
    onSuccess: (data) => { setCompileResult(data); setSolveResult(null); setShowDimacs(true); toast.success('Compilado exitosamente'); },
    onError: (err: any) => toast.error(err.message || 'Error al compilar'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.deleteModel(id),
    onSuccess: () => { refetchModels(); toast.success('Modelo eliminado'); },
  });

  // Live parse on code change (debounced)
  const parseTimer = useRef<ReturnType<typeof window.setTimeout>>();
  useEffect(() => {
    if (parseTimer.current) clearTimeout(parseTimer.current);
    parseTimer.current = window.setTimeout(async () => {
      if (code.trim()) {
        const res = await api.parse(code);
        setParseResult(res);
      } else {
        setParseResult(null);
      }
    }, 400);
    return () => { if (parseTimer.current) clearTimeout(parseTimer.current); };
  }, [code]);

  // Sync scroll between textarea and highlight overlay
  const handleScroll = useCallback(() => {
    if (textareaRef.current && highlightRef.current) {
      highlightRef.current.scrollTop = textareaRef.current.scrollTop;
      highlightRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }, []);

  const loadExample = (ex: any) => {
    setCode(ex.code);
    setSolveResult(null);
    setCompileResult(null);
    toast.success(`Ejemplo cargado: ${ex.name}`);
  };

  const handleSave = async () => {
    if (!saveName.trim()) return;
    await api.saveModel(saveName.trim(), '', code);
    refetchModels();
    setShowSave(false);
    setSaveName('');
    toast.success('Modelo guardado');
  };

  const handleCopyDimacs = () => {
    if (compileResult?.dimacs) {
      navigator.clipboard.writeText(compileResult.dimacs);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadDimacs = () => {
    if (!compileResult?.dimacs) return;
    const blob = new Blob([compileResult.dimacs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'model.cnf';
    a.click();
    URL.revokeObjectURL(url);
  };

  const highlighted = useMemo(() => highlightCode(code), [code]);

  // Line numbers
  const lineCount = code.split('\n').length;

  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col gap-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <div className="p-2 bg-purple-600/20 rounded-xl border border-purple-600/30">
              <Code2 className="w-8 h-8 text-purple-400" />
            </div>
            SAT Modeler
          </h1>
          <p className="text-gray-400 mt-1">
            Modela problemas de satisfacibilidad con lenguaje de alto nivel y resuélvelos con los solvers del sistema
          </p>
        </div>

        {/* Parse status badge */}
        {parseResult && (
          <div className={clsx(
            'flex items-center gap-2 px-3 py-2 rounded-lg border text-sm',
            parseResult.valid
              ? 'bg-green-900/20 border-green-700/40 text-green-400'
              : 'bg-red-900/20 border-red-700/40 text-red-400'
          )}>
            {parseResult.valid ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            {parseResult.valid
              ? `✓ ${parseResult.variables?.length ?? 0} vars, ${parseResult.constraints ?? 0} restricciones`
              : 'Error de sintaxis'}
          </div>
        )}
      </div>

      {/* Main grid */}
      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        {/* ──── LEFT SIDEBAR (examples / models / reference) ──── */}
        <div className="col-span-3 flex flex-col bg-dark-800 border border-dark-700 rounded-xl overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-dark-700">
            {([
              { id: 'examples' as const, label: 'Ejemplos', icon: Lightbulb },
              { id: 'models' as const, label: 'Modelos', icon: Layers },
              { id: 'reference' as const, label: 'Referencia', icon: BookOpen },
            ]).map(t => (
              <button
                key={t.id}
                onClick={() => setSideTab(t.id)}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors',
                  sideTab === t.id ? 'text-purple-400 border-b-2 border-purple-500 bg-dark-700/30' : 'text-gray-500 hover:text-gray-300'
                )}
              >
                <t.icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {sideTab === 'examples' && examples?.map((ex: any) => (
              <button
                key={ex.id}
                onClick={() => loadExample(ex)}
                className="w-full text-left p-3 rounded-lg bg-dark-900/50 border border-dark-600 hover:border-purple-600/50 hover:bg-dark-700/50 transition-all group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <FileCode className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium text-white group-hover:text-purple-300 transition-colors">{ex.name}</span>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">{ex.description}</p>
              </button>
            ))}

            {sideTab === 'models' && (
              <>
                {(!savedModels || savedModels.length === 0) && (
                  <div className="text-center py-8 text-gray-500 text-sm">
                    <Save className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    No hay modelos guardados
                  </div>
                )}
                {savedModels?.map((m: any) => (
                  <div key={m.id} className="p-3 rounded-lg bg-dark-900/50 border border-dark-600 group">
                    <div className="flex items-center justify-between mb-1">
                      <button onClick={() => { setCode(m.code); toast.success('Modelo cargado'); }} className="text-sm font-medium text-white hover:text-purple-300 transition-colors truncate">
                        {m.name}
                      </button>
                      <button
                        onClick={() => deleteMut.mutate(m.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-900/30 text-gray-500 hover:text-red-400 transition-all"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <p className="text-xs text-gray-500">{new Date(m.created_at).toLocaleDateString()}</p>
                  </div>
                ))}
              </>
            )}

            {sideTab === 'reference' && reference?.sections?.map((sec: any, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-dark-900/50 border border-dark-600">
                <h4 className="text-sm font-semibold text-white mb-1.5">{sec.title}</h4>
                {sec.syntax && (
                  <code className="block text-xs bg-dark-800 px-2 py-1 rounded text-purple-300 mb-1.5 font-mono">{sec.syntax}</code>
                )}
                {sec.description && <p className="text-xs text-gray-400 mb-1.5">{sec.description}</p>}
                {sec.example && (
                  <code className="block text-xs bg-dark-800 px-2 py-1 rounded text-cyan-300 font-mono">{sec.example}</code>
                )}
                {sec.items && (
                  <div className="space-y-1 mt-1">
                    {sec.items.map((item: any, j: number) => (
                      <div key={j} className="flex gap-2 text-xs">
                        <code className="text-yellow-300 font-mono whitespace-nowrap">{item.op}</code>
                        <span className="text-gray-400">{item.desc}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ──── CENTER: CODE EDITOR ──── */}
        <div className="col-span-5 flex flex-col bg-dark-800 border border-dark-700 rounded-xl overflow-hidden">
          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-dark-700 bg-dark-900/40">
            <div className="flex items-center gap-2">
              <Braces className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-medium text-gray-300">Editor</span>
              <span className="text-xs text-gray-500 ml-2">{lineCount} líneas</span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setShowSave(true)}
                className="px-2.5 py-1.5 rounded-lg text-xs bg-dark-700 border border-dark-600 text-gray-300 hover:bg-dark-600 transition-colors flex items-center gap-1.5"
                title="Guardar modelo"
              >
                <Save className="w-3.5 h-3.5" /> Guardar
              </button>
              <button
                onClick={() => compileMut.mutate()}
                disabled={compileMut.isPending || !parseResult?.valid}
                className="px-2.5 py-1.5 rounded-lg text-xs bg-cyan-900/30 border border-cyan-700/40 text-cyan-300 hover:bg-cyan-800/30 transition-colors flex items-center gap-1.5 disabled:opacity-40"
              >
                {compileMut.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileCode className="w-3.5 h-3.5" />}
                Compilar
              </button>
              <button
                onClick={() => solveMut.mutate()}
                disabled={solveMut.isPending || !parseResult?.valid}
                className="px-3 py-1.5 rounded-lg text-xs bg-purple-600/80 text-white hover:bg-purple-500 transition-colors flex items-center gap-1.5 disabled:opacity-40 font-medium"
              >
                {solveMut.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                Resolver
              </button>
            </div>
          </div>

          {/* Editor area */}
          <div className="flex-1 relative overflow-hidden font-mono text-sm">
            {/* Line numbers */}
            <div className="absolute left-0 top-0 bottom-0 w-10 bg-dark-900/60 border-r border-dark-700 overflow-hidden select-none z-10">
              <div className="pt-3 px-1 text-right">
                {Array.from({ length: lineCount }, (_, i) => (
                  <div key={i} className="text-xs text-gray-600 leading-[1.5rem] h-6">{i + 1}</div>
                ))}
              </div>
            </div>

            {/* Highlight overlay */}
            <pre
              ref={highlightRef}
              className="absolute inset-0 pl-12 pr-4 pt-3 pb-3 overflow-auto whitespace-pre text-gray-300 leading-6 pointer-events-none"
              dangerouslySetInnerHTML={{ __html: highlighted + '\n' }}
              aria-hidden
            />

            {/* Actual textarea */}
            <textarea
              ref={textareaRef}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onScroll={handleScroll}
              spellCheck={false}
              className="absolute inset-0 pl-12 pr-4 pt-3 pb-3 w-full h-full resize-none bg-transparent text-transparent caret-white leading-6 outline-none font-mono text-sm z-20"
              style={{ caretColor: 'white' }}
            />
          </div>

          {/* Parse error bar */}
          {parseResult && !parseResult.valid && (
            <div className="px-4 py-2 bg-red-900/20 border-t border-red-700/30 text-red-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="truncate">{parseResult.error}</span>
            </div>
          )}

          {/* Save modal */}
          {showSave && (
            <div className="px-4 py-3 bg-dark-900/80 border-t border-dark-700 flex items-center gap-3">
              <input
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="Nombre del modelo..."
                className="flex-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-500 outline-none focus:border-purple-500"
                onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                autoFocus
              />
              <button onClick={handleSave} className="px-3 py-1.5 rounded-lg text-xs bg-purple-600/80 text-white hover:bg-purple-500">Guardar</button>
              <button onClick={() => setShowSave(false)} className="px-3 py-1.5 rounded-lg text-xs bg-dark-700 text-gray-400 hover:text-white">Cancelar</button>
            </div>
          )}

          {/* Solver selector + timeout */}
          <div className="px-4 py-2.5 border-t border-dark-700 flex items-center gap-4 bg-dark-900/30">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-gray-400" />
              <select
                value={selectedSolver}
                onChange={(e) => setSelectedSolver(e.target.value)}
                className="bg-dark-700 border border-dark-600 rounded-lg px-2 py-1 text-xs text-gray-300 outline-none"
              >
                <option value="">Auto (primer solver)</option>
                {solvers?.map((s: any) => (
                  <option key={s.key} value={s.key}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <input
                type="number"
                min={1}
                max={300}
                value={timeout}
                onChange={(e) => setTimeout(Number(e.target.value))}
                className="w-16 bg-dark-700 border border-dark-600 rounded-lg px-2 py-1 text-xs text-gray-300 outline-none"
              />
              <span className="text-xs text-gray-500">seg</span>
            </div>
          </div>
        </div>

        {/* ──── RIGHT: RESULTS ──── */}
        <div className="col-span-4 flex flex-col bg-dark-800 border border-dark-700 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700 bg-dark-900/40">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <ChevronRight className="w-4 h-4 text-purple-400" />
              Resultados
            </h3>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Loading */}
            {solveMut.isPending && (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-3" />
                <p className="text-sm text-gray-400">Resolviendo...</p>
              </div>
            )}

            {/* Solve result */}
            {solveResult && !solveMut.isPending && (
              <>
                {/* Result badge */}
                <div className={clsx(
                  'p-4 rounded-xl border text-center',
                  solveResult.result === 'SAT' && 'bg-green-900/20 border-green-700/40',
                  solveResult.result === 'UNSAT' && 'bg-red-900/20 border-red-700/40',
                  solveResult.result === 'TIMEOUT' && 'bg-yellow-900/20 border-yellow-700/40',
                  !['SAT', 'UNSAT', 'TIMEOUT'].includes(solveResult.result) && 'bg-gray-900/20 border-gray-700/40',
                )}>
                  <div className={clsx(
                    'text-3xl font-bold mb-1',
                    solveResult.result === 'SAT' && 'text-green-400',
                    solveResult.result === 'UNSAT' && 'text-red-400',
                    solveResult.result === 'TIMEOUT' && 'text-yellow-400',
                    !['SAT', 'UNSAT', 'TIMEOUT'].includes(solveResult.result) && 'text-gray-400',
                  )}>
                    {solveResult.result}
                  </div>
                  <div className="flex items-center justify-center gap-4 text-xs text-gray-400">
                    <span className="flex items-center gap-1"><Cpu className="w-3 h-3" />{solveResult.solver}</span>
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{solveResult.time_seconds.toFixed(4)}s</span>
                  </div>
                </div>

                {/* Assignment table */}
                {solveResult.assignment && Object.keys(solveResult.assignment).length > 0 && (
                  <div className="bg-dark-900/50 border border-dark-600 rounded-xl overflow-hidden">
                    <div className="px-4 py-2.5 border-b border-dark-700">
                      <h4 className="text-sm font-medium text-white">Asignación satisfactoria</h4>
                    </div>
                    <div className="max-h-60 overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-dark-800/50 sticky top-0">
                          <tr>
                            <th className="px-4 py-2 text-left text-xs text-gray-400 font-medium">Variable</th>
                            <th className="px-4 py-2 text-center text-xs text-gray-400 font-medium">Valor</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-dark-700">
                          {Object.entries(solveResult.assignment).map(([name, val]) => (
                            <tr key={name} className="hover:bg-dark-700/30">
                              <td className="px-4 py-1.5 font-mono text-gray-300">{name}</td>
                              <td className="px-4 py-1.5 text-center">
                                {val ? (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-900/30 text-green-400 text-xs font-medium">
                                    <CheckCircle2 className="w-3 h-3" /> true
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-900/30 text-red-400 text-xs font-medium">
                                    <XCircle className="w-3 h-3" /> false
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* DIMACS stats */}
                {solveResult.dimacs_stats && (
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { label: 'Variables CNF', value: solveResult.dimacs_stats.variables },
                      { label: 'Cláusulas', value: solveResult.dimacs_stats.clauses },
                      { label: 'Vars usuario', value: solveResult.dimacs_stats.user_variables },
                    ].map(s => (
                      <div key={s.label} className="bg-dark-900/50 border border-dark-600 rounded-lg p-2.5 text-center">
                        <div className="text-lg font-bold text-white">{s.value}</div>
                        <div className="text-[10px] text-gray-500">{s.label}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Solver output toggle */}
                <button
                  onClick={() => setShowOutput(!showOutput)}
                  className="w-full text-left px-3 py-2 rounded-lg bg-dark-900/50 border border-dark-600 text-xs text-gray-400 hover:text-white transition-colors flex items-center gap-2"
                >
                  <ChevronRight className={clsx('w-3 h-3 transition-transform', showOutput && 'rotate-90')} />
                  Salida del solver
                </button>
                {showOutput && solveResult.solver_output && (
                  <pre className="p-3 bg-dark-900 rounded-lg border border-dark-600 text-xs text-gray-400 overflow-auto max-h-48 font-mono whitespace-pre-wrap">
                    {solveResult.solver_output}
                  </pre>
                )}
              </>
            )}

            {/* Compile result (DIMACS) */}
            {compileResult && showDimacs && !solveMut.isPending && (
              <>
                <div className="bg-cyan-900/20 border border-cyan-700/30 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-cyan-300">DIMACS CNF</h4>
                    <div className="flex items-center gap-1.5">
                      <button onClick={handleCopyDimacs} className="px-2 py-1 rounded text-xs bg-dark-700 text-gray-300 hover:bg-dark-600 flex items-center gap-1">
                        {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                        {copied ? 'Copiado' : 'Copiar'}
                      </button>
                      <button onClick={handleDownloadDimacs} className="px-2 py-1 rounded text-xs bg-dark-700 text-gray-300 hover:bg-dark-600 flex items-center gap-1">
                        <Download className="w-3 h-3" /> .cnf
                      </button>
                    </div>
                  </div>
                  <pre className="p-3 bg-dark-900 rounded-lg text-xs text-gray-300 font-mono overflow-auto max-h-48 whitespace-pre">
                    {compileResult.dimacs}
                  </pre>
                </div>

                {/* Variable mapping */}
                <div className="bg-dark-900/50 border border-dark-600 rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-dark-700">
                    <h4 className="text-sm font-medium text-white">Mapa de Variables</h4>
                  </div>
                  <div className="max-h-40 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-dark-800/50 sticky top-0">
                        <tr>
                          <th className="px-3 py-1.5 text-left text-gray-400 font-medium">Nombre</th>
                          <th className="px-3 py-1.5 text-right text-gray-400 font-medium">ID DIMACS</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dark-700">
                        {Object.entries(compileResult.variable_map).map(([name, id]) => (
                          <tr key={name} className="hover:bg-dark-700/30">
                            <td className="px-3 py-1 font-mono text-gray-300">{name}</td>
                            <td className="px-3 py-1 text-right font-mono text-purple-300">{id as number}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}

            {/* Empty state */}
            {!solveResult && !compileResult && !solveMut.isPending && (
              <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                <HelpCircle className="w-12 h-12 mb-3 opacity-30" />
                <p className="text-sm font-medium mb-1">Sin resultados aún</p>
                <p className="text-xs text-center max-w-xs">
                  Escribe un modelo o carga un ejemplo, luego pulsa <strong className="text-purple-400">Resolver</strong> o <strong className="text-cyan-400">Compilar</strong>.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
