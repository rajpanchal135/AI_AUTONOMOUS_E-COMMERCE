import React, { useState } from 'react';
import {
  Box, DollarSign, MessageSquare, Truck, Compass, Flame, Cpu,
  Shield, CheckCircle, ArrowRight, Zap, Play, Info, ExternalLink,
  ChevronRight, Lock, Activity, Eye, Layers, Sparkles
} from 'lucide-react';

interface HiveTopologyProps {
  onTriggerSimulation: () => void;
  simulating: boolean;
}

export const ALL_7_AGENTS_DATA = [
  {
    id: 'inventory',
    num: 1,
    title: 'Inventory Intelligence Agent',
    codename: 'The Stock Guardian',
    priority: 'P0',
    priorityName: 'Safety & Inventory Guardrails',
    autonomy: 'L2',
    autonomyName: 'Propose + Mandatory Human Approval',
    domain: 'Stockout Forecasting & Replenishment',
    description: 'Monitors real-time SKU levels across all fulfillment centers, calculates lead-time safety stock, detects stockout threats, and freezes price discounts.',
    keyMetrics: [
      { label: 'Safety Stock Factor', value: '1.65 (95% SLA)' },
      { label: 'Reorder Buffer', value: '12-Day Lead Time' },
      { label: 'P0 Hold Trigger', value: '< 5 Days Cover' }
    ],
    edgeCasesSample: ['EC-INV-01: Critical Stockout Freeze', 'EC-INV-02: Supplier Lead-Time Spike', 'EC-INV-12: Negative Velocity Return Surge'],
    icon: Box,
    accent: '#EF4444',
    badgeClass: 'priority-p0'
  },
  {
    id: 'pricing',
    num: 2,
    title: 'Dynamic Pricing Agent',
    codename: 'The Profit Maximizer',
    priority: 'P2',
    priorityName: 'Dynamic Margin Optimization',
    autonomy: 'L3',
    autonomyName: 'Guardrailed Auto-Execution (>=30% Floor)',
    domain: 'Elasticity, Margin Floors & Competitor Matching',
    description: 'Optimizes margins through supply-chain-aware elasticity pricing. Strictly enforces minimum unit margin floors and defends against price wars.',
    keyMetrics: [
      { label: 'Margin Floor', value: '≥ 30% Unit Margin' },
      { label: 'Max Daily Delta', value: '±15% Max Shift' },
      { label: 'Price Flapping Lock', value: '24h Cooldown' }
    ],
    edgeCasesSample: ['EC-PRC-02: Competitor Price War Defense', 'EC-PRC-04: MAP Regulatory Floor Breach', 'EC-PRC-12: Price Flapping 24h Lock'],
    icon: DollarSign,
    accent: '#3B82F6',
    badgeClass: 'priority-p2'
  },
  {
    id: 'support',
    num: 3,
    title: 'Customer Support Agent',
    codename: 'The Issue Solver',
    priority: 'P1',
    priorityName: 'Order Fulfillment & SLA Protection',
    autonomy: 'L2',
    autonomyName: 'Grounded Gemini RAG Drafts + Auto-Redaction',
    domain: 'Conversational Concierge & PII Defense',
    description: 'Multi-lingual RAG support desk powered by Gemini 1.5/3.6 Flash. Redacts sensitive credit card PANs automatically and enforces grounded carrier ETA.',
    keyMetrics: [
      { label: 'Auto-Approval Limit', value: '< $25 (L3 Auto)' },
      { label: 'VIP SLA Response', value: '< 60 Minutes' },
      { label: 'PAN Redaction', value: 'Auto-Scrub active' }
    ],
    edgeCasesSample: ['EC-SUP-01: Unverified Delivery Date Guard', 'EC-SUP-14: Credit Card PAN Auto-Redaction', 'EC-SUP-04: Multi-Lingual Regional Support'],
    icon: MessageSquare,
    accent: '#F59E0B',
    badgeClass: 'priority-p1'
  },
  {
    id: 'orders',
    num: 4,
    title: 'Order Management Agent',
    codename: 'The Workflow Master',
    priority: 'P1',
    priorityName: 'Order Fulfillment & SLA Protection',
    autonomy: 'L3',
    autonomyName: 'State Machine Transitions + COD Verification',
    domain: 'Lifecycle State Machine & Fraud Scoring',
    description: 'Manages complete order state machine from pending to dispatched. Checks high-risk COD pincodes, enforces idempotent deduplication, and handles partial splits.',
    keyMetrics: [
      { label: 'Idempotency TTL', value: '24-Hour Cache' },
      { label: 'COD Risk Threshold', value: 'High Fraud Pincodes' },
      { label: 'Split Route Gate', value: 'Multi-Warehouse' }
    ],
    edgeCasesSample: ['EC-ORD-05: COD High Risk Pincode Hold', 'EC-ORD-06: Duplicate Order Placement Guard', 'EC-ORD-09: Multi-Currency FX Drift Tolerance'],
    icon: Truck,
    accent: '#8B5CF6',
    badgeClass: 'priority-p1'
  },
  {
    id: 'logistics',
    num: 5,
    title: 'Logistics & Delivery Agent',
    codename: 'The Supply Chain Optimizer',
    priority: 'P1',
    priorityName: 'Order Fulfillment & SLA Protection',
    autonomy: 'L3',
    autonomyName: 'Carrier Re-allocation & Green Routing',
    domain: 'Carrier SLA, Route Balancing & Carbon Emissions',
    description: 'Optimizes carrier allocation using composite SLA and cost scoring. Activates lost-in-transit protocols after 72 hours of stagnation.',
    keyMetrics: [
      { label: 'Lost Stagnation Limit', value: '72h Scan Absence' },
      { label: 'Green Premium Cap', value: 'Max +10% Cost' },
      { label: 'Weight Discrepancy', value: '> 15% Flagged' }
    ],
    edgeCasesSample: ['EC-LOG-01: 72h Lost in Transit Protocol', 'EC-LOG-03: Carrier Weight Discrepancy Flag', 'EC-LOG-11: Green Fleet / Sustainability Routing'],
    icon: Compass,
    accent: '#059669',
    badgeClass: 'priority-p1'
  },
  {
    id: 'marketing',
    num: 6,
    title: 'Marketing Automation Agent',
    codename: 'The Growth Hacker',
    priority: 'P3',
    priorityName: 'Growth & Campaigns (Yields to P0)',
    autonomy: 'L2',
    autonomyName: 'AI Copy Generation + Consent Verification Gate',
    domain: 'RFM Segmentation, Copy Safety & Ad ROAS',
    description: 'Generates promotional campaigns and automated cart recovery. Yields immediately to P0 stockout holds to prevent ad spend wastage on depleted inventory.',
    keyMetrics: [
      { label: 'Min ROAS Threshold', value: '2.5x Target' },
      { label: 'Consent Hard Stop', value: 'GDPR / Double Opt-In' },
      { label: 'P0 Ad Override', value: '< 5d Cover Auto-Pause' }
    ],
    edgeCasesSample: ['EC-MKT-01: P0 Out-of-Stock Ad Spend Wastage Guard', 'EC-MKT-02: Missing GDPR Consent Hard Stop', 'EC-MKT-05: Brand Safety / AI Content Shield'],
    icon: Flame,
    accent: '#EC4899',
    badgeClass: 'priority-p3'
  },
  {
    id: 'supervisor',
    num: 7,
    title: 'Master Orchestrator Agent',
    codename: 'The Hive Brain',
    priority: 'P0-P3',
    priorityName: 'Universal Event Bus Supervisor & Conflict Engine',
    autonomy: 'L3/L4',
    autonomyName: 'Deadlock 60s Breaker & High-Throughput Orchestrator',
    domain: 'Multi-Agent Orchestration & Priority Resolution',
    description: 'LangGraph-based supervisor governing the agent mesh. Enforces priority inversion rules (P0 > P1 > P2 > P3) with zero-downtime deterministic fallback resilience.',
    keyMetrics: [
      { label: 'Deadlock Timeout', value: '60s Circuit Breaker' },
      { label: 'Priority Matrix', value: 'P0 > P1 > P2 > P3' },
      { label: 'Degradation', value: 'Deterministic Fallback' }
    ],
    edgeCasesSample: ['EC-ORC-01: 60s Deadlock Circuit Breaker', 'EC-ORC-09: Priority Inversion Guard (P0 overrides P3)', 'EC-ORC-15: Zero-Downtime Fallback Routing'],
    icon: Cpu,
    accent: '#6366F1',
    badgeClass: 'priority-p0'
  }
];

