import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId, RiskFactorItem } from '../../types';

const DETAILED_FACTORS: RiskFactorItem[] = [
  { id: 'f1', name: '01 SEVERITY (CVSS BASE)', weight: 0.25, score: 9.5, status: 'CRITICAL', description: 'Remote code execution capability on subshell injection without auth.', threadColor: '#FF1E2D' },
  { id: 'f2', name: '02 VULNERABILITY TYPE (CWE)', weight: 0.20, score: 8.8, status: 'ELEVATED', description: 'CWE-78 Command Injection sink node located in AST hierarchy.', threadColor: '#00A8FF' },
  { id: 'f3', name: '03 VALIDATION RESULT', weight: 0.15, score: 7.2, status: 'MODERATE', description: 'Sandbox verification pending uncommitted patch execution.', threadColor: '#007BFF' },
  { id: 'f4', name: '04 CONFIDENCE ADJUSTMENT', weight: 0.10, score: 9.8, status: 'OPTIMAL', description: '98% heuristic parser confidence score with zero AST ambiguity.', threadColor: '#00E699' },
  { id: 'f5', name: '05 TARGET FILE CRITICALITY', weight: 0.10, score: 8.5, status: 'ELEVATED', description: 'Located in public request ingress dispatch router (api/routes/executor.py).', threadColor: '#5BC9FF' },
  { id: 'f6', name: '06 ENVIRONMENT EXPOSURE', weight: 0.10, score: 6.0, status: 'MODERATE', description: 'Inbound web server pod exposed behind reverse proxy.', threadColor: '#00A8FF' },
  { id: 'f7', name: '07 POLICY VIOLATIONS', weight: 0.10, score: 9.0, status: 'CRITICAL', description: 'Direct breach of enterprise policy rule ARG-POL-02 (os.system forbidden).', threadColor: '#FF1E2D' },
];

export const View11Risk: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>MATHEMATICAL FORMULATION // DYNAMIC RISK MATRIX</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            7-Factor Contextual Risk Engine
          </h1>
        </div>

        <CyberButton
          variant="secondary"
          size="sm"
          onClick={() => onNavigate('telemetry')}
        >
          SECURITY TELEMETRY (VIEW 12)
        </CyberButton>
      </div>

      {/* Math Formulation Callout */}
      <GlassPanel
        headerTitle="MATHEMATICAL RISK FORMULATION"
        headerCode="FORMULA_SPEC_V2"
        statusIndicator="ACTIVE"
      >
        <div className="p-4 bg-[#020B1A] border border-[#17406E] font-mono text-xs text-[#5BC9FF] leading-relaxed">
          <div className="text-white font-semibold mb-1">FORMULATION:</div>
          <div><code>Risk_Score = ∑ (Weight_i × Raw_Score_i) × (1 - (Confidence_Factor / 100) × 0.15)</code></div>
          <div className="text-[#9AA7B8] text-[11px] mt-2">
            Normalizes raw severity into actionable contextual risk based on code placement, sandbox proof, and policy constraints.
          </div>
        </div>
      </GlassPanel>

      {/* Aggregate Score & Factor List */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Gauge (4 cols) */}
        <div className="lg:col-span-4">
          <GlassPanel
            headerTitle="COMPUTED RISK SCORE"
            headerCode="AGGREGATE"
            statusIndicator="ALERT"
            accentColor="#FF1E2D"
            className="text-center py-6"
          >
            <div className="font-headline font-black text-5xl text-white mb-1">7.42</div>
            <div className="font-mono text-xs text-[#FF1E2D] font-bold tracking-widest mb-4">
              HIGH RISK CLASSIFICATION
            </div>
            <div className="p-3 bg-[#020B1A] border border-[#17406E] text-left font-mono text-[11px] text-[#9AA7B8] space-y-1">
              <div className="flex justify-between">
                <span>POST-PATCH PROJECTED:</span>
                <span className="text-[#00E699] font-bold">1.18 / 10.0</span>
              </div>
              <div className="flex justify-between">
                <span>PR GATE STATUS:</span>
                <span className="text-[#FF1E2D] font-bold">MERGE BLOCKED</span>
              </div>
            </div>
          </GlassPanel>
        </div>

        {/* Factors (8 cols) */}
        <div className="lg:col-span-8 space-y-2">
          {DETAILED_FACTORS.map((factor) => (
            <div
              key={factor.id}
              className="p-3 bg-[#050B16] border border-[#17406E] font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="text-white font-semibold">{factor.name}</span>
                  <span className="text-[10px] text-[#00A8FF]">({Math.round(factor.weight * 100)}% WEIGHT)</span>
                </div>
                <p className="text-[11px] text-[#9AA7B8]">{factor.description}</p>
              </div>

              <div className="flex items-center space-x-3 shrink-0">
                <div className="w-24 bg-[#020B1A] h-2 border border-[#17406E]">
                  <div
                    className="h-full"
                    style={{
                      width: `${(factor.score / 10) * 100}%`,
                      backgroundColor: factor.threadColor
                    }}
                  />
                </div>
                <span className="font-bold text-white w-8 text-right">{factor.score.toFixed(1)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
