import React, { useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { GitCommit, Wrench, CheckCircle, ArrowRight, Play, Cpu, Shield } from 'lucide-react';

export const View08Patch: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const [generating, setGenerating] = useState(false);
  const [patchGenerated, setPatchGenerated] = useState(true);

  const handleGenerate = () => {
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
      setPatchGenerated(true);
    }, 700);
  };

  return (
    <div className="py-8 px-4 sm:px-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1E3C5C]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00CFFF] tracking-widest mb-1">
            <span>CODE SYNTHESIS // AST TRANSFORMER</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Automated Code Remediation Workstation
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <CyberButton
            variant="primary"
            size="md"
            loading={generating}
            icon={<Wrench className="w-4 h-4 text-white" />}
            onClick={handleGenerate}
          >
            {generating ? 'SYNTHESIZING AST PATCH...' : 'GENERATE REMEDIATION'}
          </CyberButton>

          <CyberButton
            variant="secondary"
            size="md"
            icon={<ArrowRight className="w-4 h-4 text-[#00CFFF]" />}
            onClick={() => onNavigate('sandbox')}
          >
            VALIDATE IN SANDBOX (VIEW 09)
          </CyberButton>
        </div>
      </div>

      {/* BEFORE vs AFTER Split Pane */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: BEFORE */}
        <GlassPanel
          headerTitle="BEFORE: VULNERABLE CODE (ORIGINAL AST)"
          headerCode="CWE-78 SINK"
          statusIndicator="ALERT"
          accentColor="#FF304F"
        >
          <div className="font-mono text-xs bg-[#02050B] p-4 border border-[#1E3C5C] space-y-1 text-[#8D9AAA] min-h-[220px]">
            <div className="text-[#8D9AAA]/50"># api/routes/executor.py - Line 40-44</div>
            <div><span className="text-[#00CFFF]">import</span> os</div>
            <div className="pt-2 text-[#00CFFF]">def <span className="text-white">run_backup</span>(target_path):</div>
            <div className="pl-4 text-[#8D9AAA] text-[11px]"># Vulnerable shell invocation with string interpolation</div>
            <div className="pl-4 p-2 bg-[#8F1424]/40 border-l-2 border-[#FF304F] text-[#FF304F] font-bold">
              - os.system(f"tar -czf /tmp/backup.tar.gz &#123;target_path&#125;")
            </div>
            <div className="pl-4 text-[#00CFFF]">return <span className="text-white">True</span></div>
          </div>
        </GlassPanel>

        {/* Right: AFTER */}
        <GlassPanel
          headerTitle="AFTER: VALIDATED SAFE CODE (REMEDIATED AST)"
          headerCode="NodeTransformer APPLIED"
          statusIndicator="ACTIVE"
          accentColor="#00E699"
        >
          <div className="font-mono text-xs bg-[#02050B] p-4 border border-[#1E3C5C] space-y-1 text-[#8D9AAA] min-h-[220px]">
            <div className="text-[#8D9AAA]/50"># Hardened with subprocess.run & shlex quotation</div>
            <div><span className="text-[#00CFFF]">import</span> subprocess, shlex</div>
            <div className="pt-2 text-[#00CFFF]">def <span className="text-white">run_backup</span>(target_path):</div>
            <div className="pl-4 text-[#8D9AAA] text-[11px]"># Sanitized argument array bypassing shell injection</div>
            <div className="pl-4 p-2 bg-[#00E699]/20 border-l-2 border-[#00E699] text-[#00E699] font-bold">
              + safe_target = shlex.quote(target_path)<br />
              + cmd = ["tar", "-czf", "/tmp/backup.tar.gz", safe_target]<br />
              + subprocess.run(cmd, capture_output=True, check=True)
            </div>
            <div className="pl-4 text-[#00CFFF]">return <span className="text-white">True</span></div>
          </div>
        </GlassPanel>
      </div>

      {/* Bottom: UNIFIED DIFF */}
      <GlassPanel
        headerTitle="UNIFIED AST DIFF (GIT PATCH CANDIDATE)"
        headerCode="SHA-256: 4a9e2d...01"
        statusIndicator="ACTIVE"
      >
        <div className="font-mono text-xs bg-[#02050B] p-4 border border-[#1E3C5C] space-y-1 text-[#D7DEE7] overflow-x-auto">
          <div className="text-[#8D9AAA]">diff --git a/api/routes/executor.py b/api/routes/executor.py</div>
          <div className="text-[#8D9AAA]">index 920f1a..88c12e 100644</div>
          <div className="text-[#00CFFF]">--- a/api/routes/executor.py</div>
          <div className="text-[#00CFFF]">+++ b/api/routes/executor.py</div>
          <div className="text-[#65E7FF]">@@ -1,5 +1,7 @@</div>
          <div className="text-[#FF304F] bg-[#8F1424]/30 px-2 py-0.5">- import os</div>
          <div className="text-[#00E699] bg-[#00E699]/15 px-2 py-0.5">+ import subprocess, shlex</div>
          <div className="text-[#8D9AAA] px-2">  def run_backup(target_path):</div>
          <div className="text-[#FF304F] bg-[#8F1424]/30 px-2 py-0.5">-     os.system(f"tar -czf /tmp/backup.tar.gz &#123;target_path&#125;")</div>
          <div className="text-[#00E699] bg-[#00E699]/15 px-2 py-0.5">+     safe_target = shlex.quote(target_path)</div>
          <div className="text-[#00E699] bg-[#00E699]/15 px-2 py-0.5">+     cmd = ["tar", "-czf", "/tmp/backup.tar.gz", safe_target]</div>
          <div className="text-[#00E699] bg-[#00E699]/15 px-2 py-0.5">+     subprocess.run(cmd, capture_output=True, check=True)</div>
          <div className="text-[#8D9AAA] px-2">      return True</div>
        </div>

        <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-[#1E3C5C]/60 font-mono text-xs text-[#8D9AAA]">
          <div>
            TRANSFORMATION ENGINE: <span className="text-[#00CFFF]">SubprocessTransformer (v2.4.0)</span>
          </div>
          <CyberButton
            variant="primary"
            size="sm"
            onClick={() => onNavigate('sandbox')}
            icon={<ArrowRight className="w-3.5 h-3.5" />}
          >
            DISPATCH PATCH TO SANDBOX RUNTIME
          </CyberButton>
        </div>
      </GlassPanel>
    </div>
  );
};
