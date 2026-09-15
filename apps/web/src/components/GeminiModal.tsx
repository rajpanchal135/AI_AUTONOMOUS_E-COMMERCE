import React, { useState } from 'react';
import { Sparkles, X, Send, CheckCircle, AlertCircle, Cpu, Clock, Shield } from 'lucide-react';
import { executeLiveGeminiPrompt } from '../lib/api';

interface GeminiModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: any;
}

export const GeminiModal: React.FC<GeminiModalProps> = ({ isOpen, onClose, status }) => {
  const [prompt, setPrompt] = useState('Analyze this customer message: "Where is my order #10045? Tracking is not moving." Respond in JSON with intent, sentiment, and urgency.');
  const [testing, setTesting] = useState(false);
  const [response, setResponse] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleTest = async () => {
    if (!prompt.trim()) return;
    setTesting(true);
    setError(null);
    setResponse(null);
    try {
      const res = await executeLiveGeminiPrompt(prompt.trim());
      setResponse(res);
    } catch (err: any) {
      setError(err.message || 'Failed to communicate with Gemini API');
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="drawer-backdrop" onClick={onClose} style={{ zIndex: 9999 }}>
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '16px',
          maxWidth: '680px',
          width: '90vw',
          maxHeight: '90vh',
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'linear-gradient(135deg, #2563EB 0%, #9333EA 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Sparkles size={20} color="#FFFFFF" />
            </div>
            <div>
              <div style={{ fontSize: '16px', fontWeight: 800 }}>Google Gemini AI Studio Console</div>
              <div style={{ fontSize: '11px', color: '#94A3B8' }}>Real-Time Inference & Telemetry Engine</div>
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
          {/* Telemetry Status Bar */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', background: '#F8FAFC', padding: '14px', borderRadius: '10px', border: '1px solid var(--admin-border)', marginBottom: '20px', fontSize: '12px' }}>
            <div>
              <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Connection</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, color: status?.status === 'online' ? '#059669' : '#D97706', marginTop: '2px' }}>
                <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: status?.status === 'online' ? '#10B981' : '#F59E0B' }} />
                {status?.status === 'online' ? 'LIVE ONLINE' : 'FALLBACK MODE'}
              </div>
            </div>
            <div>
              <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Active Model</span>
              <div style={{ fontWeight: 700, color: '#0F172A', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                {status?.model || 'gemini-3.6-flash'}
              </div>
            </div>
            <div>
              <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Rate Limit Tier</span>
              <div style={{ fontWeight: 700, color: '#2563EB', marginTop: '2px' }}>
                {status?.tier || status?.rate_limit || 'Enterprise Production'}
              </div>
            </div>
            <div>
              <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>API Key Hash</span>
              <div style={{ fontWeight: 700, color: '#475569', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                {status?.masked_key || 'AQ.Ab8...zPrw'}
              </div>
            </div>
          </div>

          {/* Test Prompt Input */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A', display: 'block', marginBottom: '6px' }}>
              Direct Test Prompt
            </label>
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter a prompt to test live Gemini inference..."
              style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--admin-border)', fontSize: '13px', fontFamily: 'var(--font-sans)', outline: 'none' }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <span style={{ fontSize: '12px', color: '#64748B' }}>
              Enterprise Tier: Zero-downtime deterministic heuristic fallback engine active for maximum SLA reliability.
            </span>
            <button
              onClick={handleTest}
              disabled={testing || !prompt.trim()}
              className="btn-luxury-primary"
              style={{ padding: '10px 18px', fontSize: '13px', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', border: 'none' }}
            >
              <Send size={14} /> {testing ? 'Querying Gemini...' : 'Generate Live Completion'}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', color: '#991B1B', padding: '12px 16px', borderRadius: '8px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <AlertCircle size={16} /> {error}
            </div>
          )}

          {/* Output Display */}
          {response && (
            <div style={{ background: '#0B0F19', color: '#FFFFFF', borderRadius: '10px', padding: '16px', border: '1px solid #1E293B' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1E293B', paddingBottom: '10px', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#10B981', fontWeight: 700 }}>
                  <CheckCircle size={14} /> Gemini Response Received
                </div>
                <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: '#94A3B8' }}>
                  <span>Latency: <strong style={{ color: '#FFFFFF' }}>{response.latency_ms}ms</strong></span>
                  <span>Model: <strong style={{ color: '#FFFFFF' }}>{response.model}</strong></span>
                </div>
              </div>
              <pre style={{ margin: 0, fontSize: '13px', fontFamily: 'var(--font-mono)', lineHeight: 1.5, whiteSpace: 'pre-wrap', color: '#E2E8F0' }}>
                {response.response}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