export const HiveTopologyView: React.FC<HiveTopologyProps> = ({
  onTriggerSimulation,
  simulating
}) => {
  const [selectedAgent, setSelectedAgent] = useState<any | null>(null);

  return (
    <div>
      {/* Priority Rules & Hive Governance Banner */}
      <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', padding: '24px', marginBottom: '24px', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '18px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <Sparkles size={18} color="#2563EB" />
              <h3 style={{ fontSize: '18px', fontWeight: 800 }}>Universal Multi-Agent Mesh Topology (All 7 Agents)</h3>
            </div>
            <p style={{ fontSize: '13px', color: '#64748B' }}>
              Autonomous swarm architecture governed by strict Priority Hierarchy (P0 Safety → P1 SLA → P2 Margin → P3 Growth) and L0–L4 Autonomy Gates.
            </p>
          </div>
          <button
            onClick={onTriggerSimulation}
            disabled={simulating}
            className="btn-luxury-primary"
            style={{ padding: '10px 18px', fontSize: '13px', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', border: 'none' }}
          >
            <Zap size={14} /> {simulating ? 'Executing Swarm...' : '⚡ Run Multi-Agent Cross-Check'}
          </button>
        </div>

        {/* Priority Legend Pill Bar */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', background: '#F8FAFC', padding: '12px', borderRadius: '8px', border: '1px solid var(--admin-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="priority-badge priority-p0">P0 SAFETY</span>
            <span style={{ fontSize: '12px', color: '#64748B' }}>Critical Stockout & Safety Locks</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="priority-badge priority-p1">P1 FULFILLMENT</span>
            <span style={{ fontSize: '12px', color: '#64748B' }}>Order SLA & Carrier Allocation</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="priority-badge priority-p2">P2 MARGIN</span>
            <span style={{ fontSize: '12px', color: '#64748B' }}>Dynamic Pricing & Margin Floors</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="priority-badge priority-p3">P3 GROWTH</span>
            <span style={{ fontSize: '12px', color: '#64748B' }}>Ad Spend & Marketing Campaigns</span>
          </div>
        </div>
      </div>

      {/* All 7 Agents Interactive Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {ALL_7_AGENTS_DATA.map((agent) => {
          const Icon = agent.icon;
          return (
            <div
              key={agent.id}
              className={`agent-grid-card ${agent.priority.toLowerCase()}`}
              style={{ display: 'flex', flexDirection: 'column' }}
            >
              {/* Card Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: `${agent.accent}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon size={22} color={agent.accent} />
                  </div>
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: agent.accent, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Agent {agent.num} • {agent.codename}
                    </div>
                    <h4 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginTop: '1px' }}>
                      {agent.title}
                    </h4>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                  <span className={`priority-badge ${agent.badgeClass}`}>{agent.priority}</span>
                  <span className={`autonomy-badge autonomy-${agent.autonomy.toLowerCase()}`}>{agent.autonomy}</span>
                </div>
              </div>

              {/* Description */}
              <p style={{ fontSize: '13px', color: '#475569', lineHeight: 1.5, marginBottom: '16px', flex: 1 }}>
                {agent.description}
              </p>

              {/* Key Metrics */}
              <div style={{ background: '#F8FAFC', border: '1px solid var(--admin-border)', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', textAlign: 'center' }}>
                  {agent.keyMetrics.map((km, idx) => (
                    <div key={idx}>
                      <span style={{ fontSize: '10px', color: '#64748B', display: 'block' }}>{km.label}</span>
                      <strong style={{ fontSize: '12px', color: '#0F172A', marginTop: '2px', display: 'block' }}>{km.value}</strong>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sample Edge Cases Pills */}
              <div style={{ marginBottom: '16px' }}>
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', display: 'block', marginBottom: '6px' }}>
                  Verified Real-World Edge Cases (16 Total):
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {agent.edgeCasesSample.map((ec, idx) => (
                    <div key={idx} style={{ fontSize: '11px', color: '#334155', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle size={12} color="#059669" />
                      <span style={{ fontFamily: 'var(--font-mono)' }}>{ec}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer Buttons */}
              <div style={{ display: 'flex', gap: '8px', marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--admin-border)' }}>
                <button
                  onClick={() => setSelectedAgent(agent)}
                  className="btn-luxury-primary"
                  style={{ flex: 1, padding: '8px 12px', fontSize: '12px', borderRadius: '6px' }}
                >
                  <Info size={14} /> View Architecture & Policies
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Agent Spec Inspection Drawer Modal */}
      {selectedAgent && (
        <div className="drawer-backdrop" onClick={() => setSelectedAgent(null)} style={{ zIndex: 9999 }}>
          <div
            style={{
              background: '#FFFFFF',
              borderRadius: '16px',
              maxWidth: '600px',
              width: '90vw',
              padding: '28px',
              margin: 'auto',
              boxShadow: 'var(--shadow-xl)',
              maxHeight: '85vh',
              overflowY: 'auto'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid var(--admin-border)', paddingBottom: '12px' }}>
              <div>
                <span style={{ fontSize: '11px', fontWeight: 800, color: selectedAgent.accent, textTransform: 'uppercase' }}>
                  Agent {selectedAgent.num} Specification
                </span>
                <h3 style={{ fontSize: '20px', fontWeight: 800 }}>{selectedAgent.title}</h3>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                style={{ background: '#F1F5F9', border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
              <span className={`priority-badge ${selectedAgent.badgeClass}`}>Priority: {selectedAgent.priority}</span>
              <span className="autonomy-badge">Autonomy: {selectedAgent.autonomy}</span>
              <span className="badge-pill badge-pill-info">Enterprise Guardrails Active</span>
            </div>

            <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '6px' }}>Domain Mandate</h4>
            <p style={{ fontSize: '13px', color: '#475569', lineHeight: 1.5, marginBottom: '20px' }}>
              {selectedAgent.description}
            </p>

            <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '8px' }}>Priority & Autonomy Rules</h4>
            <div style={{ background: '#F8FAFC', border: '1px solid var(--admin-border)', borderRadius: '8px', padding: '14px', marginBottom: '20px', fontSize: '13px' }}>
              <div style={{ marginBottom: '8px' }}>
                <strong style={{ color: '#0F172A' }}>Priority Role: </strong>
                <span style={{ color: '#475569' }}>{selectedAgent.priorityName}</span>
              </div>
              <div>
                <strong style={{ color: '#0F172A' }}>Autonomy Gate: </strong>
                <span style={{ color: '#475569' }}>{selectedAgent.autonomyName}</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedAgent(null)}
              className="btn-luxury-secondary"
              style={{ width: '100%', padding: '12px' }}
            >
              Close Specification
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
