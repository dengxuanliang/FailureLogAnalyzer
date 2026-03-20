// === Auth ===

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface JwtPayload {
  sub: string; // user UUID
  role: "admin" | "analyst" | "viewer";
  exp: number;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

// === Sessions ===

export interface EvalSession {
  id: string;
  model: string;
  model_version: string;
  benchmark: string;
  dataset_name: string | null;
  total_count: number;
  error_count: number;
  accuracy: number;
  tags: string[];
  created_at: string;
}

// === Analysis ===

export interface AnalysisSummary {
  total_sessions: number;
  total_records: number;
  total_errors: number;
  accuracy: number;
  llm_analysed_count: number;
  llm_total_cost: number;
}

export interface DistributionItem {
  label: string;
  count: number;
  percentage: number;
}

export interface ErrorRecordBrief {
  id: string;
  session_id: string;
  benchmark: string;
  task_category: string | null;
  question_id: string | null;
  question: string;
  is_correct: boolean;
  score: number | null;
  error_tags: string[];
  has_llm_analysis: boolean;
}

export interface PaginatedRecords {
  items: ErrorRecordBrief[];
  total: number;
  page: number;
  size: number;
}

export interface AnalysisResultDetail {
  id: string;
  analysis_type: string;
  error_types: string[];
  root_cause: string | null;
  severity: string | null;
  confidence: number | null;
  evidence: string | null;
  suggestion: string | null;
  llm_model: string | null;
  llm_cost: number | null;
  unmatched_tags: string[];
  created_at: string;
}

export interface RecordDetail {
  record: Record<string, unknown>;
  analysis_results: AnalysisResultDetail[];
  error_tags: Record<string, unknown>[];
}

// === Trends ===

export interface TrendPoint {
  period: string;
  error_rate: number;
  total: number;
  errors: number;
}

export interface ErrorTrends {
  data_points: TrendPoint[];
}

// === Compare ===

export interface VersionMetrics {
  total: number;
  errors: number;
  accuracy: number;
  error_type_distribution: Record<string, number>;
}

export interface VersionComparison {
  version_a: string;
  version_b: string;
  benchmark: string | null;
  metrics_a: VersionMetrics;
  metrics_b: VersionMetrics;
}

export interface DiffItem {
  question_id: string;
  benchmark: string;
  task_category: string | null;
  question: string;
}

export interface VersionDiff {
  regressed: DiffItem[];
  improved: DiffItem[];
  new_errors: string[];
  resolved_errors: string[];
}

export interface RadarData {
  dimensions: string[];
  scores_a: number[];
  scores_b: number[];
}

// === Cross-Benchmark ===

export interface BenchmarkMatrix {
  models: string[];
  benchmarks: string[];
  matrix: number[][];
}

export interface Weakness {
  error_type: string;
  benchmarks: string[];
  frequency: number;
}

export interface SystematicWeaknesses {
  weaknesses: Weakness[];
}

// === Global Filters ===

export interface GlobalFilters {
  benchmark: string | null;
  model_version: string | null;
  time_range_start: string | null;
  time_range_end: string | null;
}
