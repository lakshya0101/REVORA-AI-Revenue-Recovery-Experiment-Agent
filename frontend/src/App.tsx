import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  ListOrdered,
  Cpu,
  History,
  FlaskConical,
  RefreshCw,
  Zap,
  Shield,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import { api } from './api/client';
import type { DatasetStats, ModelEvaluation, LearningSummary, ExecutionRecord, ExperimentRecord } from './types';
import { OverviewScreen } from './components/OverviewScreen';
import { RecoveryQueueScreen } from './components/RecoveryQueueScreen';
import { AgentConsoleScreen } from './components/AgentConsoleScreen';
import { ExperimentsScreen } from './components/ExperimentsScreen';
import { AuditLearningScreen } from './components/AuditLearningScreen';

export const App: React.FC = () => {
  const [currentScreen, setCurrentScreen] = useState<'OVERVIEW' | 'QUEUE' | 'CONSOLE' | 'EXPERIMENTS' | 'AUDIT'>('OVERVIEW');
  const [selectedTxnId, setSelectedTxnId] = useState<string>('txn_syn_0001');

  // App-wide state from real backend
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [evalMetrics, setEvalMetrics] = useState<ModelEvaluation | null>(null);
  const [learningSummary, setLearningSummary] = useState<LearningSummary | null>(null);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [razorpayStatus, setRazorpayStatus] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [st, ev, ls, ex, exp, rzp] = await Promise.all([
        api.getDatasetStats(),
        api.getModelEvaluation(),
        api.getLearningSummary('SIMULATION').catch(() => null),
        api.listExecutions(),
        api.listExperiments(),
        api.checkRazorpay().catch(() => ({ connected: false })),
      ]);

      setStats(st);
      setEvalMetrics(ev);
      setLearningSummary(ls);
      setExecutions(ex);
      setExperiments(exp);
      setRazorpayStatus(!!rzp.connected);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigateToConsole = (txnId: string) => {
    setSelectedTxnId(txnId);
    setCurrentScreen('CONSOLE');
  };

  return (
    <div className="app-container">
      {/* Persistent Precision Sidebar */}
      <aside className="sidebar">
        {/* Brand Crest */}
        <div className="brand-crest">
          <div className="brand-logo-wrap">
            <div className="brand-icon-box">
              <Zap size={16} />
            </div>
            <span className="brand-title">REVORA</span>
          </div>
          <div className="brand-subtitle">
            AI REVENUE RECOVERY AGENT
          </div>
        </div>

        {/* Navigation Rail */}
        <nav style={{ flex: 1, padding: '16px 0' }}>
          <div
            className={`nav-item ${currentScreen === 'OVERVIEW' ? 'active' : ''}`}
            onClick={() => setCurrentScreen('OVERVIEW')}
          >
            <span className="nav-index">01</span>
            <LayoutDashboard size={17} />
            <span>Overview</span>
          </div>

          <div
            className={`nav-item ${currentScreen === 'QUEUE' ? 'active' : ''}`}
            onClick={() => setCurrentScreen('QUEUE')}
          >
            <span className="nav-index">02</span>
            <ListOrdered size={17} />
            <span>Recovery Queue</span>
          </div>

          <div
            className={`nav-item ${currentScreen === 'CONSOLE' ? 'active' : ''}`}
            onClick={() => setCurrentScreen('CONSOLE')}
          >
            <span className="nav-index">03</span>
            <Cpu size={17} />
            <span>Agent Console</span>
          </div>

          <div
            className={`nav-item ${currentScreen === 'EXPERIMENTS' ? 'active' : ''}`}
            onClick={() => setCurrentScreen('EXPERIMENTS')}
          >
            <span className="nav-index">04</span>
            <FlaskConical size={17} />
            <span>Experiments</span>
          </div>

          <div
            className={`nav-item ${currentScreen === 'AUDIT' ? 'active' : ''}`}
            onClick={() => setCurrentScreen('AUDIT')}
          >
            <span className="nav-index">05</span>
            <History size={17} />
            <span>Audit & Learning</span>
          </div>
        </nav>

        {/* Bottom Sidebar: Razorpay Gateway Indicator */}
        <div className="gateway-footer">
          <div className="gateway-label">
            <span className="gateway-text">GATEWAY CONNECTION</span>
            <span className={`live-dot ${razorpayStatus ? 'live-dot-emerald' : 'live-dot-cyan'}`} />
          </div>
          <div style={{ fontSize: '12px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '0.01em' }}>
            Razorpay Test Mode
          </div>
          <div
            style={{
              fontSize: '10.5px',
              color: razorpayStatus ? 'var(--emerald-bright)' : 'var(--amber-bright)',
              fontFamily: 'var(--font-mono)',
              fontWeight: '700',
              marginTop: '3px',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            {razorpayStatus ? (
              <>
                <CheckCircle2 size={11} /> ACTIVE & AUTHENTICATED
              </>
            ) : (
              '● TEST ENVIRONMENT ONLY'
            )}
          </div>
        </div>
      </aside>

      {/* Main Command Workspace */}
      <div className="main-content">
        {/* Top Command Bar */}
        <header className="top-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <span style={{ fontSize: '12px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              SYSTEM // {currentScreen}
            </span>
            <span style={{ color: 'var(--border-subtle)' }}>/</span>
            <span className="badge badge-cyan" style={{ fontSize: '9.5px' }}>
              Razorpay AI Buildathon 2026
            </span>
            <span style={{ color: 'var(--border-subtle)' }}>/</span>
            <span className="badge badge-amber" style={{ fontSize: '9.5px' }}>
              RAZORPAY TEST MODE · SIMULATION
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              className="btn btn-secondary"
              onClick={loadAllData}
              disabled={loading}
              style={{ fontSize: '11.5px', padding: '6px 14px' }}
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              <span>Sync Engine</span>
            </button>
          </div>
        </header>

        {/* Content Workspace */}
        <main className="workspace">
          {/* Signature System Living Pipeline Strip */}
          <div className="pipeline-strip">
            <div className="pipeline-track">
              <span className="pipeline-label">
                <Activity size={12} color="var(--cyan-primary)" />
                AGENT LIFECYCLE:
              </span>

              <span className="pipeline-node-link active" title="Real-time transaction failure interception">
                <span className="live-dot live-dot-cyan" /> DETECT
              </span>
              <span className="pipeline-connector-arrow">──→</span>

              <span className="pipeline-node-link active" title="ML Multi-Strategy Classification & Expected Yield">
                DECIDE
              </span>
              <span className="pipeline-connector-arrow">──→</span>

              <span className="pipeline-node-link active" title="Deterministic Merchant Guardrail Verification">
                <Shield size={11} /> POLICY
              </span>
              <span className="pipeline-connector-arrow">──→</span>

              <span className="pipeline-node-link active" title="Controlled Safe Execution via Razorpay Test API">
                EXECUTE
              </span>
              <span className="pipeline-connector-arrow">──→</span>

              <span className="pipeline-node-link success" title="Settlement Monitoring & Customer Response">
                OBSERVE
              </span>
              <span className="pipeline-connector-arrow">──→</span>

              <span className="pipeline-node-link success" title="Immutable SQLite Audit Record & Idempotency Key">
                AUDIT
              </span>
              <span className="pipeline-connector-arrow">──→</span>

              <span className="pipeline-node-link success" title="Calibration Error Feedback & Model Learning Loop">
                LEARN
              </span>
            </div>
          </div>

          {/* Screen Routing */}
          {currentScreen === 'OVERVIEW' && (
            <OverviewScreen
              stats={stats}
              evalMetrics={evalMetrics}
              learningSummary={learningSummary}
              onNavigateToConsole={handleNavigateToConsole}
            />
          )}

          {currentScreen === 'QUEUE' && (
            <RecoveryQueueScreen
              executions={executions}
              onSelectTransaction={handleNavigateToConsole}
            />
          )}

          {currentScreen === 'CONSOLE' && (
            <AgentConsoleScreen
              transactionId={selectedTxnId}
              onTransactionChange={setSelectedTxnId}
            />
          )}

          {currentScreen === 'EXPERIMENTS' && (
            <ExperimentsScreen initialExperiments={experiments} />
          )}

          {currentScreen === 'AUDIT' && (
            <AuditLearningScreen
              executions={executions}
              learningSummary={learningSummary}
              onRefresh={loadAllData}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
