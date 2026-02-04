import axios from 'axios';
import type { 
  Solver, SolverCreate, 
  Benchmark, BenchmarkFamily,
  Experiment, ExperimentCreate, Run,
  DashboardStats
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==================== Dashboard ====================

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const { data } = await api.get('/dashboard/stats');
    return data;
  },
  
  getRecentActivity: async (limit = 10) => {
    const { data } = await api.get(`/dashboard/recent-activity?limit=${limit}`);
    return data;
  },
};

// ==================== Solvers ====================

export const solversApi = {
  getAll: async (status?: string): Promise<Solver[]> => {
    const params = status ? `?status=${status}` : '';
    const { data } = await api.get(`/solvers${params}`);
    return data;
  },
  
  getById: async (id: number): Promise<Solver> => {
    const { data } = await api.get(`/solvers/${id}`);
    return data;
  },
  
  create: async (solver: SolverCreate) => {
    const { data } = await api.post('/solvers', solver);
    return data;
  },
  
  update: async (id: number, updates: Partial<Solver>) => {
    const { data } = await api.put(`/solvers/${id}`, updates);
    return data;
  },
  
  delete: async (id: number) => {
    const { data } = await api.delete(`/solvers/${id}`);
    return data;
  },
  
  compile: async (id: number, compileCommand?: string) => {
    const { data } = await api.post(`/solvers/${id}/compile`, { 
      compile_command: compileCommand 
    });
    return data;
  },
  
  test: async (id: number) => {
    const { data } = await api.post(`/solvers/${id}/test`);
    return data;
  },
  
  getTemplates: async () => {
    const { data } = await api.get('/solvers/templates/list');
    return data;
  },
  
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/solvers/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
};

// ==================== Benchmarks ====================

export const benchmarksApi = {
  getAll: async (family?: string, difficulty?: string, limit?: number): Promise<Benchmark[]> => {
    const params = new URLSearchParams();
    if (family) params.append('family', family);
    if (difficulty) params.append('difficulty', difficulty);
    if (limit) params.append('limit', limit.toString());
    
    const { data } = await api.get(`/benchmarks?${params}`);
    return data;
  },
  
  getById: async (id: number): Promise<Benchmark> => {
    const { data } = await api.get(`/benchmarks/${id}`);
    return data;
  },
  
  getFamilies: async (): Promise<BenchmarkFamily[]> => {
    const { data } = await api.get('/benchmarks/families');
    return data;
  },
  
  getStats: async () => {
    const { data } = await api.get('/benchmarks/stats');
    return data;
  },
  
  preview: async (id: number, lines = 50) => {
    const { data } = await api.get(`/benchmarks/${id}/preview?lines=${lines}`);
    return data;
  },
  
  delete: async (id: number) => {
    const { data } = await api.delete(`/benchmarks/${id}`);
    return data;
  },
  
  upload: async (files: File[]) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    const { data } = await api.post('/benchmarks/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  
  scan: async (directory?: string) => {
    const { data } = await api.post('/benchmarks/scan', null, {
      params: directory ? { directory } : {},
    });
    return data;
  },
};

// ==================== Experiments ====================

export const experimentsApi = {
  getAll: async (status?: string): Promise<Experiment[]> => {
    const params = status ? `?status=${status}` : '';
    const { data } = await api.get(`/experiments/${params}`);
    return data;
  },
  
  getById: async (id: number): Promise<Experiment> => {
    const { data } = await api.get(`/experiments/${id}`);
    return data;
  },
  
  create: async (experiment: ExperimentCreate) => {
    const { data } = await api.post('/experiments', experiment);
    return data;
  },
  
  update: async (id: number, updates: Partial<Experiment>) => {
    const { data } = await api.put(`/experiments/${id}`, updates);
    return data;
  },
  
  delete: async (id: number) => {
    const { data } = await api.delete(`/experiments/${id}`);
    return data;
  },
  
  start: async (id: number) => {
    const { data } = await api.post(`/experiments/${id}/start`);
    return data;
  },
  
  stop: async (id: number) => {
    const { data } = await api.post(`/experiments/${id}/stop`);
    return data;
  },
  
  getProgress: async (id: number) => {
    const { data } = await api.get(`/experiments/${id}/progress`);
    return data;
  },
  
  getRuns: async (id: number): Promise<Run[]> => {
    const { data } = await api.get(`/experiments/${id}/runs`);
    return data;
  },
};

// ==================== Analysis ====================

export const analysisApi = {
  getSummary: async (experimentId?: number) => {
    const params = experimentId ? `?experiment_id=${experimentId}` : '';
    const { data } = await api.get(`/analysis/summary${params}`);
    return data;
  },
  
  getPAR2: async (experimentId: number, timeout = 5000): Promise<any> => {
    const params = new URLSearchParams();
    params.append('experiment_id', experimentId.toString());
    params.append('timeout', timeout.toString());
    
    const { data } = await api.get(`/analysis/par2?${params}`);
    return data;
  },
  
  getVBS: async (experimentId: number, timeout = 5000): Promise<any> => {
    const params = new URLSearchParams();
    params.append('experiment_id', experimentId.toString());
    params.append('timeout', timeout.toString());
    
    const { data } = await api.get(`/analysis/vbs?${params}`);
    return data;
  },
  
  getPairwise: async (experimentId: number): Promise<any> => {
    const { data } = await api.get(`/analysis/pairwise?experiment_id=${experimentId}`);
    return data;
  },
  
  getByFamily: async (experimentId: number): Promise<any> => {
    const { data } = await api.get(`/analysis/by-family?experiment_id=${experimentId}`);
    return data;
  },
  
  // Visualization endpoints
  getCactusData: async (experimentId: number, timeout = 5000): Promise<any> => {
    const params = new URLSearchParams();
    params.append('experiment_id', experimentId.toString());
    params.append('timeout', timeout.toString());
    
    const { data } = await api.get(`/analysis/cactus?${params}`);
    return data;
  },
  
  getScatterData: async (experimentId: number): Promise<any> => {
    const { data } = await api.get(`/analysis/scatter?experiment_id=${experimentId}`);
    return data;
  },
  
  getECDFData: async (experimentId: number): Promise<any> => {
    const { data } = await api.get(`/analysis/ecdf?experiment_id=${experimentId}`);
    return data;
  },
  
  getHeatmapData: async (experimentId: number): Promise<any> => {
    const { data } = await api.get(`/analysis/heatmap?experiment_id=${experimentId}`);
    return data;
  },
  
  getPerformanceProfile: async (experimentId: number, maxRatio = 10): Promise<any> => {
    const params = new URLSearchParams();
    params.append('experiment_id', experimentId.toString());
    params.append('max_ratio', maxRatio.toString());
    
    const { data } = await api.get(`/analysis/performance-profile?${params}`);
    return data;
  },
  
  getFamilyAnalysis: async (experimentId: number) => {
    const { data } = await api.get(`/analysis/family-analysis?experiment_id=${experimentId}`);
    return data;
  },
  
  exportResults: async (experimentId: number, format = 'csv') => {
    const { data } = await api.get(`/analysis/export?experiment_id=${experimentId}&format=${format}`, {
      responseType: 'blob',
    });
    return data;
  },
};

export default api;
