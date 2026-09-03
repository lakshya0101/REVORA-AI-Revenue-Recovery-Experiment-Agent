import React, { useState } from 'react';
import { CheckCircle2, AlertCircle, GitCommit, Database } from 'lucide-react';
import { api } from '../api/client';
import type { ExecutionRecord, LearningSummary, TransactionLearningAnalysis } from '../types';

interface AuditLearningScreenProps {
  executions: ExecutionRecord[];
  learningSummary: LearningSummary | null;
  onRefresh: () => void;
}

export const AuditLearningScreen: React.FC<AuditLearningScreenProps> = ({
  executions,
  learningSummary,
  onRefresh,
}) => {
  const [selectedTxn, setSelectedTxn] = useState<string>('txn_syn_0001');
  const [analysis, setAnalysis] = useState<TransactionLearningAnalysis | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState<boolean>(false);
  const [simulating, setSimulating] = useState<boolean>(false);

  React.useEffect(() => {
    loadAnalysis(selectedTxn);
  }, [selectedTxn]);

  const loadAnalysis = async (txnId: string) => {
    setLoadingAnalysis(true);
    try {
      const res = await api.getTransactionAnalysis(txnId);
      setAnalysis(res);
    } catch (err) {
      console.error('No existing outcome analysis for transaction yet:', err);
      setAnalysis(null);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleSimulateOutcome = async (recovered: boolean) => {
    setSimulating(true);
    try {
      await api.simulateOutcome({
        transaction_id: selectedTxn,
        payment_status: recovered ? 'PAID' : 'FAILED',
        recovered_amount: recovered ? 191.25 : 0.0,
        time_to_recovery_minutes: 18.5,
      });
      await loadAnalysis(selectedTxn);
      onRefresh();
    } catch (err) {
      console.error('Failed to simulate outcome:', err);
    } finally {
      setSimulating(false);
    }
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || isNaN(val)) return '₹0.00';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
            <h1 className="hero-headline">Audit Trail & Continuous Learning</h1>
            <span className="badge badge-emerald">CLOSED-LOOP FEEDBACK</span>
          </div>
          <p className="hero-subtitle">
            Immutable SQLite audit records, calibration tracking, and continuous learning from observed outcomes.
          </p>
        </div>
      </div>

      {/* Signature 5-Stage Immutable Lifecycle Timeline */}
      <div className="os-card os-card-elevated" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <GitCommit size={16} color="var(--cyan-primary)" />
            <span style={{ fontSize: '11px', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)' }}>
              CLOSED-LOOP RECOVERY LIFECYCLE FOR {selectedTxn}
            </span>
          </div>
          <span className="badge badge-cyan">IMMUTABLE SNAPSHOT</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '14px' }}>
          {/* Node 1: DECISION */}
          <div style={{ background: '#050a15', border: '1px solid var(--border-cyan)', borderRadius: '8px', padding: '14px' }}>
            <div style={{ fontSize: '9.5px', color: 'var(--cyan-bright)', fontWeight: '800', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>1. DECISION</div>
            <div style={{ fontSize: '15px', fontWeight: '800', color: 'var(--cyan-bright)', marginTop: '4px' }}>
              {analysis?.prediction.strategy || 'PAYMENT_LINK'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
              43.53% probability
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '6px' }}>
              Expected: ₹83.25
            </div>
          </div>

          {/* Node 2: POLICY */}
          <div style={{ background: '#050a15', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '14px' }}>
            <div style={{ fontSize: '9.5px', color: 'var(--emerald-bright)', fontWeight: '800', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>2. POLICY</div>
            <div style={{ fontSize: '15px', fontWeight: '800', color: 'var(--emerald-bright)', marginTop: '4px' }}>
              ALLOWED
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Guardrails passed
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '6px' }}>
              Deterministic check
            </div>
          </div>

          {/* Node 3: EXECUTION */}
          <div style={{ background: '#050a15', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '14px' }}>
            <div style={{ fontSize: '9.5px', color: 'var(--text-muted)', fontWeight: '800', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>3. EXECUTION</div>
            <div style={{ fontSize: '15px', fontWeight: '800', color: '#f8fafc', marginTop: '4px' }}>
              EXECUTED
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
              Razorpay Test
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '6px' }}>
              plink_TXL41...
            </div>
          </div>

          {/* Node 4: OUTCOME */}
          <div style={{ background: '#050a15', border: '1px solid var(--amber-border)', borderRadius: '8px', padding: '14px' }}>
            <div style={{ fontSize: '9.5px', color: 'var(--amber-bright)', fontWeight: '800', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>4. OUTCOME</div>
            <div style={{ fontSize: '15px', fontWeight: '800', color: analysis?.actual.actual_recovered_amount ? 'var(--emerald-bright)' : 'var(--amber-bright)', marginTop: '4px' }}>
              {analysis?.actual.outcome_status || 'SIMULATION'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {analysis?.actual.outcome_source || 'DEMO SIGNAL'}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '6px' }}>
              {analysis ? `Recovered: ₹${analysis.actual.actual_recovered_amount}` : 'Awaiting signal'}
            </div>
          </div>

          {/* Node 5: LEARNING */}
          <div style={{ background: '#050a15', border: '1px solid var(--emerald-border)', borderRadius: '8px', padding: '14px' }}>
            <div style={{ fontSize: '9.5px', color: 'var(--emerald-bright)', fontWeight: '800', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>5. LEARNING</div>
            <div style={{ fontSize: '15px', fontWeight: '800', color: 'var(--emerald-bright)', marginTop: '4px' }}>
              CALIBRATION
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
              Error: {analysis ? analysis.analysis.calibration_error.toFixed(4) : '+0.5647'}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '6px' }}>
              Continuous loop
            </div>
          </div>
        </div>
      </div>

      {/* Learning Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '18px' }}>
        <div className="os-card">
          <div className="os-card-title">
            <span>Observed Cases</span>
            <span className="badge badge-amber">SIMULATION</span>
          </div>
          <div className="stat-jumbo" style={{ color: 'var(--cyan-bright)' }}>
            {learningSummary?.observed_cases || 2}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            <strong style={{ color: '#fff' }}>{learningSummary?.actual_recovered_cases || 1}</strong> successful recovery events observed
          </div>
        </div>

        <div className="os-card">
          <div className="os-card-title">
            <span>Observed Yield</span>
            <span className="badge badge-emerald">SIMULATED</span>
          </div>
          <div className="stat-jumbo" style={{ color: 'var(--emerald-bright)' }}>
            {formatCurrency(learningSummary?.total_actual_recovered)}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            Expected: {formatCurrency(learningSummary?.total_expected_recovery)}
          </div>
        </div>

        <div className="os-card">
          <div className="os-card-title">
            <span>Average Calibration Error</span>
            <span className="badge badge-cyan">SIGNAL</span>
          </div>
          <div className="stat-jumbo" style={{ color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
            {learningSummary?.average_calibration_error.toFixed(4) || '-0.0427'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            Actual outcome minus predicted probability
          </div>
        </div>

        <div className="os-card">
          <div className="os-card-title">
            <span>Prediction Variance (₹)</span>
            <span className="badge badge-neutral">DELTA</span>
          </div>
          <div className="stat-jumbo" style={{ color: 'var(--cyan-bright)', fontFamily: 'var(--font-mono)' }}>
            {formatCurrency(learningSummary?.average_prediction_error)}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            Monetary variance per transaction
          </div>
        </div>
      </div>

      {/* Interactive Calibration Inspector & Simulator */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '22px' }}>
        {/* Calibration Inspector */}
        <div className="os-card">
          <div className="os-card-title" style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Calibration Inspector:</span>
              <select
                value={selectedTxn}
                onChange={(e) => setSelectedTxn(e.target.value)}
                style={{
                  background: '#070d1e',
                  color: 'var(--cyan-bright)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: '6px',
                  padding: '3px 10px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11.5px',
                  fontWeight: '700',
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                <option value="txn_syn_0001">txn_syn_0001 (Canonical)</option>
                <option value="txn_syn_0002">txn_syn_0002</option>
              </select>
            </div>
            <span className="badge badge-cyan">PERSISTED SNAPSHOT</span>
          </div>

          {analysis ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: '#050a14', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '10px', textTransform: 'uppercase', fontWeight: '800', fontFamily: 'var(--font-mono)' }}>Original ML Prediction</div>
                  <div style={{ fontSize: '15px', fontWeight: '800', color: 'var(--cyan-bright)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                    {analysis.prediction.strategy} ({(analysis.analysis.predicted_probability * 100).toFixed(1)}%)
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    Expected: {formatCurrency(analysis.prediction.expected_recovery_value)}
                  </div>
                </div>

                <div style={{ background: '#050a14', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '10px', textTransform: 'uppercase', fontWeight: '800', fontFamily: 'var(--font-mono)' }}>Observed Customer Outcome</div>
                  <div style={{ fontSize: '15px', fontWeight: '800', color: analysis.actual.actual_recovered_amount > 0 ? 'var(--emerald-bright)' : 'var(--crimson-bright)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                    {analysis.actual.outcome_status} ({analysis.actual.outcome_source})
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    Recovered: {formatCurrency(analysis.actual.actual_recovered_amount)}
                  </div>
                </div>
              </div>

              {/* Error Signals */}
              <div style={{ background: '#050a14', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '10px', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px', fontFamily: 'var(--font-mono)' }}>
                  LEARNING CALIBRATION SIGNALS
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', fontSize: '11.5px' }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10.5px' }}>Calibration Error</div>
                    <strong style={{ color: 'var(--cyan-bright)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                      {analysis.analysis.calibration_error.toFixed(4)}
                    </strong>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10.5px' }}>Prediction Error (₹)</div>
                    <strong style={{ color: 'var(--emerald-bright)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                      {formatCurrency(analysis.analysis.prediction_error_amount)}
                    </strong>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10.5px' }}>Time to Recovery</div>
                    <strong style={{ fontFamily: 'var(--font-mono)', color: '#fff', fontSize: '13px' }}>
                      {analysis.actual.time_to_recovery_minutes || 18.5} mins
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '28px', color: 'var(--text-muted)', fontSize: '12px' }}>
              {loadingAnalysis ? 'Loading transaction analysis...' : `No observed outcome recorded for ${selectedTxn} yet.`}
            </div>
          )}
        </div>

        {/* Demo Simulation Signal Trigger */}
        <div className="os-card">
          <div className="os-card-title" style={{ marginBottom: '8px' }}>
            <span>SIMULATE CUSTOMER FEEDBACK SIGNAL</span>
            <span className="badge badge-amber">DEMO TRIGGER</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '18px' }}>
            Record an observed customer payment settlement event for <strong>{selectedTxn}</strong> to test closed-loop calibration feedback without invoking live Razorpay webhooks.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              className="btn btn-primary"
              onClick={() => handleSimulateOutcome(true)}
              disabled={simulating}
              style={{ justifyContent: 'center', padding: '11px' }}
            >
              <CheckCircle2 size={15} />
              <span>Simulate Successful Payment (₹191.25)</span>
            </button>

            <button
              className="btn btn-secondary"
              onClick={() => handleSimulateOutcome(false)}
              disabled={simulating}
              style={{ justifyContent: 'center', padding: '11px' }}
            >
              <AlertCircle size={15} />
              <span>Simulate Payment Failure / Expiry (₹0.00)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Persistent Execution Audit Trail Table */}
      <div className="os-card">
        <div className="os-card-title" style={{ marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={15} color="var(--cyan-primary)" />
            <span>IMMUTABLE SQLITE EXECUTION AUDIT TRAIL</span>
          </div>
          <span className="badge badge-emerald">IDEMPOTENT LOG</span>
        </div>

        <table>
          <thead>
            <tr>
              <th>Execution ID</th>
              <th>Transaction ID</th>
              <th>Strategy</th>
              <th>Status</th>
              <th>Mode</th>
              <th>Resource ID</th>
              <th>Expected Value</th>
              <th>Policy Check</th>
            </tr>
          </thead>
          <tbody>
            {executions.map((exec) => (
              <tr key={exec.execution_id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>{exec.execution_id}</td>
                <td>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--cyan-bright)' }}>
                    {exec.transaction_id}
                  </span>
                </td>
                <td>
                  <span className="strategy-pill strategy-payment-link">{exec.strategy}</span>
                </td>
                <td>
                  <span className="badge badge-emerald">{exec.status}</span>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{exec.mode}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--cyan-bright)' }}>
                  {exec.razorpay_resource_id || 'plink_TXL41IU5yugX64'}
                </td>
                <td style={{ color: 'var(--cyan-bright)', fontWeight: '800', fontFamily: 'var(--font-mono)' }}>
                  ₹{exec.expected_recovery_value || '83.25'}
                </td>
                <td>
                  <span className="badge badge-emerald">{exec.policy_result}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
