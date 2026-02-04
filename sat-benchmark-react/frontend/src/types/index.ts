// Solver types
export interface Solver {
  id: number;
  name: string;
  version: string | null;
  executable_path: string;
  source_path: string | null;
  compile_command: string | null;
  run_command_template: string | null;
  last_compiled: string | null;
  status: 'ready' | 'needs_compile' | 'compiling' | 'error';
  description: string | null;
  metadata: Record<string, any> | null;
  created_at: string;
}

export interface SolverCreate {
  name: string;
  executable_path: string;
  version?: string;
  source_path?: string;
  compile_command?: string;
  run_command_template?: string;
  description?: string;
}

// Benchmark types
export interface Benchmark {
  id: number;
  filename: string;
  filepath: string;
  family: string;
  size_bytes: number;
  num_variables: number | null;
  num_clauses: number | null;
  clause_variable_ratio: number | null;
  difficulty: 'easy' | 'medium' | 'hard' | 'unknown';
  expected_result: string | null;
  tags: string | null;
  checksum: string | null;
  created_at: string;
}

export interface BenchmarkFamily {
  family: string;
  count: number;
  avg_variables: number;
  avg_clauses: number;
}

// Experiment types
export interface Experiment {
  id: number;
  name: string;
  description: string | null;
  status: 'pending' | 'running' | 'completed' | 'stopped' | 'error';
  timeout_seconds: number;
  memory_limit_mb: number;
  parallel_jobs: number;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  metadata: Record<string, any> | null;
  result_distribution?: Record<string, number>;
  runs_count?: number;
}

export interface ExperimentCreate {
  name: string;
  description?: string;
  timeout_seconds: number;
  memory_limit_mb: number;
  parallel_jobs: number;
  solver_ids: number[];
  benchmark_ids: number[];
}

// Run types
export interface Run {
  id: number;
  experiment_id: number;
  solver_id: number;
  benchmark_id: number;
  solver_name: string;
  benchmark_name: string;
  benchmark_family: string;
  experiment_name: string;
  result: 'SAT' | 'UNSAT' | 'TIMEOUT' | 'MEMOUT' | 'ERROR' | 'UNKNOWN';
  exit_code: number;
  verified: boolean;
  cpu_time_seconds: number | null;
  wall_time_seconds: number | null;
  max_memory_kb: number | null;
  conflicts: number | null;
  decisions: number | null;
  propagations: number | null;
  restarts: number | null;
  timestamp: string;
  solver_output: string | null;
  error_message: string | null;
}

// Analysis types
export interface PAR2Scores {
  timeout: number;
  penalty_factor: number;
  scores: Record<string, number>;
  best_solver: string | null;
}

export interface VBSAnalysis {
  vbs_average_time: number;
  total_benchmarks: number;
  solver_contribution: Record<string, number>;
  best_contributor: string | null;
}

export interface PairwiseComparison {
  solver1: string;
  solver2: string;
  common_benchmarks: number;
  both_solved: number;
  ties: number;
  geometric_speedup: number;
  interpretation: string;
}

export interface SolvedCounts {
  [solver: string]: {
    total: number;
    sat: number;
    unsat: number;
    timeout: number;
    error: number;
    solved: number;
    solved_pct: number;
  };
}

// Chart data types
export interface CactusDataPoint {
  x: number;
  y: number;
}

export interface CactusSeries {
  name: string;
  data: CactusDataPoint[];
  total_solved: number;
}

export interface ScatterPoint {
  benchmark: string;
  x: number;
  y: number;
  result: string;
}

// Dashboard types
export interface DashboardStats {
  total_solvers: number;
  ready_solvers: number;
  total_benchmarks: number;
  total_experiments: number;
  total_runs: number;
  sat_results: number;
  unsat_results: number;
  timeout_results: number;
  recent_experiments: Experiment[];
}
