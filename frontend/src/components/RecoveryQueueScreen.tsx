import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, Clock, Search } from 'lucide-react';
import type { ExecutionRecord } from '../types';

interface QueueItem {
  transaction_id: string;
  amount: number;
  failure_reason: string;
  payment_method: string;
  customer_type: string;
  strategy: 'RETRY' | 'PAYMENT_LINK' | 'ALTERNATE_FLOW' | 'NO_ACTION';
  confidence: number;
  probability: number;
  expected_value: number;
  policy: 'ALLOWED' | 'POLICY_BLOCKED';
}

const CANONICAL_QUEUE: QueueItem[] = [
  {
    transaction_id: 'txn_syn_0001',
    amount: 191.25,
    failure_reason: 'INCORRECT_OTP',
    payment_method: 'DEBIT_CARD',
    customer_type: 'FIRST_TIME',
    strategy: 'PAYMENT_LINK',
    confidence: 0.8885,
    probability: 0.4353,
    expected_value: 83.25,
    policy: 'ALLOWED',
  },
  {
    transaction_id: 'txn_syn_0002',
    amount: 3500.56,
    failure_reason: 'CHECKOUT_DROPOFF',
    payment_method: 'UPI',
    customer_type: 'RETURNING',
    strategy: 'PAYMENT_LINK',
    confidence: 0.912,
    probability: 0.8145,
    expected_value: 2851.21,
    policy: 'ALLOWED',
  },
  {
    transaction_id: 'txn_syn_0003',
    amount: 664.78,
    failure_reason: 'INSUFFICIENT_FUNDS',
    payment_method: 'NET_BANKING',
    customer_type: 'FIRST_TIME',
    strategy: 'NO_ACTION',
    confidence: 0.941,
    probability: 0.02,
    expected_value: 0.0,
    policy: 'ALLOWED',
  },
  {
    transaction_id: 'txn_syn_0004',
    amount: 941.99,
    failure_reason: 'INCORRECT_OTP',
    payment_method: 'CREDIT_CARD',
    customer_type: 'RETURNING',
    strategy: 'PAYMENT_LINK',
    confidence: 0.845,
    probability: 0.6237,
    expected_value: 587.52,
    policy: 'ALLOWED',
  },
  {
    transaction_id: 'txn_syn_0005',
    amount: 125000.0,
    failure_reason: 'AUTHENTICATION_TIMEOUT',
    payment_method: 'NET_BANKING',
    customer_type: 'RETURNING',
    strategy: 'NO_ACTION',
    confidence: 0.95,
    probability: 0.88,
    expected_value: 0.0,
    policy: 'POLICY_BLOCKED',
  },
];

interface RecoveryQueueScreenProps {
  onSelectTransaction: (txnId: string) => void;
  executions: ExecutionRecord[];
}

