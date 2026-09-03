export interface DatasetStats {
  total_cases: number;
  total_revenue_at_risk: number;
  recoverable_revenue: number;
  historical_recovery_rate: number;
  strategy_distribution: Record<string, number>;
  failure_reason_distribution: Record<string, number>;
  customer_type_distribution: Record<string, number>;
  order_value_segment_distribution: Record<string, number>;
}

export interface ModelEvaluation {
  model: {
    algorithm: string;
    train_size: number;
    test_size: number;
    accuracy: number;
    precision_macro: number;
    recall_macro: number;
    f1_macro: number;
    confusion_matrix: number[][];
    labels: string[];
  };
  baseline: {
    strategy: string;
    accuracy: number;
  };
  improvement: number;
  recovery_probability: {
    mae: number;
    rmse: number;
  };
  revenue: {
    test_revenue_at_risk: number;
    predicted_expected_recovery: number;
    actual_recovered_revenue: number;
    ground_truth_recovery_rate: number;
  };
}

export interface DecisionOutput {
  transaction_id: string;
  recommended_strategy: 'RETRY' | 'PAYMENT_LINK' | 'ALTERNATE_FLOW' | 'NO_ACTION';
  strategy_confidence: number;
  predicted_recovery_probability: number;
  expected_recovery_value: number;
  reason_codes: string[];
}

export interface StrategyOption {
  recovery_probability: number;
  expected_recovery_value: number;
}

export interface EvaluatedOptions {
  transaction_id: string;
  strategies: Record<string, StrategyOption>;
  recommended_strategy: string;
  strategy_confidence: number;
  predicted_recovery_probability: number;
  expected_recovery_value: number;
  policy_result: 'ALLOWED' | 'POLICY_BLOCKED';
  reason_codes: string[];
  audit_event: Record<string, any>;
}

export interface ExperimentRecord {
  experiment_id: string;
  sample_size: number;
  total_revenue_at_risk: number;
  baseline_recovery_rate: number;
  revora_recovery_rate: number;
  recovery_rate_lift: number;
  baseline_expected_recovery: number;
  revora_expected_recovery: number;
  revenue_improvement_amount: number;
  revenue_improvement_percent: number;
  strategy_distribution: Record<string, number>;
  strategy_performance: Record<
    string,
    {
      cases: number;
      total_amount: number;
      expected_recovery: number;
      simulated_recovered_amount: number;
      recovery_rate: number;
    }
  >;
  policy_blocked_cases: number;
  created_at?: string;
}

export interface ExecutionRecord {
  execution_id: string;
  transaction_id: string;
  strategy: string;
  status: string;
  mode: string;
  strategy_confidence?: number;
  predicted_recovery_probability?: number;
  expected_recovery_value?: number;
  reason_codes?: string[];
  razorpay_resource_id?: string;
  short_url?: string;
  amount: number;
  policy_result: string;
  created_at?: string;
  audit_data?: Record<string, any>;
}

export interface ExplanationResponse {
  transaction_id: string;
  type: string;
  strategy: string;
  explanation: string;
  structured_explanation?: {
    summary: string;
    why_this_strategy: string;
    expected_outcome: string;
    risk_note: string;
    merchant_action: string;
    full_text: string;
  };
  evidence?: {
    confidence: number;
    predicted_recovery_probability: number;
    expected_recovery_value: number;
    reason_codes: string[];
  };
  provider: string;
  model: string;
  fallback_used: boolean;
  audit_event?: Record<string, any>;
}

export interface LearningSummary {
  observed_cases: number;
  actual_recovered_cases: number;
  actual_recovery_rate: number;
  total_value_at_risk: number;
  total_expected_recovery: number;
  total_actual_recovered: number;
  average_prediction_error: number;
  average_calibration_error: number;
  average_time_to_recovery_minutes: number;
  strategy_performance: Record<
    string,
    {
      cases: number;
      recovered: number;
      total_amount: number;
      expected_recovery: number;
      actual_recovered_amount: number;
      recovery_rate: number;
    }
  >;
}

export interface TransactionLearningAnalysis {
  transaction_id: string;
  prediction: {
    strategy: string;
    predicted_recovery_probability: number;
    expected_recovery_value: number;
  };
  actual: {
    outcome_status: string;
    outcome_source: string;
    actual_recovered_amount: number;
    time_to_recovery_minutes?: number;
    observed_at?: string;
  };
  analysis: {
    predicted_probability: number;
    actual_success: boolean;
    calibration_error: number;
    expected_recovery_value: number;
    actual_recovered_amount: number;
    prediction_error_amount: number;
    absolute_error_amount: number;
  };
}

export interface RazorpayConnectionStatus {
  connected: boolean;
  message: string;
  orders_count: number;
}
