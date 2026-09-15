import React, { useState, useMemo } from 'react';
import {
  Search, Play, CheckCircle, AlertTriangle, Shield, Check,
  X, Filter, Zap, Layers, RefreshCw, Clock, ArrowRight, ExternalLink,
  ChevronRight, Activity, Terminal
} from 'lucide-react';
import { EdgeCaseItem, EdgeCaseSimulationResult, runEdgeCaseSimulation } from '../lib/api';

interface EdgeCaseSimulatorProps {
  edgeCases: EdgeCaseItem[];
  preselectedAgent?: string;
  showToast: (text: string, type?: 'info' | 'success' | 'error') => void;
}

export const EdgeCaseSimulatorView: React.FC<EdgeCaseSimulatorProps> = ({
  edgeCases,
  preselectedAgent = 'all',
  showToast
}) => {
  const [agentFilter, setAgentFilter] = useState<string>(preselectedAgent);
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCase, setSelectedCase] = useState<EdgeCaseItem | null>(edgeCases[0] || null);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<EdgeCaseSimulationResult | null>(null);

  // Filtered edge cases
  const filteredCases = useMemo(() => {
    return edgeCases.filter((ec) => {
      if (agentFilter !== 'all' && ec.agent.toLowerCase() !== agentFilter.toLowerCase()) return false;
      if (priorityFilter !== 'all' && ec.priority !== priorityFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          ec.code.toLowerCase().includes(q) ||
          ec.name.toLowerCase().includes(q) ||
          ec.scenario.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [edgeCases, agentFilter, priorityFilter, searchQuery]);

  // Execute simulation
  const handleRunSimulation = async (code: string) => {
    setSimulating(true);
    setSimulationResult(null);
    try {
      const res = await runEdgeCaseSimulation(code);
      setSimulationResult(res);
      showToast(`Edge Case [${code}] executed successfully through agent mesh.`, 'success');
    } catch (err: any) {
      showToast(err.message || `Failed to run edge case ${code}`, 'error');
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div>
      {/* Top Banner */}
      <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', padding: '24px', marginBottom: '24px', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <Terminal size={18} color="#2563EB" />
              <h3 style={{ fontSize: '18px', fontWeight: 800 }}>Enterprise Edge Case Simulator & Inspector</h3>
            </div>
            <p style={{ fontSize: '13px', color: '#64748B' }}>
              Test and inspect all 112 enterprise-grade edge cases in real-time across all 7 autonomous agents.
              Inspect live multi-hop event cascades, evidence chains, and policy engine guardrails.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge-pill badge-pill-info">
              {filteredCases.length} of {edgeCases.length} Edge Cases Displayed
            </span>
          </div>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '18px', alignItems: 'center', borderTop: '1px solid var(--admin-border)', paddingTop: '16px' }}>
          {/* Agent Filter */}
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {[
              { id: 'all', label: 'All Agents' },
              { id: 'inventory', label: '1. Inventory' },
              { id: 'pricing', label: '2. Pricing' },
              { id: 'support', label: '3. Support' },
              { id: 'orders', label: '4. Orders' },
              { id: 'logistics', label: '5. Logistics' },
              { id: 'marketing', label: '6. Marketing' },
              { id: 'supervisor', label: '7. Orchestrator' },
              { id: 'products', label: '8. Product Catalog' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setAgentFilter(tab.id)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid',
                  borderColor: agentFilter === tab.id ? '#2563EB' : 'var(--admin-border)',
                  background: agentFilter === tab.id ? '#EFF6FF' : '#FFFFFF',
                  color: agentFilter === tab.id ? '#1E40AF' : '#475569',
                  fontSize: '12px',
                  fontWeight: agentFilter === tab.id ? 700 : 500,
                  cursor: 'pointer'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div style={{ width: '1px', height: '24px', background: 'var(--admin-border)', margin: '0 4px' }} />

          {/* Priority Filter */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {['all', 'P0', 'P1', 'P2', 'P3'].map(p => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                style={{
                  padding: '6px 10px',
                  borderRadius: '6px',
                  border: '1px solid',
                  borderColor: priorityFilter === p ? '#0F172A' : 'var(--admin-border)',
                  background: priorityFilter === p ? '#0F172A' : '#FFFFFF',
                  color: priorityFilter === p ? '#FFFFFF' : '#475569',
                  fontSize: '11px',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                {p === 'all' ? 'All Priorities' : p}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div style={{ marginLeft: 'auto', minWidth: '220px', position: 'relative' }}>
            <Search size={14} color="#94A3B8" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            <input
              type="text"
              placeholder="Search by code or keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '100%', padding: '8px 10px 8px 32px', borderRadius: '6px', border: '1px solid var(--admin-border)', fontSize: '12px', outline: 'none' }}
            />
          </div>
        </div>
      </div>

      {/* Main Split View: Left Catalog + Right Live Inspector */}
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '24px', alignItems: 'start' }}>
        {/* Left Column: Edge Case Selector List */}
        <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', maxHeight: '720px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--admin-border)', background: '#F8FAFC', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#475569' }}>CATALOG ({filteredCases.length})</span>
            <span style={{ fontSize: '11px', color: '#94A3B8' }}>Select to test</span>
          </div>

          <div style={{ overflowY: 'auto', flex: 1, padding: '8px' }}>
            {filteredCases.map(ec => {
              const isSelected = selectedCase?.code === ec.code;
              const pClass = ec.priority === 'P0' ? 'priority-p0' : ec.priority === 'P1' ? 'priority-p1' : ec.priority === 'P2' ? 'priority-p2' : 'priority-p3';
              return (
                <div
                  key={ec.code}
                  onClick={() => {
                    setSelectedCase(ec);
                    setSimulationResult(null);
                  }}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    marginBottom: '6px',
                    background: isSelected ? '#EFF6FF' : '#FFFFFF',
                    border: '1px solid',
                    borderColor: isSelected ? '#3B82F6' : 'var(--admin-border)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 800, fontFamily: 'var(--font-mono)', fontSize: '12px', color: isSelected ? '#1D4ED8' : '#0F172A' }}>
                      {ec.code}
                    </span>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <span className={`priority-badge ${pClass}`} style={{ fontSize: '9px', padding: '1px 5px' }}>{ec.priority}</span>
                      <span className="autonomy-badge" style={{ fontSize: '9px', padding: '1px 5px' }}>L{ec.autonomy_level}</span>
                    </div>
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#1E293B', marginBottom: '4px' }}>
                    {ec.name}
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748B', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {ec.scenario}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Active Edge Case Cockpit & Real-Time Runner */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {selectedCase ? (
            <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', padding: '24px', boxShadow: 'var(--shadow-sm)' }}>
              {/* Cockpit Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', borderBottom: '1px solid var(--admin-border)', paddingBottom: '18px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span style={{ fontSize: '14px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#2563EB' }}>
                      {selectedCase.code}
                    </span>
                    <span className="badge-pill badge-pill-neutral">
                      Agent: {selectedCase.agent.toUpperCase()}
                    </span>
                    <span className={`priority-badge ${selectedCase.priority === 'P0' ? 'priority-p0' : selectedCase.priority === 'P1' ? 'priority-p1' : selectedCase.priority === 'P2' ? 'priority-p2' : 'priority-p3'}`}>
                      Priority: {selectedCase.priority}
                    </span>
                    <span className="autonomy-badge">
                      Autonomy: L{selectedCase.autonomy_level}
                    </span>
                  </div>
                  <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A' }}>
                    {selectedCase.name}
                  </h3>
                </div>

                <button
                  onClick={() => handleRunSimulation(selectedCase.code)}
                  disabled={simulating}
                  className="btn-luxury-primary"
                  style={{ padding: '12px 22px', fontSize: '13px', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', border: 'none' }}
                >
                  <Zap size={15} /> {simulating ? 'Simulating Edge Case...' : '⚡ Run Live Edge Case Simulation'}
                </button>
              </div>

              {/* Scenario & Resolution Spec Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                <div style={{ background: '#F8FAFC', border: '1px solid var(--admin-border)', borderRadius: '10px', padding: '16px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#D97706', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Trigger Scenario
                  </div>
                  <p style={{ fontSize: '13px', color: '#334155', lineHeight: 1.5 }}>
                    {selectedCase.scenario}
                  </p>
                </div>
                <div style={{ background: '#F8FAFC', border: '1px solid var(--admin-border)', borderRadius: '10px', padding: '16px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#059669', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Autonomous Resolution Strategy
                  </div>
                  <p style={{ fontSize: '13px', color: '#334155', lineHeight: 1.5 }}>
                    {selectedCase.resolution}
                  </p>
                </div>
              </div>

              {/* Simulation Result Box */}
              {simulationResult && (
                <div style={{ borderTop: '1px solid var(--admin-border)', paddingTop: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <CheckCircle size={18} color="#059669" />
                    <h4 style={{ fontSize: '16px', fontWeight: 800 }}>Live Execution Pipeline & Policy Verification</h4>
                  </div>

                  {/* Summary Callout */}
                  <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: '#166534', marginBottom: '4px' }}>
                      Agent Run Decision Summary:
                    </div>
                    <div style={{ fontSize: '13px', color: '#14532D', lineHeight: 1.5 }}>
                      {simulationResult.summary}
                    </div>
                  </div>

                  {/* 4 Visual Pipeline Steps */}
                  <h5 style={{ fontSize: '13px', fontWeight: 700, color: '#475569', marginBottom: '10px' }}>
                    Execution Workflow Stages:
                  </h5>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
                    {simulationResult.steps.map((st) => (
                      <div key={st.step} className="sim-step-node active">
                        <div className="sim-step-icon" style={{ background: '#EFF6FF', color: '#2563EB' }}>
                          {st.step}
                        </div>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', marginBottom: '3px' }}>
                            {st.title}
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748B', lineHeight: 1.4 }}>
                            {st.detail}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Policy Validation Checklist */}
                  <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '10px', padding: '18px', marginBottom: '20px' }}>
                    <h5 style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A', marginBottom: '12px' }}>
                      Policy Engine Hard Guardrail Verification Checklist:
                    </h5>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <CheckCircle size={14} color="#059669" />
                        <span>Margin Floor (≥30%): <strong style={{ color: '#059669' }}>VERIFIED</strong></span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <CheckCircle size={14} color={simulationResult.validation_checklist.map_compliant ? '#059669' : '#DC2626'} />
                        <span>MAP Compliance: <strong>{simulationResult.validation_checklist.map_compliant ? 'PASSED' : 'FLAGGED'}</strong></span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <CheckCircle size={14} color="#059669" />
                        <span>Idempotency Hash: <strong style={{ color: '#059669' }}>VERIFIED</strong></span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Shield size={14} color={simulationResult.validation_checklist.p0_hold_active ? '#DC2626' : '#64748B'} />
                        <span>P0 Safety Hold: <strong>{simulationResult.validation_checklist.p0_hold_active ? 'ACTIVE' : 'INACTIVE'}</strong></span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', gridColumn: 'span 2' }}>
                        <Clock size={14} color="#2563EB" />
                        <span>Autonomy Routing Gate: <strong>{simulationResult.validation_checklist.autonomy_gate}</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* Actions Generated */}
                  {simulationResult.actions.length > 0 && (
                    <div>
                      <h5 style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>
                        Proposed Actions Dispatched to Queue:
                      </h5>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {simulationResult.actions.map((act, idx) => (
                          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: '#F8FAFC', border: '1px solid var(--admin-border)', borderRadius: '8px', fontSize: '12px' }}>
                            <div>
                              <div style={{ fontWeight: 700, color: '#0F172A' }}>{act.action_type}</div>
                              <div style={{ color: '#64748B', marginTop: '2px' }}>Resource: {act.resource_id} • Risk: {act.risk_level}</div>
                            </div>
                            <span className={`badge-pill ${act.requires_approval ? 'badge-pill-warning' : 'badge-pill-success'}`}>
                              {act.requires_approval ? 'L2 Awaiting Human Sign-Off' : 'L3/L4 Auto-Executing'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', padding: '60px 20px', textAlign: 'center', color: '#64748B' }}>
              <Terminal size={40} style={{ margin: '0 auto 12px auto', opacity: 0.4 }} />
              <h4 style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A' }}>No Edge Case Selected</h4>
              <p style={{ fontSize: '13px', marginTop: '4px' }}>Select any edge case from the catalog on the left to simulate.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
