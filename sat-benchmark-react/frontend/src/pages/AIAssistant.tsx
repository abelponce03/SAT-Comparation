import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { 
  Brain, 
  Send, 
  Sparkles, 
  FileCode, 
  MessageSquare, 
  Lightbulb,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Copy,
  Download,
  Trash2,
  RefreshCw,
  ChevronDown,
  Zap,
  BookOpen,
  Code2
} from 'lucide-react';
import toast from 'react-hot-toast';
import LoadingSpinner from '@/components/common/LoadingSpinner';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface GeneratedFile {
  name: string;
  path: string;
  size: number;
  created: string;
  num_variables: number | null;
  num_clauses: number | null;
}

interface ExampleProblem {
  name: string;
  description: string;
  type: string;
  sample_input: {
    problem_description: string;
    constraints?: string[];
    variables?: Record<string, string>;
    num_variables?: number;
  };
}

export default function AIAssistant() {
  const [activeTab, setActiveTab] = useState<'chat' | 'generate' | 'analyze'>('chat');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '¡Hola! Soy tu asistente de IA especializado en problemas SAT. Puedo ayudarte a:\n\n• **Analizar problemas** para determinar si pueden formularse como SAT\n• **Generar archivos CNF** a partir de descripciones de problemas\n• **Explicar resultados** de SAT solvers\n• **Responder preguntas** sobre SAT, CNF, CDCL, y más\n\n¿En qué puedo ayudarte hoy?',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [problemDescription, setProblemDescription] = useState('');
  const [constraints, setConstraints] = useState<string[]>(['']);
  const [selectedModel, setSelectedModel] = useState<string>('llama3.2');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Queries
  const { data: aiStatus, isLoading: loadingStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['ai-status'],
    queryFn: async () => {
      const response = await fetch('/api/ai/status');
      return response.json();
    },
    refetchInterval: 30000 // Check every 30 seconds
  });

  const { data: generatedFiles, refetch: refetchFiles } = useQuery({
    queryKey: ['generated-files'],
    queryFn: async () => {
      const response = await fetch('/api/ai/generated-files');
      return response.json() as Promise<GeneratedFile[]>;
    }
  });

  const { data: examples } = useQuery({
    queryKey: ['ai-examples'],
    queryFn: async () => {
      const response = await fetch('/api/ai/examples');
      return response.json() as Promise<ExampleProblem[]>;
    }
  });

  // Mutations
  const chatMutation = useMutation({
    mutationFn: async (userMessage: string) => {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages.filter(m => m.role !== 'system'), { role: 'user', content: userMessage }].map(m => ({
            role: m.role,
            content: m.content
          })),
          model: selectedModel
        })
      });
      if (!response.ok) throw new Error('Chat failed');
      return response.json();
    },
    onSuccess: (data) => {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date()
      }]);
    },
    onError: () => toast.error('Error al comunicarse con la IA')
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/ai/generate-cnf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          problem_description: problemDescription,
          constraints: constraints.filter(c => c.trim()),
          model: selectedModel,
          save_to_file: true
        })
      });
      if (!response.ok) throw new Error('Generation failed');
      return response.json();
    },
    onSuccess: (data) => {
      if (data.cnf_parsed) {
        toast.success(`CNF generado: ${data.num_variables} variables, ${data.num_clauses} cláusulas`);
        refetchFiles();
      } else {
        toast.error('No se pudo parsear el CNF generado');
      }
    },
    onError: () => toast.error('Error al generar CNF')
  });

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/ai/analyze-problem', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          problem_description: problemDescription,
          model: selectedModel
        })
      });
      if (!response.ok) throw new Error('Analysis failed');
      return response.json();
    },
    onError: () => toast.error('Error al analizar problema')
  });

  const deleteFileMutation = useMutation({
    mutationFn: async (filename: string) => {
      const response = await fetch(`/api/ai/generated-files/${filename}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Delete failed');
      return response.json();
    },
    onSuccess: () => {
      toast.success('Archivo eliminado');
      refetchFiles();
    }
  });

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = () => {
    if (!inputMessage.trim() || chatMutation.isPending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    chatMutation.mutate(inputMessage);
    setInputMessage('');
  };

  const handleCopyCNF = (content: string) => {
    navigator.clipboard.writeText(content);
    toast.success('CNF copiado al portapapeles');
  };

  const loadExample = (example: ExampleProblem) => {
    setProblemDescription(example.sample_input.problem_description);
    if (example.sample_input.constraints) {
      setConstraints(example.sample_input.constraints);
    }
    toast.success(`Ejemplo "${example.name}" cargado`);
  };

  if (loadingStatus) {
    return <LoadingSpinner size="lg" text="Conectando con el servicio de IA..." />;
  }

  const isOllamaOnline = aiStatus?.ollama?.status === 'online';
  const availableModels = aiStatus?.ollama?.models || [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-purple-600/30 to-pink-600/30 rounded-xl border border-purple-500/30">
              <Brain className="w-8 h-8 text-purple-400" />
            </div>
            Asistente IA
          </h1>
          <p className="text-gray-400 mt-2">
            Genera CNF, analiza problemas y aprende sobre SAT
          </p>
        </div>

        {/* AI Status */}
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
            isOllamaOnline 
              ? 'bg-green-900/20 border-green-600/30' 
              : 'bg-red-900/20 border-red-600/30'
          }`}>
            {isOllamaOnline ? (
              <CheckCircle2 className="w-5 h-5 text-green-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400" />
            )}
            <span className={isOllamaOnline ? 'text-green-400' : 'text-red-400'}>
              Ollama {isOllamaOnline ? 'Online' : 'Offline'}
            </span>
            <button onClick={() => refetchStatus()} className="ml-2 p-1 hover:bg-dark-700 rounded">
              <RefreshCw className="w-4 h-4 text-gray-400" />
            </button>
          </div>

          {isOllamaOnline && availableModels.length > 0 && (
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="input py-2 w-40"
            >
              {availableModels.map((model: string) => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Offline Warning */}
      {!isOllamaOnline && (
        <div className="bg-red-900/20 border border-red-600/30 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-400">Ollama no está disponible</h3>
              <p className="text-sm text-gray-400 mt-1">
                Para usar el asistente de IA, necesitas tener Ollama ejecutándose localmente.
              </p>
              <code className="block mt-2 bg-dark-900 px-3 py-2 rounded text-sm text-gray-300">
                ollama serve
              </code>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-dark-700 pb-2">
        {[
          { id: 'chat', label: 'Chat', icon: MessageSquare },
          { id: 'generate', label: 'Generar CNF', icon: FileCode },
          { id: 'analyze', label: 'Analizar', icon: Lightbulb }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-primary-600/20 text-primary-400 border-b-2 border-primary-500'
                : 'text-gray-400 hover:text-white hover:bg-dark-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {activeTab === 'chat' && (
            <div className="bg-dark-800/50 border border-dark-700 rounded-xl flex flex-col h-[600px]">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] p-4 rounded-xl ${
                        message.role === 'user'
                          ? 'bg-primary-600/30 border border-primary-600/30 text-white'
                          : 'bg-dark-700/50 border border-dark-600 text-gray-200'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        {message.role === 'assistant' && (
                          <Sparkles className="w-4 h-4 text-purple-400" />
                        )}
                        <span className="text-xs text-gray-500">
                          {message.role === 'user' ? 'Tú' : 'Asistente'}
                        </span>
                      </div>
                      <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap">
                        {message.content}
                      </div>
                    </div>
                  </div>
                ))}
                {chatMutation.isPending && (
                  <div className="flex justify-start">
                    <div className="bg-dark-700/50 border border-dark-600 p-4 rounded-xl">
                      <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-4 border-t border-dark-700">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                    placeholder="Pregunta sobre SAT, CNF, o pide ayuda..."
                    className="input flex-1"
                    disabled={!isOllamaOnline || chatMutation.isPending}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!isOllamaOnline || !inputMessage.trim() || chatMutation.isPending}
                    className="btn-primary"
                  >
                    {chatMutation.isPending ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'generate' && (
            <div className="space-y-4">
              <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-primary-400" />
                  Generar CNF desde Descripción
                </h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Descripción del Problema
                    </label>
                    <textarea
                      value={problemDescription}
                      onChange={(e) => setProblemDescription(e.target.value)}
                      placeholder="Describe tu problema de restricciones... Por ejemplo: Colorea un grafo de 4 vértices con 3 colores de manera que vértices adyacentes no tengan el mismo color."
                      className="input h-32 resize-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Restricciones (opcional)
                    </label>
                    {constraints.map((constraint, idx) => (
                      <div key={idx} className="flex gap-2 mb-2">
                        <input
                          type="text"
                          value={constraint}
                          onChange={(e) => {
                            const newConstraints = [...constraints];
                            newConstraints[idx] = e.target.value;
                            setConstraints(newConstraints);
                          }}
                          placeholder={`Restricción ${idx + 1}`}
                          className="input flex-1"
                        />
                        {idx === constraints.length - 1 ? (
                          <button
                            onClick={() => setConstraints([...constraints, ''])}
                            className="btn-secondary"
                          >
                            +
                          </button>
                        ) : (
                          <button
                            onClick={() => setConstraints(constraints.filter((_, i) => i !== idx))}
                            className="btn-secondary text-red-400"
                          >
                            ×
                          </button>
                        )}
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => generateMutation.mutate()}
                    disabled={!isOllamaOnline || !problemDescription.trim() || generateMutation.isPending}
                    className="btn-primary w-full"
                  >
                    {generateMutation.isPending ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin mr-2" />
                        Generando CNF...
                      </>
                    ) : (
                      <>
                        <Zap className="w-5 h-5 mr-2" />
                        Generar CNF
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Generation Result */}
              {generateMutation.data && (
                <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Code2 className="w-5 h-5 text-green-400" />
                    Resultado
                  </h3>

                  {generateMutation.data.cnf_parsed ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-4 text-sm">
                        <span className="px-3 py-1 bg-primary-600/20 text-primary-300 rounded-lg">
                          {generateMutation.data.num_variables} variables
                        </span>
                        <span className="px-3 py-1 bg-green-600/20 text-green-300 rounded-lg">
                          {generateMutation.data.num_clauses} cláusulas
                        </span>
                        {generateMutation.data.saved_to && (
                          <span className="px-3 py-1 bg-blue-600/20 text-blue-300 rounded-lg">
                            Guardado ✓
                          </span>
                        )}
                      </div>

                      <div className="bg-dark-900 rounded-lg p-4">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-sm text-gray-400">CNF (DIMACS)</span>
                          <button
                            onClick={() => handleCopyCNF(generateMutation.data.cnf_content)}
                            className="text-gray-400 hover:text-white"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                        </div>
                        <pre className="text-sm text-gray-300 overflow-x-auto max-h-60">
                          {generateMutation.data.cnf_content}
                        </pre>
                      </div>

                      <div className="bg-dark-900/50 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-gray-300 mb-2">Explicación de la IA:</h4>
                        <div className="text-sm text-gray-400 whitespace-pre-wrap max-h-40 overflow-y-auto">
                          {generateMutation.data.ai_response}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-yellow-400">
                      <AlertCircle className="w-5 h-5 inline mr-2" />
                      No se pudo parsear el CNF automáticamente. Revisa la respuesta:
                      <pre className="mt-2 text-sm text-gray-400 whitespace-pre-wrap">
                        {generateMutation.data.ai_response}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'analyze' && (
            <div className="space-y-4">
              <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-yellow-400" />
                  Analizar Problema SAT
                </h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Descripción del Problema
                    </label>
                    <textarea
                      value={problemDescription}
                      onChange={(e) => setProblemDescription(e.target.value)}
                      placeholder="Describe el problema que quieres analizar..."
                      className="input h-32 resize-none"
                    />
                  </div>

                  <button
                    onClick={() => analyzeMutation.mutate()}
                    disabled={!isOllamaOnline || !problemDescription.trim() || analyzeMutation.isPending}
                    className="btn-primary w-full"
                  >
                    {analyzeMutation.isPending ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin mr-2" />
                        Analizando...
                      </>
                    ) : (
                      <>
                        <Lightbulb className="w-5 h-5 mr-2" />
                        Analizar Compatibilidad SAT
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Analysis Result */}
              {analyzeMutation.data && (
                <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`p-2 rounded-lg ${
                      analyzeMutation.data.is_sat_compatible === 'YES'
                        ? 'bg-green-600/20'
                        : analyzeMutation.data.is_sat_compatible === 'NO'
                        ? 'bg-red-600/20'
                        : 'bg-yellow-600/20'
                    }`}>
                      {analyzeMutation.data.is_sat_compatible === 'YES' ? (
                        <CheckCircle2 className="w-6 h-6 text-green-400" />
                      ) : analyzeMutation.data.is_sat_compatible === 'NO' ? (
                        <AlertCircle className="w-6 h-6 text-red-400" />
                      ) : (
                        <Lightbulb className="w-6 h-6 text-yellow-400" />
                      )}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">
                        {analyzeMutation.data.is_sat_compatible === 'YES'
                          ? 'Compatible con SAT'
                          : analyzeMutation.data.is_sat_compatible === 'NO'
                          ? 'No compatible con SAT'
                          : 'Parcialmente compatible'}
                      </h3>
                    </div>
                  </div>

                  <div className="bg-dark-900/50 rounded-lg p-4">
                    <div className="text-sm text-gray-300 whitespace-pre-wrap">
                      {analyzeMutation.data.analysis}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Examples */}
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary-400" />
              Problemas de Ejemplo
            </h3>
            <div className="space-y-2">
              {examples?.map((example: ExampleProblem) => (
                <button
                  key={example.name}
                  onClick={() => loadExample(example)}
                  className="w-full text-left p-3 bg-dark-700/50 hover:bg-dark-700 rounded-lg transition-colors group"
                >
                  <div className="font-medium text-white text-sm group-hover:text-primary-400">
                    {example.name}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{example.type}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Generated Files */}
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <FileCode className="w-4 h-4 text-green-400" />
              Archivos CNF Generados
            </h3>
            {generatedFiles && generatedFiles.length > 0 ? (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {generatedFiles.map((file: GeneratedFile) => (
                  <div
                    key={file.name}
                    className="p-3 bg-dark-700/50 rounded-lg group"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1 min-w-0">
                        <div className="font-mono text-sm text-white truncate">
                          {file.name}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {file.num_variables && file.num_clauses && (
                            <span>{file.num_variables}v / {file.num_clauses}c</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => deleteFileMutation.mutate(file.name)}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-600/20 rounded text-red-400 transition-opacity"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-500 text-sm py-4">
                No hay archivos generados
              </div>
            )}
          </div>

          {/* Quick Tips */}
          <div className="bg-gradient-to-br from-primary-900/30 to-purple-900/30 border border-primary-600/30 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-white mb-3">💡 Tips</h3>
            <ul className="text-xs text-gray-400 space-y-2">
              <li>• Describe las variables claramente</li>
              <li>• Especifica todas las restricciones</li>
              <li>• Usa problemas pequeños para probar</li>
              <li>• Verifica el CNF generado</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
