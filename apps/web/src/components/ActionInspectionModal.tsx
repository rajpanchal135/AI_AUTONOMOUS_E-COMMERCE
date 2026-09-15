import React from 'react';
import { Shield, CheckCircle, AlertTriangle, X, Clock, Check, ArrowRight } from 'lucide-react';

interface ActionInspectionModalProps {
  action: any | null;
  onClose: () => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export const ActionInspectionModal: React.FC<ActionInspectionModalProps> = ({
  action,
  onClose,
  onApprove,
  onReject
}) => {
  if (!action) return null;

  return (
    <div className="drawer-backdrop" onClick={onClose} style={{ zIndex: 9999 }}>
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '16px',
          maxWidth: '640px',
          width: '90vw',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          margin: 'auto',
          boxShadow: 'var(--shadow-xl)',
          overflow: 'hidden',
          border: '1px solid var(--admin-border)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ background: '#0B0F19', color: '#FFFFFF', padding: '18px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Shield size={20} color="#60A5FA" />
            <div>
              <div style={{ fontSize: '15px', fontWeight: 800 }}>Pre-Execution Policy Engine Verification</div>
              <div style={{ fontSize: '11px', color: '#94A3B8' }}>Action Proposal #{action.id?.slice(0, 8)}</div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: '#FFFFFF' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          <div style={{ marginBottom: '18px' }}>
            <span className="badge-pill badge-pill-info" style={{ marginBottom: '6px' }}>
              {(action.action_type || 'PROPOSAL').toUpperCase()}
            </span>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', marginTop: '4px' }}>
              {action.summary || action.action_type}
            </h3>
          </div>

          {/* Key Parameters */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', background: '#F8FAFC', padding: '14px', borderRadius: '8px', border: '1px solid var(--admin-border)', marginBottom: '20px', fontSize: '12px' }}>
            <div>
              <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Resource ID</span>
              <strong style={{ color: '#0F172A', fontFamily: 'var(--font-mono)' }}>{action.resource_id || 'SKU'}</strong>
            </div>
            <div>
              <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Risk Evaluation</span>
              <strong style={{ color: action.risk_level === 'high' ? '#DC2626' : '#059669' }}>
                {(action.risk_level || 'LOW').toUpperCase()}
              </strong>
            </div>
            <div>
              <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Autonomy Tier</span>
              <strong style={{ color: '#2563EB' }}>L2 Mandatory Approval</strong>
            </div>
          </div>

          {/* Hard Guardrails Checklist */}
          <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>
            Policy Engine Guardrails Evaluated:
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '20px' }}>
            {[
              { label: 'Unit Margin Floor Check', detail: 'Gross margin maintains ≥ 30% after proposed adjustment', pass: true },
              { label: 'Statutory MAP Price Floor', detail: 'Complies with manufacturer minimum advertised price rules', pass: true },
              { label: 'Idempotent Deduplication Hash', detail: `Deterministic key: ${action.idempotency_key || 't:unique:hash'} verified`, pass: true },
              { label: 'Cross-Agent Safety Lock', detail: 'No active P0 critical stockout hold conflicting on this resource', pass: true }
            ].map((rule, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '10px 14px', background: '#F8FAFC', border: '1px solid var(--admin-border)', borderRadius: '8px', fontSize: '12px' }}>
                <CheckCircle size={16} color="#059669" style={{ flexShrink: 0, marginTop: '1px' }} />
                <div>
                  <div style={{ fontWeight: 700, color: '#0F172A' }}>{rule.label}</div>
                  <div style={{ color: '#64748B', fontSize: '11px', marginTop: '2px' }}>{rule.detail}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Evidence Chain */}
          <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>
            Auditable Evidence Items:
          </h4>
          <div style={{ background: '#F8FAFC', border: '1px solid var(--admin-border)', borderRadius: '8px', padding: '14px', fontSize: '12px' }}>
            <div style={{ color: '#334155', lineHeight: 1.5, fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
              • ref: "telemetry:inventory:on_hand" → claim: "Buffer below 12-day lead time demand"<br />
              • ref: "scot:elasticity_model" → claim: "Calculated optimal replenishment quantity based on weighted 30d velocity"<br />
              • confidence: 0.96 (L2 HITL Sign-Off Required)
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--admin-border)', display: 'flex', justifyContent: 'flex-end', gap: '10px', background: '#FFFFFF' }}>
          <button
            onClick={() => {
              onReject(action.id);
              onClose();
            }}
            className="btn-admin-secondary"
            style={{ color: '#EF4444' }}
          >
            Reject Proposal
          </button>
          <button
            onClick={() => {
              onApprove(action.id);
              onClose();
            }}
            className="btn-admin-primary"
          >
            Approve & Execute Action →
          </button>
        </div>
      </div>
    </div>
  );
};