export const RecoveryQueueScreen: React.FC<RecoveryQueueScreenProps> = ({
  onSelectTransaction,
  executions,
}) => {
  const [strategyFilter, setStrategyFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');

  const executedTxnIds = new Set(executions.map((e) => e.transaction_id));

  const filteredQueue = CANONICAL_QUEUE.filter((item) => {
    if (
      search &&
      !item.transaction_id.toLowerCase().includes(search.toLowerCase()) &&
      !item.failure_reason.toLowerCase().includes(search.toLowerCase())
    ) {
      return false;
    }
    
    // Strategy Filter
    if (strategyFilter !== 'ALL' && item.strategy !== strategyFilter) {
      return false;
    }

    // Status Filter (conceptually separate)
    const isExecuted = executedTxnIds.has(item.transaction_id);
    const isBlockedOrFailed = item.policy === 'POLICY_BLOCKED';
    if (statusFilter === 'EXECUTED' && !isExecuted) return false;
    if (statusFilter === 'PENDING' && (isExecuted || isBlockedOrFailed)) return false;
    if (statusFilter === 'FAILED' && !isBlockedOrFailed) return false;

    return true;
  });

  const getStrategyClass = (strategy: string) => {
    switch (strategy) {
      case 'PAYMENT_LINK':
        return 'strategy-payment-link';
      case 'RETRY':
        return 'strategy-retry';
      case 'ALTERNATE_FLOW':
        return 'strategy-alternate-flow';
      default:
        return 'strategy-no-action';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '26px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
            <h1 className="hero-headline">At-Risk Recovery Queue</h1>
            <span className="badge badge-cyan">OPERATIONAL TRIAGE</span>
          </div>
          <p className="hero-subtitle">
            Prioritized salvage queue ordered by failure interception risk and predicted monetary recovery yield.
          </p>
        </div>

        {/* Search */}
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            placeholder="Search ID or reason..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: '#070d1e',
              border: '1px solid var(--border-medium)',
              borderRadius: '7px',
              padding: '7px 12px 7px 32px',
              fontSize: '12px',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)',
              outline: 'none',
              width: '200px',
            }}
          />
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '9px' }} />
        </div>
      </div>

      {/* Two-Dimensional Filter Control Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#050a14',
          border: '1px solid var(--border-subtle)',
          borderRadius: '8px',
          padding: '12px 18px',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        {/* Dimension 1: Filter By Strategy */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '10px', color: 'var(--cyan-bright)', fontWeight: '800', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)' }}>
            FILTER BY STRATEGY:
          </span>
          {['ALL', 'PAYMENT_LINK', 'RETRY', 'ALTERNATE_FLOW', 'NO_ACTION'].map((f) => (
            <button
              key={f}
              className={`btn ${strategyFilter === f ? 'btn-outline-cyan' : 'btn-secondary'}`}
              style={{ fontSize: '10.5px', padding: '5px 10px' }}
              onClick={() => setStrategyFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Dimension 2: Filter By Execution Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderLeft: '1px solid var(--border-medium)', paddingLeft: '16px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '10px', color: 'var(--emerald-bright)', fontWeight: '800', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)' }}>
            FILTER BY EXECUTION STATUS:
          </span>
          {['ALL', 'PENDING', 'EXECUTED', 'FAILED'].map((s) => (
            <button
              key={s}
              className={`btn ${statusFilter === s ? 'btn-outline-cyan' : 'btn-secondary'}`}
              style={{ fontSize: '10.5px', padding: '5px 10px' }}
              onClick={() => setStatusFilter(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="os-card" style={{ padding: '0px', overflow: 'hidden' }}>
        <table>
          <thead>
            <tr>
              <th>Transaction ID</th>
              <th>Amount</th>
              <th>Failure Signal</th>
              <th>Recommended Action</th>
              <th>Confidence</th>
              <th>Recovery Prob.</th>
              <th>Expected Recovery</th>
              <th>Policy Check</th>
              <th>State</th>
              <th>Triage Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredQueue.map((item) => {
              const isExecuted = executedTxnIds.has(item.transaction_id);

              return (
                <tr key={item.transaction_id}>
                  <td>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: '700',
                        color: item.transaction_id === 'txn_syn_0001' ? 'var(--cyan-bright)' : 'var(--text-primary)',
                      }}
                    >
                      {item.transaction_id}
                    </span>
                    {item.transaction_id === 'txn_syn_0001' && (
                      <span className="badge badge-cyan" style={{ marginLeft: '8px', fontSize: '9px' }}>
                        CANONICAL
                      </span>
                    )}
                  </td>
                  <td>
                    <strong style={{ fontFamily: 'var(--font-mono)', color: '#fff' }}>₹{item.amount.toFixed(2)}</strong>
                  </td>
                  <td>
                    <span className="badge badge-amber" style={{ fontSize: '10px' }}>
                      {item.failure_reason}
                    </span>
                  </td>
                  <td>
                    <span className={`strategy-pill ${getStrategyClass(item.strategy)}`}>
                      {item.strategy}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      {(item.confidence * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--emerald-bright)' }}>
                      {(item.probability * 100).toFixed(1)}%
                    </strong>
                  </td>
                  <td style={{ color: 'var(--cyan-bright)', fontWeight: '800', fontFamily: 'var(--font-mono)' }}>
                    ₹{item.expected_value.toFixed(2)}
                  </td>
                  <td>
                    {item.policy === 'ALLOWED' ? (
                      <span className="badge badge-emerald">ALLOWED</span>
                    ) : (
                      <span className="badge badge-crimson">BLOCKED (&gt;100k)</span>
                    )}
                  </td>
                  <td>
                    {isExecuted ? (
                      <span className="badge badge-emerald" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle2 size={11} /> EXECUTED
                      </span>
                    ) : (
                      <span className="badge badge-amber" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={11} /> PENDING
                      </span>
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: '11px', padding: '5px 12px' }}
                      onClick={() => onSelectTransaction(item.transaction_id)}
                    >
                      <span>Inspect</span>
                      <ArrowRight size={12} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
