import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { Terminal, ShieldAlert, Cpu, AlertTriangle, CheckCircle } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';

export const StageAST: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  return (
    <section className="relative py-20 px-4 sm:px-6 border-b border-[#1E3C5C]/40">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Stage Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-[#06101F] border border-[#1E3C5C] font-mono text-[10px] text-[#00CFFF] tracking-widest mb-2">
              <span>SCROLL STAGE 02 // INTELLIGENCE ACTIVATION</span>
            </div>
            <h2 className="font-headline text-2xl sm:text-4xl text-white">
              AST Abstract Syntax Analysis
            </h2>
            <p className="font-mono text-xs sm:text-sm text-[#8D9AAA] mt-1">
              Direct Python compiler parsing isolates call nodes, evaluating syntax trees against Shannon entropy matrices.
            </p>
          </div>

          <div className="flex items-center space-x-2 font-mono text-[10px]">
            <span className="px-2 py-1 bg-[#06101F] border border-[#00CFFF]/40 text-[#00CFFF]">AST: ACTIVE</span>
            <span className="px-2 py-1 bg-[#06101F] border border-[#00CFFF]/40 text-[#65E7FF]">NODE VISITOR: RUNNING</span>
            <span className="px-2 py-1 bg-[#8F1424]/40 border border-[#FF304F]/60 text-[#FF304F]">CWE DETECTION: CRITICAL</span>
          </div>
        </div>

        {/* 3-Column Technical Workstation Layer */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Col 1 (Left 4 cols): Python Source Code */}
          <div className="lg:col-span-4">
            <GlassPanel
              headerTitle="SOURCE FILE: api/routes/executor.py"
              headerCode="TARGET_INGRESS"
              statusIndicator="ACTIVE"
              className="h-full"
            >
              <div className="font-mono text-xs text-[#8D9AAA] space-y-1">
                <div className="text-[#8D9AAA]/50"># Inbound unvalidated request handler</div>
                <div><span className="text-[#00CFFF]">import</span> os, sys, ast</div>
                <div><span className="text-[#00CFFF]">from</span> flask <span className="text-[#00CFFF]">import</span> request</div>
                <div className="pt-2 text-[#00CFFF]">def <span className="text-[#65E7FF]">run_diagnostics</span>(cmd):</div>
                <div className="pl-4 text-[#8D9AAA]"># Vulnerability injection sink</div>
                <div className="pl-4 p-1.5 bg-[#8F1424]/30 border border-[#FF304F] text-[#F1F5F9] rounded-sm relative group">
                  <span className="text-[#FF304F] font-bold">os.system(</span>
                  <span className="text-[#FF304F]">f"ping &#123;cmd&#125;"</span>
                  <span className="text-[#FF304F] font-bold">)</span>
                  <span className="absolute right-2 top-1.5 text-[9px] font-mono text-[#FF304F] px-1 bg-[#030914] border border-[#FF304F]">
                    CWE-78 SINK
                  </span>
                </div>
                <div className="pl-4 text-[#00CFFF]">return <span className="text-[#65E7FF]">{`{"status": "ok"}`}</span></div>
              </div>
            </GlassPanel>
          </div>

          {/* Col 2 (Center 4 cols): AST Visualization Tree */}
          <div className="lg:col-span-4">
            <GlassPanel
              headerTitle="AST COMPILER SYNTAX TREE"
              headerCode="VISITOR_GRAPH"
              statusIndicator="WARNING"
              className="h-full"
            >
              <div className="font-mono text-xs space-y-2.5">
                <div className="p-2 bg-[#030914] border border-[#1E3C5C] flex items-center justify-between">
                  <span className="text-[#65E7FF]">Module</span>
                  <span className="text-[10px] text-[#8D9AAA]">body=[FunctionDef]</span>
                </div>

                <div className="pl-4 border-l border-[#00CFFF]/40 space-y-2">
                  <div className="p-2 bg-[#030914] border border-[#1E3C5C] flex items-center justify-between">
                    <span className="text-[#65E7FF]">FunctionDef: run_diagnostics</span>
                    <span className="text-[10px] text-[#8D9AAA]">args=[cmd]</span>
                  </div>

                  <div className="pl-4 border-l border-[#FF304F]/60 space-y-2">
                    <div className="p-2 bg-[#8F1424]/20 border border-[#FF304F] flex items-center justify-between">
                      <div className="flex items-center space-x-1.5">
                        <span className="w-2 h-2 rounded-full bg-[#FF304F] animate-ping" />
                        <span className="text-[#FF304F] font-bold">Expr &gt; Call &gt; os.system</span>
                      </div>
                      <span className="text-[10px] text-[#FF304F] font-mono">CWE-78</span>
                    </div>

                    <div className="pl-4 text-[11px] text-[#8D9AAA] space-y-1">
                      <div>├─ func: <span className="text-[#00CFFF]">Attribute(id='os', attr='system')</span></div>
                      <div>└─ args: <span className="text-[#FF304F]">JoinedStr(f"ping &#123;cmd&#125;")</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </GlassPanel>
          </div>

          {/* Col 3 (Right 4 cols): Finding Panel */}
          <div className="lg:col-span-4">
            <GlassPanel
              headerTitle="DISCOVERED FINDINGS"
              headerCode="HIGH_SEVERITY"
              statusIndicator="ALERT"
              accentColor="#FF304F"
              className="h-full flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="p-3 bg-[#8F1424]/30 border border-[#FF304F] space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="px-1.5 py-0.5 bg-[#FF304F] text-white font-mono text-[10px] font-bold">
                      CRITICAL
                    </span>
                    <span className="text-[#FF304F] font-mono text-[11px] font-semibold">CWE-78</span>
                  </div>
                  <div className="font-headline font-bold text-sm text-white">
                    OS Command Injection via os.system()
                  </div>
                  <p className="font-mono text-[11px] text-[#D7DEE7]">
                    Untrusted request parameter passed directly to subshell. Enables arbitrary code execution under web process UID.
                  </p>
                </div>

                <div className="p-2.5 bg-[#030914] border border-[#1E3C5C] font-mono text-[11px] space-y-1 text-[#8D9AAA]">
                  <div className="flex justify-between">
                    <span>CONFIDENCE SCORE:</span>
                    <span className="text-[#00E699] font-bold">0.98 / 1.00</span>
                  </div>
                  <div className="flex justify-between">
                    <span>SHANNON ENTROPY:</span>
                    <span className="text-[#65E7FF]">3.42 bits/char</span>
                  </div>
                  <div className="flex justify-between">
                    <span>AST TRANSFORMER:</span>
                    <span className="text-[#00CFFF]">subprocess.run safe repl</span>
                  </div>
                </div>
              </div>

              <div className="pt-4">
                <CyberButton
                  variant="primary"
                  size="sm"
                  className="w-full"
                  onClick={() => onNavigate('patch')}
                >
                  REMEDIATE WITH AST PATCH
                </CyberButton>
              </div>
            </GlassPanel>
          </div>
        </div>
      </div>
    </section>
  );
};
