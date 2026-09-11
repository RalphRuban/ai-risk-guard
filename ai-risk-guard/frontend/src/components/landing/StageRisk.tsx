import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { RiskFactorItem, ViewId } from '../../types';
import { ShieldAlert, Zap, TrendingUp, Compass, ArrowRight } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';

const FACTORS: RiskFactorItem[] = [
  { id: 'f1', name: 'SEVERITY FACTOR', weight: 0.25, score: 9.5, status: 'CRITICAL', description: 'Base CVSS 9.8 remote execution impact vector', threadColor: '#FF304F' },
  { id: 'f2', name: 'VULNERABILITY TYPE', weight: 0.20, score: 8.8, status: 'ELEVATED', description: 'CWE-78 Command Injection sink in AST hierarchy', threadColor: '#00CFFF' },
  { id: 'f3', name: 'VALIDATION RESULT', weight: 0.15, score: 7.2, status: 'MODERATE', description: 'Sandbox verification pending uncommitted patch', threadColor: '#087BFF' },
  { id: 'f4', name: 'CONFIDENCE ADJUSTMENT', weight: 0.10, score: 9.8, status: 'OPTIMAL', description: '98% heuristic parser confidence score with zero AST ambiguity', threadColor: '#00E699' },
  { id: 'f5', name: 'TARGET FILE CRITICALITY', weight: 0.10, score: 8.5, status: 'ELEVATED', description: 'Core authentication & ingress dispatcher route', threadColor: '#65E7FF' },
  { id: 'f6', name: 'ENVIRONMENT EXPOSURE', weight: 0.10, score: 6.0, status: 'MODERATE', description: 'Internet-facing production API endpoint', threadColor: '#00CFFF' },
  { id: 'f7', name: 'POLICY VIOLATIONS', weight: 0.10, score: 9.0, status: 'CRITICAL', description: 'Explicit ban on os.system() under Enterprise Standard ARG-POL-02', threadColor: '#FF304F' },
];

export const StageRisk: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  return (
    <section className="relative py-20 px-4 sm:px-6 border-b border-[#1E3C5C]/40">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Stage Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-[#06101F] border border-[#1E3C5C] font-mono text-[10px] text-[#00CFFF] tracking-widest mb-2">
              <span>SCROLL STAGE 03 // CONTEXTUAL INTELLIGENCE</span>
            </div>
            <h2 className="font-headline text-2xl sm:text-4xl text-white">
              7-Factor Contextual Risk Engine
            </h2>
            <p className="font-mono text-xs sm:text-sm text-[#8D9AAA] mt-1">
              Dynamic multi-dimensional scoring converts isolated alerts into luminous energy threads that converge into the defense shield.
            </p>
          </div>

          <CyberButton
            variant="secondary"
            size="sm"
            onClick={() => onNavigate('risk')}
            icon={<TrendingUp className="w-3.5 h-3.5 text-[#00CFFF]" />}
          >
            OPEN RISK ENGINE (VIEW 11)
          </CyberButton>
        </div>

        {/* Main Risk Display */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          {/* Left: Large Risk Score Gauge */}
          <div className="lg:col-span-4">
            <GlassPanel
              headerTitle="AGGREGATE CONTEXTUAL RISK"
              headerCode="CALC_SIGMA_W"
              statusIndicator="ALERT"
              accentColor="#FF304F"
              className="text-center py-6"
            >
              <div className="space-y-4">
                <div className="relative inline-flex items-center justify-center">
                  {/* Circular Arc Representation */}
                  <svg className="w-48 h-48 transform -rotate-90">
                    <circle
                      cx="96"
                      cy="96"
                      r="80"
                      stroke="#0F253E"
                      strokeWidth="12"
                      fill="transparent"
                    />
                    <circle
                      cx="96"
                      cy="96"
                      r="80"
                      stroke="#FF304F"
                      strokeWidth="12"
                      strokeDasharray={502}
                      strokeDashoffset={502 - (502 * 7.42) / 10}
                      strokeLinecap="round"
                      fill="transparent"
                      className="transition-all duration-1000 ease-out"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="font-headline font-black text-4xl sm:text-5xl text-white">
                      7.42
                    </span>
                    <span className="font-mono text-[11px] text-[#8D9AAA] tracking-widest">
                      OUT OF 10.0
                    </span>
                  </div>
                </div>

                <div className="p-3 bg-[#8F1424]/25 border border-[#FF304F]/60 text-left font-mono text-[11px] space-y-1">
                  <div className="flex justify-between font-bold text-[#FF304F]">
                    <span>CLASSIFICATION:</span>
                    <span>HIGH RISK (PR GATE BLOCKED)</span>
                  </div>
                  <p className="text-[#D7DEE7] text-[10px]">
                    Automatic merge authorization suspended until container sandbox validation passes and unified AST diff is applied.
                  </p>
                </div>
              </div>
            </GlassPanel>
          </div>

          {/* Right: 7 Luminous Factors & Thread Projection */}
          <div className="lg:col-span-8 space-y-2.5">
            <div className="font-mono text-[11px] text-[#8D9AAA] flex items-center justify-between pb-1">
              <span>EVALUATION FACTORS (LUMINOUS THREADS TO SHIELD CORE)</span>
              <span className="text-[#00CFFF]">WEIGHTED TOTAL: 100%</span>
            </div>

            {FACTORS.map((factor, i) => (
              <div
                key={factor.id}
                className="group relative p-3 bg-[#06101F]/80 border border-[#1E3C5C] hover:border-[#00CFFF]/70 transition-all duration-200"
              >
                {/* Luminous Thread Particle Indicator */}
                <div
                  className="absolute left-0 top-0 bottom-0 w-1"
                  style={{ backgroundColor: factor.threadColor }}
                />

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pl-2">
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2 font-mono text-xs">
                      <span className="text-[#D7DEE7] font-semibold">{factor.name}</span>
                      <span className="text-[10px] px-1.5 py-0.2 bg-[#030914] text-[#8D9AAA] border border-[#1E3C5C]">
                        WEIGHT {Math.round(factor.weight * 100)}%
                      </span>
                    </div>
                    <p className="font-mono text-[11px] text-[#8D9AAA]">{factor.description}</p>
                  </div>

                  <div className="flex items-center space-x-3 shrink-0">
                    <div className="w-28 sm:w-36 bg-[#030914] h-2 border border-[#1E3C5C] overflow-hidden">
                      <div
                        className="h-full transition-all duration-500"
                        style={{
                          width: `${(factor.score / 10) * 100}%`,
                          backgroundColor: factor.threadColor
                        }}
                      />
                    </div>
                    <span className="font-mono text-xs font-bold text-white w-10 text-right">
                      {factor.score.toFixed(1)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
