import type {
  DatasetStats,
  DecisionOutput,
  EvaluatedOptions,
  ExecutionRecord,
  ExperimentRecord,
  ExplanationResponse,
  LearningSummary,
  ModelEvaluation,
  RazorpayConnectionStatus,
  TransactionLearningAnalysis,
} from '../types';

const BASE_URL = 'http://localhost:8000';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errBody.detail || `API request failed: ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Razorpay
  checkRazorpay: () => fetchJson<RazorpayConnectionStatus>('/api/razorpay/test'),

  // Dataset
  getDatasetStats: () => fetchJson<DatasetStats>('/api/dataset/stats'),

  // Recovery Engine & Predictions
  getModelEvaluation: () => fetchJson<ModelEvaluation>('/api/recovery/evaluation'),
  predictTransactionId: (txnId: string) => fetchJson<DecisionOutput>(`/api/recovery/predict/${txnId}`),
  evaluateOptions: (payload: any) =>
    fetchJson<EvaluatedOptions>('/api/recovery/evaluate-options', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Execution & Dry Run
  dryRunRecovery: (txnId: string) =>
    fetchJson<any>(`/api/recovery/dry-run/${txnId}`, { method: 'POST' }),
  executeRecovery: (txnId: string) =>
    fetchJson<any>(`/api/recovery/execute/${txnId}`, { method: 'POST' }),
  listExecutions: () => fetchJson<ExecutionRecord[]>('/api/recovery/executions'),

  // Experiments
  listExperiments: () => fetchJson<ExperimentRecord[]>('/api/experiments'),
  runExperiment: (sampleSize = 100, seed = 42) =>
    fetchJson<ExperimentRecord>('/api/experiments/run', {
      method: 'POST',
      body: JSON.stringify({ sample_size: sampleSize, seed }),
    }),

  // LLM Explanations
  explainDecision: (txnId: string) =>
    fetchJson<ExplanationResponse>(`/api/explanations/decision/${txnId}`, { method: 'POST' }),
  explainWhyNot: (txnId: string, alternativeStrategy: string) =>
    fetchJson<ExplanationResponse>(`/api/explanations/why-not/${txnId}`, {
      method: 'POST',
      body: JSON.stringify({ alternative_strategy: alternativeStrategy }),
    }),
  explainPolicy: (txnId: string) =>
    fetchJson<ExplanationResponse>(`/api/explanations/policy/${txnId}`, { method: 'POST' }),
  explainExecution: (txnId: string) =>
    fetchJson<ExplanationResponse>(`/api/explanations/execution/${txnId}`, { method: 'POST' }),

  // Outcomes & Learning
  getOutcomeStatus: (txnId: string) => fetchJson<any>(`/api/outcomes/${txnId}`),
  simulateOutcome: (payload: { transaction_id: string; payment_status: string; recovered_amount: number; time_to_recovery_minutes?: number }) =>
    fetchJson<any>('/api/outcomes/simulate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getLearningSummary: (source = 'SIMULATION') =>
    fetchJson<LearningSummary>(`/api/learning/summary?outcome_source=${source}`),
  getTransactionAnalysis: (txnId: string) =>
    fetchJson<TransactionLearningAnalysis>(`/api/learning/transaction/${txnId}`),
};
