import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { ShieldCheck, Lock, Sliders, CheckCircle2, AlertOctagon } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';

export const StagePolicy: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  return (
    <section className="relative py-20 px-4 sm:px-6 border-b border-[#1E3C5C]/40">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Stage Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-[#06101F] border border-[#1E3C5C] font-mono text-[10px] text-[#00CFFF] tracking-widest mb-2">
              <span>SCROLL STAGE 07 // GOVERNANCE RINGS</span>
            </div>
            <h2 className="font-headline text-2xl sm:text-4xl text-white">
              Policy Gateway & Geometric Ring Lock
            </h2>
            <p className="font-mono text-xs sm:text-sm text-[#8D9AAA] mt-1">
              Autonomous organizational policy enforcement rules appear as concentric geometric rings that lock firmly around the shield core.
            </p>
          </div>

          <div className="flex items-center space-x-2 font-mono text-[10px]">
            <span className="px-2.5 py-1 bg-[#00E699]/20 border border-[#00E699]/60 text-[#00E699] font-bold flex items-center space-x-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>POLICY RINGS LOCKED</span>
            </span>
          </div>
        </div>

        {/* 4 Policy Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Pillar 1: Blocked Modules */}
          <GlassPanel
            headerTitle="BLOCKED MODULES"
            headerCode="RING_01_LOCKED"
            statusIndicator="ACTIVE"
          >
            <div className="space-y-2 font-mono text-xs">
              <div className="text-[#8D9AAA] text-[11px]">Strict module import whitelist</div>
              <div className="space-y-1.5">
                {['telnetlib', 'pickle (untrusted)', 'ftplib', 'crypt (legacy)'].map((mod) => (
                  <div key={mod} className="p-2 bg-[#02050B] border border-[#1E3C5C] flex items-center justify-between">
                    <span className="text-[#F1F5F9]">{mod}</span>
                    <span className="text-[10px] text-[#FF304F] font-bold">BLOCKED</span>
                  </div>
                ))}
              </div>
            </div>
          </GlassPanel>

          {/* Pillar 2: Blocked Functions */}
          <GlassPanel
            headerTitle="BLOCKED FUNCTIONS"
            headerCode="RING_02_LOCKED"
            statusIndicator="ACTIVE"
          >
            <div className="space-y-2 font-mono text-xs">
              <div className="text-[#8D9AAA] text-[11px]">Banned sink functions</div>
              <div className="space-y-1.5">
                {['eval()', 'exec()', 'os.system()', '__import__()'].map((fn) => (
                  <div key={fn} className="p-2 bg-[#02050B] border border-[#1E3C5C] flex items-center justify-between">
                    <span className="text-[#F1F5F9]">{fn}</span>
                    <span className="text-[10px] text-[#FF304F] font-bold">PROHIBITED</span>
                  </div>
                ))}
              </div>
            </div>
          </GlassPanel>

          {/* Pillar 3: Mandatory Sanitizers */}
          <GlassPanel
            headerTitle="MANDATORY SANITIZERS"
            headerCode="RING_03_LOCKED"
            statusIndicator="ACTIVE"
          >
            <div className="space-y-2 font-mono text-xs">
              <div className="text-[#8D9AAA] text-[11px]">Required wrapper transformers</div>
              <div className="space-y-1.5">
                {['shlex.quote()', 'html.escape()', 'psycopg2.sql', 'jwt.decode(verify)'].map((san) => (
                  <div key={san} className="p-2 bg-[#02050B] border border-[#1E3C5C] flex items-center justify-between">
                    <span className="text-[#F1F5F9]">{san}</span>
                    <span className="text-[10px] text-[#00E699] font-bold">REQUIRED</span>
                  </div>
                ))}
              </div>
            </div>
          </GlassPanel>

          {/* Pillar 4: Risk Thresholds */}
          <GlassPanel
            headerTitle="RISK THRESHOLDS"
            headerCode="RING_04_LOCKED"
            statusIndicator="ACTIVE"
          >
            <div className="space-y-2 font-mono text-xs">
              <div className="text-[#8D9AAA] text-[11px]">Automated merge gates</div>
              <div className="space-y-2 pt-1">
                <div className="p-2 bg-[#02050B] border border-[#1E3C5C] space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#8D9AAA]">MAX MERGE RISK:</span>
                    <span className="text-[#00CFFF] font-bold">4.0 / 10.0</span>
                  </div>
                  <div className="w-full bg-[#030914] h-1.5">
                    <div className="w-[40%] bg-[#00CFFF] h-full" />
                  </div>
                </div>

                <div className="p-2 bg-[#02050B] border border-[#1E3C5C] space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#8D9AAA]">CURRENT PR RISK:</span>
                    <span className="text-[#00E699] font-bold">1.2 (POST-PATCH)</span>
                  </div>
                  <div className="w-full bg-[#030914] h-1.5">
                    <div className="w-[12%] bg-[#00E699] h-full" />
                  </div>
                </div>
              </div>
            </div>
          </GlassPanel>
        </div>
      </div>
    </section>
  );
};
