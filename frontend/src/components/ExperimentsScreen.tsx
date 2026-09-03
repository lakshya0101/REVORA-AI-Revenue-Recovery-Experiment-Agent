import React, { useState } from 'react';
import { Play } from 'lucide-react';
import { api } from '../api/client';
import type { ExperimentRecord } from '../types';

interface ExperimentsScreenProps {
  initialExperiments: ExperimentRecord[];
}

export const ExperimentsScreen: React.FC<ExperimentsScreenProps> = ({
  initialExperiments,
}) => {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>(initialExperiments || []);
  const [sampleSize, setSampleSize] = useState<number>(100);
  const [running, setRunning] = useState<boolean>(false);
  const [selectedExp, setSelectedExp] = useState<ExperimentRecord | null>(
    (initialExperiments && initialExperiments.length > 0) ? initialExperiments[0] : null
  );

  React.useEffect(() => {
    if (initialExperiments && initialExperiments.length > 0) {
      setExperiments(initialExperiments);
      if (!selectedExp) {
        setSelectedExp(initialExperiments[0]);
      }
    }
  }, [initialExperiments]);

  const handleRunExperiment = async () => {
    setRunning(true);
    try {
      const newExp = await api.runExperiment(sampleSize, 42);
      setExperiments([newExp, ...experiments]);
      setSelectedExp(newExp);
    } catch (err) {
      console.error('Failed to run experiment:', err);
    } finally {
      setRunning(false);
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

  const formatPercent = (val?: number) => {
    if (val === undefined || isNaN(val)) return '0.0%';
    return `${(val * 100).toFixed(1)}%`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
            <h1 className="hero-headline">Recovery Experiment Lab</h1>
            <span className="badge badge-amber">COUNTERFACTUAL SIMULATION</span>
          </div>
          <p className="hero-subtitle">
            Compare recovery interventions before changing production behavior.
          </p>
        </div>
      </div>

      {/* Experiment Controls Banner */}
      <div
        className="os-card os-card-elevated"
        style={{
          background: 'linear-gradient(135deg, rgba(0, 210, 255, 0.08) 0%, rgba(9, 16, 33, 0.95) 100%)',
          border: '1px solid var(--border-cyan)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '22px 28px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '28px' }}>
          <div>
            <div style={{ fontSize: '10px', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px', fontFamily: 'var(--font-mono)' }}>
              SAMPLE COHORT SIZE
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <input
                type="range"
                min="10"
                max="1000"
                step="10"
                value={sampleSize}
                onChange={(e) => setSampleSize(Number(e.target.value))}
                style={{ cursor: 'pointer', width: '160px', accentColor: 'var(--cyan-primary)' }}
              />
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '800', fontSize: '16px', color: 'var(--cyan-bright)' }}>
                {sampleSize} cases
              </span>
            </div>
          </div>

          <div style={{ borderLeft: '1px solid var(--border-subtle)', height: '40px' }} />

          <div>
            <div style={{ fontSize: '10px', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px', fontFamily: 'var(--font-mono)' }}>
              COUNTERFACTUAL POLICY COMPARISON
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
              Static Baseline (Always Payment Link) vs <strong style={{ color: '#fff' }}>REVORA Multi-Strategy</strong>
            </div>
          </div>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleRunExperiment}
          disabled={running}
          style={{ padding: '11px 22px', fontSize: '13px' }}
        >
          <Play size={15} />
          <span>{running ? 'Simulating 4 Strategies...' : 'Run Experiment (Explicit Action)'}</span>
        </button>
      </div>

      {/* Selected Experiment Lift Cards */}
      {selectedExp ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '18px' }}>
          <div className="os-card">
            <div className="os-card-title">
              <span>Revora Recovery Rate</span>
              <span className="badge badge-emerald">SIMULATED</span>
            </div>
            <div className="stat-jumbo" style={{ color: 'var(--emerald-bright)' }}>
              {formatPercent(selectedExp.revora_recovery_rate)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
              Baseline: {formatPercent(selectedExp.baseline_recovery_rate)} (
              {(selectedExp.recovery_rate_lift ?? 0) > 0 ? '+' : ''}
              {formatPercent(selectedExp.recovery_rate_lift)} Lift)
            </div>
          </div>

          <div className="os-card">
            <div className="os-card-title">
              <span>Revora Expected Yield</span>
              <span className="badge badge-cyan">PREDICTIVE</span>
            </div>
            <div className="stat-jumbo" style={{ color: 'var(--cyan-bright)' }}>
              {formatCurrency(selectedExp.revora_expected_recovery)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
              Baseline: {formatCurrency(selectedExp.baseline_expected_recovery)}
            </div>
          </div>

          <div className="os-card">
            <div className="os-card-title">
              <span>Revenue Improvement</span>
              <span className="badge badge-emerald">DELTA</span>
            </div>
            <div
              className="stat-jumbo"
              style={{
                color: (selectedExp.revenue_improvement_amount ?? 0) >= 0 ? 'var(--emerald-bright)' : 'var(--text-secondary)',
              }}
            >
              {formatCurrency(selectedExp.revenue_improvement_amount)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
              {(selectedExp.revenue_improvement_percent ?? 0) > 0 ? '+' : ''}
              {(selectedExp.revenue_improvement_percent ?? 0).toFixed(2)}% simulated yield delta
            </div>
          </div>

          <div className="os-card">
            <div className="os-card-title">
              <span>Policy Guardrail Blocks</span>
              <span className="badge badge-amber">GUARDRAILS</span>
            </div>
            <div className="stat-jumbo" style={{ color: 'var(--amber-bright)' }}>
              {selectedExp.policy_blocked_cases ?? 0} cases
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
              Safely defaulted to NO_ACTION by policy
            </div>
          </div>
        </div>
      ) : null}

      {/* Per Strategy Matrix */}
      {selectedExp && selectedExp.strategy_performance && (
        <div className="os-card">
          <div className="os-card-title" style={{ marginBottom: '16px' }}>
            <span>PER-STRATEGY COUNTERFACTUAL BREAKDOWN</span>
            <span className="badge badge-cyan">{selectedExp.sample_size} Case Cohort</span>
          </div>

          <table>
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Selected Cases</th>
                <th>Total Value at Risk</th>
                <th>Expected Recovery</th>
                <th>Simulated Recovered</th>
                <th>Strategy Recovery Rate</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(selectedExp.strategy_performance).map(([strat, metrics]) => (
                <tr key={strat}>
                  <td><strong style={{ fontFamily: 'var(--font-mono)' }}>{strat}</strong></td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{metrics.cases}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{formatCurrency(metrics.total_amount)}</td>
                  <td style={{ color: 'var(--cyan-bright)', fontFamily: 'var(--font-mono)' }}>{formatCurrency(metrics.expected_recovery)}</td>
                  <td style={{ color: 'var(--emerald-bright)', fontWeight: '800', fontFamily: 'var(--font-mono)' }}>
                    {formatCurrency(metrics.simulated_recovered_amount)}
                  </td>
                  <td><strong style={{ fontFamily: 'var(--font-mono)' }}>{formatPercent(metrics.recovery_rate)}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!selectedExp && (
        <div className="os-card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <div style={{ fontSize: '13px', fontWeight: '800', color: 'var(--cyan-bright)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px', fontFamily: 'var(--font-mono)' }}>
            Awaiting Experiment Execution
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', maxWidth: '540px', margin: '0 auto' }}>
            Adjust the sample cohort slider above and click <strong>Run Experiment</strong> to simulate counterfactual multi-strategy recovery vs the static baseline.
          </div>
        </div>
      )}
    </div>
  );
};
