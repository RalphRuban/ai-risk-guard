import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { CheckCircle2, ShieldAlert, Cpu, GitCommit, ArrowRight, Code } from 'lucide-react';

export const StagePatch: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  return (
    <section className="relative py-20 px-4 sm:px-6 border-b border-[#1E3C5C]/40">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Stage Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-[#06101F] border border-[#1E3C5C] font-mono text-[10px] text-[#00CFFF] tracking-widest mb-2">
              <span>SCROLL STAGE 05 // DETERMINISTIC REMEDIATION</span>
            </div>
            <h2 className="font-headline text-2xl sm:text-4xl text-white">
              Automated Remediation & AST Diff
            </h2>
            <p className="font-mono text-xs sm:text-sm text-[#8D9AAA] mt-1">
              `ast.NodeTransformer` surgically rewrites vulnerable calls into hardened parameterized structures without breaking adjacent logic.
            </p>
          </div>

          <div className="flex items-center space-x-2 font-mono text-[10px]">
            <span className="px-2.5 py-1 bg-[#00E699]/20 border border-[#00E699]/50 text-[#00E699] font-bold">
              PATCH GENERATED
            </span>
            <span className="px-2.5 py-1 bg-[#087BFF]/20 border border-[#00CFFF]/50 text-[#00CFFF]">
              VALIDATION PENDING
            </span>
          </div>
        </div>

        {/* Dual Pane: Vulnerable Code (Left) vs Safe Code (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Left: Vulnerable Code */}
          <GlassPanel
            headerTitle="ORIGINAL VULNERABLE CODE"
            headerCode="CWE-78 DETECTED"
            statusIndicator="ALERT"
            accentColor="#FF304F"
          >
            <div className="font-mono text-xs text-[#8D9AAA] space-y-1">
              <div className="text-[#8D9AAA]/50"># Insecure shell invocation</div>
              <div><span className="text-[#00CFFF]">import</span> os</div>
              <div className="pt-2 text-[#00CFFF]">def <span className="text-white">ping_host</span>(target):</div>
              <div className="pl-4 text-[#8D9AAA] text-[11px]"># Flawed concatenation passed to sh -c</div>
              <div className="pl-4 p-2 bg-[#8F1424]/40 border-l-2 border-[#FF304F] text-[#FF304F] font-bold">
                - return os.system(f"ping -c 1 &#123;target&#125;")
              </div>
            </div>
          </GlassPanel>

          {/* Right: Safe Code */}
          <GlassPanel
            headerTitle="AST TRANSFORMED SAFE REPLACEMENT"
            headerCode="NodeTransformer APPLIED"
            statusIndicator="ACTIVE"
            accentColor="#00E699"
          >
            <div className="font-mono text-xs text-[#8D9AAA] space-y-1">
              <div className="text-[#8D9AAA]/50"># Parameterized array without subshell</div>
              <div><span className="text-[#00CFFF]">import</span> subprocess, shlex</div>
              <div className="pt-2 text-[#00CFFF]">def <span className="text-white">ping_host</span>(target):</div>
              <div className="pl-4 text-[#8D9AAA] text-[11px]"># Hardened execution bypassing shell injection</div>
              <div className="pl-4 p-2 bg-[#00E699]/15 border-l-2 border-[#00E699] text-[#00E699] font-bold">
                + cmd = ["ping", "-c", "1", shlex.quote(target)]<br />
                + return subprocess.run(cmd, capture_output=True, check=True)
              </div>
            </div>
          </GlassPanel>
        </div>

        {/* Bottom: Unified Diff Workstation */}
        <GlassPanel
          headerTitle="UNIFIED AST DIFF (GIT SPECIFICATION)"
          headerCode="SUBPROCESS_TRANSFORMER_V2"
          statusIndicator="ACTIVE"
        >
          <div className="font-mono text-xs bg-[#02050B] p-4 border border-[#1E3C5C] space-y-1.5 overflow-x-auto text-[#D7DEE7]">
            <div className="text-[#8D9AAA]">--- a/api/routes/executor.py</div>
            <div className="text-[#8D9AAA]">+++ b/api/routes/executor.py</div>
            <div className="text-[#00CFFF]">@@ -1,5 +1,6 @@</div>
            <div className="text-[#FF304F] bg-[#8F1424]/20 px-2 py-0.5">- import os</div>
            <div className="text-[#00E699] bg-[#00E699]/15 px-2 py-0.5">+ import subprocess, shlex</div>
            <div className="text-[#8D9AAA] px-2">  def ping_host(target):</div>
            <div className="text-[#FF304F] bg-[#8F1424]/20 px-2 py-0.5">-     return os.system(f"ping -c 1 &#123;target&#125;")</div>
            <div className="text-[#00E699] bg-[#00E699]/15 px-2 py-0.5">+     cmd = ["ping", "-c", "1", shlex.quote(target)]</div>
            <div className="text-[#00E699] bg-[#00E699]/15 px-2 py-0.5">+     return subprocess.run(cmd, capture_output=True, check=True)</div>
          </div>

          <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="font-mono text-[11px] text-[#8D9AAA]">
              DISPATCH SIGNAL: <span className="text-[#00CFFF]">SAFE PATCH SIGNAL TRAVELING TO SHIELD CORE</span>
            </div>
            <CyberButton
              variant="primary"
              size="sm"
              icon={<ArrowRight className="w-3.5 h-3.5" />}
              onClick={() => onNavigate('sandbox')}
            >
              DISPATCH TO HARDENED SANDBOX (STAGE 06)
            </CyberButton>
          </div>
        </GlassPanel>
      </div>
    </section>
  );
};
