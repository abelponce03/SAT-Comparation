import React, { useState, useEffect } from 'react';
import { Settings, Play, Database, Search, LayoutDashboard, Cpu, CheckCircle } from 'lucide-react';
import { tuningApi, solversApi } from '../services/api';
import type { Solver } from '../types';

export default function Tuning() {
  const [solvers, setSolvers] = useState<Solver[]>([]);
  const [selectedSolver, setSelectedSolver] = useState<string>('');
  
  // A simple placeholder for instances. In a real scenario, fetch these from benchmarksApi
  const [instancesConfig, setInstancesConfig] = useState<string>('random_3sat');
  
  const [timeoutPerRun, setTimeoutPerRun] = useState<number>(100);
  const [maxEvaluations, setMaxEvaluations] = useState<number>(30);
  
  const [tuningJobId, setTuningJobId] = useState<string | null>(null);
  const [tuningStatus, setTuningStatus] = useState<string>('');
  const [incumbentConfig, setIncumbentConfig] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  
  const [ablationJobId, setAblationJobId] = useState<string | null>(null);
  const [ablationStatus, setAblationStatus] = useState<string>('');
  const [ablationResults, setAblationResults] = useState<any>(null);

  useEffect(() => {
    loadSolvers();
  }, []);

  const loadSolvers = async () => {
    try {
      const data = await solversApi.getAll('READY');
      setSolvers(data);
      if (data.length > 0) setSelectedSolver(data[0].key || data[0].name);
    } catch (error) {
      console.error("Error loading solvers:", error);
    }
  };

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (tuningJobId && (tuningStatus === 'pending' || tuningStatus === 'running')) {
      interval = setInterval(async () => {
        try {
          const status = await tuningApi.getTuningStatus(tuningJobId);
          setTuningStatus(status.status);
          if (status.status === 'completed') {
            setIncumbentConfig(status.incumbent);
          } else if (status.status === 'error') {
            setErrorMsg(status.error);
          }
        } catch (e) {
          console.error(e);
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [tuningJobId, tuningStatus]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (ablationJobId && (ablationStatus === 'pending' || ablationStatus === 'running')) {
      interval = setInterval(async () => {
        try {
          const status = await tuningApi.getAblationStatus(ablationJobId);
          setAblationStatus(status.status);
          if (status.status === 'completed') {
            setAblationResults(status.results);
          }
        } catch (e) {
          console.error(e);
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [ablationJobId, ablationStatus]);


  const getInstancesList = () => {
    // Return dummy list based on selection
    if (instancesConfig === 'random_3sat') return ['/data/benchmarks/rand_3sat_1.cnf', '/data/benchmarks/rand_3sat_2.cnf'];
    return ['/data/benchmarks/hard_1.cnf'];
  };

  const handleStartTuning = async () => {
    try {
      setErrorMsg('');
      setIncumbentConfig(null);
      setAblationResults(null);
      
      const req = {
        solver_name: selectedSolver,
        instances: getInstancesList(),
        timeout_per_run: timeoutPerRun,
        max_evaluations: maxEvaluations
      };
      
      const res = await tuningApi.startTuning(req);
      setTuningJobId(res.job_id);
      setTuningStatus('pending');
    } catch (err: any) {
      setErrorMsg(err.message || 'Error starting tuning');
    }
  };

  const handleStartAblation = async () => {
    try {
      if (!incumbentConfig) return;
      const req = {
        solver_name: selectedSolver,
        instances: getInstancesList(),
        timeout_per_run: timeoutPerRun,
        incumbent_config: incumbentConfig
      };
      const res = await tuningApi.startAblation(req);
      setAblationJobId(res.job_id);
      setAblationStatus('pending');
    } catch (err: any) {
      setErrorMsg(err.message || 'Error starting ablation');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 border-l-4 border-indigo-500 pl-3">
            Algorithm Configuration (SMAC3)
          </h1>
          <p className="text-gray-500 mt-2">
            Ajuste automatizado de hiperparámetros y Análisis de Ablación
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Panel de Configuración */}
        <div className="bg-white shadow rounded-lg p-6 flex flex-col gap-4 border border-gray-200">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Settings className="w-5 h-5 text-indigo-600" /> Parámetros
          </h2>

          <div>
            <label className="block text-sm font-medium text-gray-700">Solver</label>
            <select 
              value={selectedSolver}
              onChange={(e) => setSelectedSolver(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
              disabled={tuningStatus === 'running'}
            >
              {solvers.map(s => (
                <option key={s.id} value={s.key || s.name}>{s.name} ({s.version})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Dataset de Instancias</label>
            <select 
              value={instancesConfig}
              onChange={(e) => setInstancesConfig(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
              disabled={tuningStatus === 'running'}
            >
              <option value="random_3sat">Random 3-SAT (Demo)</option>
              <option value="hard_combinatorial">Hard Combinatorial (Demo)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Timeout por Evaluación (s)</label>
            <input 
              type="number" 
              value={timeoutPerRun}
              onChange={(e) => setTimeoutPerRun(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
              disabled={tuningStatus === 'running'}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Max Evaluaciones</label>
            <input 
              type="number" 
              value={maxEvaluations}
              onChange={(e) => setMaxEvaluations(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
              disabled={tuningStatus === 'running'}
            />
          </div>

          <button
            onClick={handleStartTuning}
            disabled={tuningStatus === 'running' || tuningStatus === 'pending'}
            className="mt-4 w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
          >
            {tuningStatus === 'running' ? 'Tuning en Progreso...' : 'Iniciar Tuning'}
          </button>

          {errorMsg && (
            <div className="p-3 bg-red-50 text-red-700 text-sm rounded-md">
              {errorMsg}
            </div>
          )}
        </div>

        {/* Panel de Resultados */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="bg-white shadow rounded-lg p-6 border border-gray-200 min-h-[250px]">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <Search className="w-5 h-5 text-green-600" /> Resultados del Tuning
            </h2>
            
            {!tuningJobId && !incumbentConfig && (
              <div className="text-gray-400 text-sm italic">Configura y ejecuta un job para visualizar los resultados.</div>
            )}

            {(tuningStatus === 'running' || tuningStatus === 'pending') && (
               <div className="flex items-center gap-3 text-indigo-600">
                 <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600"></div>
                 Poblando espacio de configuraciones mediante SMAC3... esto puede tomar tiempo.
               </div>
            )}

            {incumbentConfig && (
              <div className="space-y-4">
                <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                  <h3 className="text-green-800 font-bold flex items-center gap-2">
                    <CheckCircle className="w-5 h-5"/> ¡Incumbent Founds! (Mejor Configuración Global)
                  </h3>
                  <pre className="mt-3 bg-gray-900 text-green-400 p-3 rounded text-sm overflow-x-auto">
                    {JSON.stringify(incumbentConfig, null, 2)}
                  </pre>
                </div>
                
                <div className="pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-600 mb-3">
                    Desglosa probabilísticamente qué hiperparámetro generó la mayor mejora usando Análisis de Ablación.
                  </p>
                  <button
                    onClick={handleStartAblation}
                    disabled={ablationStatus === 'running' || ablationStatus === 'pending'}
                    className="flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 disabled:bg-gray-400"
                  >
                     {ablationStatus === 'running' ? 'Calculando Ablación...' : 'Ejecutar Análisis de Ablación'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Panel de Ablation */}
          {ablationJobId && (
            <div className="bg-white shadow rounded-lg p-6 border border-gray-200">
              <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <Database className="w-5 h-5 text-purple-600" /> Resultados de Ablación
              </h2>
              
              {(ablationStatus === 'running' || ablationStatus === 'pending') && (
                <div className="flex items-center gap-3 text-purple-600 mb-4">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600"></div>
                  Simulando flujos aislados sobre el Baseline PAR-2...
                </div>
              )}

              {ablationResults && (
                <div className="space-y-3">
                   <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                      <div className="bg-gray-50 p-3 rounded border text-center">
                        <div className="text-xs text-gray-500 uppercase">Baseline PAR-2</div>
                        <div className="text-lg font-bold">{ablationResults.baseline_default_score.toFixed(2)}s</div>
                      </div>
                      <div className="bg-indigo-50 p-3 rounded border text-center">
                        <div className="text-xs text-indigo-500 uppercase">Incumbent PAR-2</div>
                        <div className="text-lg font-bold text-indigo-700">{ablationResults.incumbent_score.toFixed(2)}s</div>
                      </div>
                      <div className="bg-green-50 p-3 rounded border col-span-2 text-center">
                        <div className="text-xs text-green-600 uppercase">Mejora Total PAR-2</div>
                        <div className="text-xl font-bold text-green-700">-{ablationResults.total_improvement.toFixed(2)}s 🔥</div>
                      </div>
                   </div>

                   <h3 className="font-semibold text-gray-800">Impacto Individual de Parámetros:</h3>
                   <div className="overflow-x-auto">
                     <table className="min-w-full divide-y divide-gray-200">
                       <thead className="bg-gray-50">
                         <tr>
                           <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Parámetro</th>
                           <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Default ➔ Nuevo</th>
                           <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mejora Independiente</th>
                           <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">% del Total Ganado</th>
                         </tr>
                       </thead>
                       <tbody className="bg-white divide-y divide-gray-200">
                         {Object.entries(ablationResults.parameters_impact).map(([param, data]: [string, any]) => (
                           <tr key={param}>
                             <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{param}</td>
                             <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                               <span className="line-through text-red-400 mr-2">{String(data.default_value)}</span>
                               <span className="text-green-600 font-bold">{String(data.incumbent_value)}</span>
                             </td>
                             <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                               {data.improvement > 0 ? `-${data.improvement.toFixed(2)}s` : `+${Math.abs(data.improvement).toFixed(2)}s (Peor)`}
                             </td>
                             <td className="px-6 py-4 whitespace-nowrap">
                               <div className="w-full bg-gray-200 rounded-full h-2.5">
                                 <div 
                                    className="bg-purple-600 h-2.5 rounded-full" 
                                    style={{ width: `${Math.max(0, Math.min(100, data.percentage_of_total_gain))}%` }}
                                  ></div>
                               </div>
                               <span className="text-xs text-gray-500 mt-1">{data.percentage_of_total_gain.toFixed(1)}%</span>
                             </td>
                           </tr>
                         ))}
                       </tbody>
                     </table>
                   </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
