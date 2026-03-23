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

export interface SessionDetail extends EvalSession {
  updated_at: string;
}

export interface SessionDeleteResponse {
  session_id: string;
  deleted: boolean;
}

export interface SessionActionResponse {
  session_id: string;
  job_id: string;
  message: string;
}

// === Operations / Jobs ===

export interface IngestUploadPayload {
  file: globalThis.File;
  benchmark: string;
  model: string;
  model_version: string;
  adapter_name?: string;
  session_id?: string;
}

export interface IngestUploadResponse {
  job_id: string;
  session_id: string;
  message: string;
}

export interface IngestJobStatus {
  job_id: string;
  session_id: string;
  file_path: string;
  status: string;
  processed: number;
  total: number | null;
  total_written: number;
  total_skipped: number;
  reason?: string;
  created_at: number;
}

export interface LlmJobTriggerPayload {
  session_id: string;
  strategy_id: string;
  manual_record_ids?: string[];
  expect_manual_records?: boolean;
}

export interface LlmJobTriggerResponse {
  job_id: string;
  celery_task_id: string;
  status: string;
}

export interface LlmJobStatus {
  job_id: string;
  session_id: string;
  strategy_id: string;
  status: string;
  processed: number;
  total: number | null;
  succeeded: number;
  failed: number;
  total_cost: number;
  stop_reason: string | null;
  reason: string;
  celery_task_id?: string | null;
  created_at: number;
  updated_at: number;
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

export interface MatrixCell {
  model_version: string;
  benchmark: string;
  error_rate: number;
  error_count: number;
  total_count: number;
}

export interface CrossBenchmarkMatrix {
  model_versions: string[];
  benchmarks: string[];
  cells: MatrixCell[];
}

export interface CommonErrorPattern {
  error_type: string;
  affected_benchmarks: string[];
  avg_error_rate: number;
  record_count: number;
}

export interface WeaknessReport {
  generated_at: string;
  summary: string;
  common_patterns: CommonErrorPattern[];
}

// === Analysis Config ===

export type RuleConditionType =
  | "regex"
  | "contains"
  | "not_contains"
  | "length_gt"
  | "length_lt"
  | "field_equals"
  | "field_missing"
  | "python_expr";

export interface RuleCondition {
  type: RuleConditionType;
  pattern?: string;
  value?: string | number;
  threshold?: number;
}

export interface AnalysisRule {
  id: string;
  name: string;
  description: string;
  field: string;
  condition: RuleCondition;
  tags: string[];
  confidence: number;
  priority: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export type AnalysisRuleCreate = Omit<
  AnalysisRule,
  "id" | "created_by" | "created_at" | "updated_at"
>;
export type AnalysisRuleUpdate = Partial<AnalysisRuleCreate>;

export type LLMStrategyType = "full" | "fallback" | "sample" | "manual";

export interface AnalysisStrategy {
  id: string;
  name: string;
  strategy_type: LLMStrategyType;
  config: Record<string, unknown>;
  llm_provider: string;
  llm_model: string;
  prompt_template_id: string | null;
  max_concurrent: number;
  daily_budget: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export type AnalysisStrategyCreate = Omit<
  AnalysisStrategy,
  "id" | "created_by" | "created_at" | "updated_at"
>;
export type AnalysisStrategyUpdate = Partial<AnalysisStrategyCreate>;

export interface PromptTemplate {
  id: string;
  name: string;
  benchmark: string | null;
  template: string;
  version: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
}

// === Reports ===

export type ReportType = "summary" | "comparison" | "cross_benchmark" | "custom";
export type ReportStatus = "pending" | "generating" | "done" | "failed";

export interface ReportListItem {
  id: string;
  title: string;
  report_type: ReportType;
  status: ReportStatus;
  benchmark: string | null;
  model_version: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportDetail extends ReportListItem {
  session_ids: string[] | null;
  time_range_start: string | null;
  time_range_end: string | null;
  content: Record<string, unknown>;
  error_message: string | null;
}

export interface ReportExportPayload {
  blob: globalThis.Blob;
  filename: string;
}

export type PromptTemplateCreate = Omit<
  PromptTemplate,
  "id" | "version" | "created_by" | "created_at"
>;
export type PromptTemplateUpdate = Partial<PromptTemplateCreate>;

export interface BenchmarkAdapter {
  name: string;
  description: string;
  detected_fields: string[];
  is_builtin: boolean;
}

export type UserRole = "admin" | "analyst" | "viewer";

export interface UserInfo {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role: UserRole;
}

export type UserUpdate = Partial<Omit<UserCreate, "username">> & {
  is_active?: boolean;
};

// === Global Filters ===

export interface GlobalFilters {
  benchmark: string | null;
  model_version: string | null;
  time_range_start: string | null;
  time_range_end: string | null;
}
