import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { Box, Cpu, HardDrive, WifiOff, Clock, Terminal, CheckCircle2 } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';

export const StageSandbox: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  return (
    <section className="relative py-20 px-4 sm:px-6 border-b border-[#1E3C5C]/40">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Stage Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-[#06101F] border border-[#1E3C5C] font-mono text-[10px] text-[#00CFFF] tracking-widest mb-2">
              <span>SCROLL STAGE 06 // ISOLATION VERIFICATION</span>
            </div>
            <h2 className="font-headline text-2xl sm:text-4xl text-white">
              Hardened Container Sandbox Validation
            </h2>
            <p className="font-mono text-xs sm:text-sm text-[#8D9AAA] mt-1">
              Patches are compiled and stress-tested inside an air-gapped Docker container with physical quotas before PR integration.
            </p>
          </div>

          <div className="flex items-center space-x-2 font-mono text-[10px]">
            <span className="px-2.5 py-1 bg-[#00E699]/20 border border-[#00E699]/60 text-[#00E699] font-bold flex items-center space-x-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00E699] animate-pulse" />
              <span>STATUS: VALIDATED (SAFE)</span>
            </span>
          </div>
        </div>

        {/* 4 Hardened Specifications */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 bg-[#06101F]/80 border border-[#1E3C5C] space-y-1">
            <div className="flex items-center space-x-2 text-[#8D9AAA] font-mono text-xs">
              <Cpu className="w-4 h-4 text-[#00CFFF]" />
              <span>CPU LIMIT</span>
            </div>
            <div className="font-headline text-xl font-bold text-white">0.5 CORE MAX</div>
            <div className="font-mono text-[10px] text-[#8D9AAA]">Hard cgroups quota: 50,000 / 100,000</div>
          </div>

          <div className="p-4 bg-[#06101F]/80 border border-[#1E3C5C] space-y-1">
            <div className="flex items-center space-x-2 text-[#8D9AAA] font-mono text-xs">
              <HardDrive className="w-4 h-4 text-[#00CFFF]" />
              <span>MEMORY LIMIT</span>
            </div>
            <div className="font-headline text-xl font-bold text-white">128 MB RAM</div>
            <div className="font-mono text-[10px] text-[#8D9AAA]">OOM-killer enabled on breach</div>
          </div>

          <div className="p-4 bg-[#06101F]/80 border border-[#1E3C5C] space-y-1">
            <div className="flex items-center space-x-2 text-[#8D9AAA] font-mono text-xs">
              <WifiOff className="w-4 h-4 text-[#FF304F]" />
              <span>NETWORK MESH</span>
            </div>
            <div className="font-headline text-xl font-bold text-[#FF304F]">DISABLED</div>
            <div className="font-mono text-[10px] text-[#8D9AAA]">--network=none airgap isolation</div>
          </div>

          <div className="p-4 bg-[#06101F]/80 border border-[#1E3C5C] space-y-1">
            <div className="flex items-center space-x-2 text-[#8D9AAA] font-mono text-xs">
              <Clock className="w-4 h-4 text-[#00E699]" />
              <span>EXEC TIMEOUT</span>
            </div>
            <div className="font-headline text-xl font-bold text-white">10.0 SEC</div>
            <div className="font-mono text-[10px] text-[#8D9AAA]">SIGKILL on timeout breach</div>
          </div>
        </div>

        {/* Execution Terminal & Verification Logs */}
        <GlassPanel
          headerTitle="CONTAINER EXECUTION CONSOLE"
          headerCode="SANDBOX_RUNTIME_04"
          statusIndicator="ACTIVE"
          accentColor="#00E699"
        >
          <div className="p-4 bg-[#02050B] border border-[#1E3C5C] font-mono text-xs space-y-2 text-[#D7DEE7]">
            <div className="text-[#8D9AAA] flex items-center space-x-2">
              <Terminal className="w-3.5 h-3.5 text-[#00CFFF]" />
              <span>SPAWNING CONTAINER: sandbox-exec-9428-cwe78...</span>
            </div>
            <div className="text-[#65E7FF]">[0.02s] docker run --memory=128m --cpus=0.5 --network=none --read-only ai-risk-guard:runtime</div>
            <div className="text-[#D7DEE7]">[0.14s] Mounting AST transformed patch candidate /tmp/patch_executor.py</div>
            <div className="text-[#D7DEE7]">[0.31s] Executing Python syntax test suite: `python3 -m py_compile /tmp/patch_executor.py`</div>
            <div className="text-[#00E699]">[0.52s] SYNTAX_VALIDATION: PASS (Zero syntax errors)</div>
            <div className="text-[#D7DEE7]">[0.78s] Simulating command injection payload: `ping_host("127.0.0.1; cat /etc/passwd")`</div>
            <div className="text-[#00E699]">[1.04s] INJECTION_TEST: PASS (Subshell execution rejected; target parsed safely as argument)</div>
            <div className="text-[#00E699] font-bold">[1.12s] CONTAINER TERMINATED NORMALLY (Exit code: 0)</div>
            <div className="p-2 bg-[#00E699]/15 border border-[#00E699] text-[#00E699] font-bold flex items-center justify-between">
              <span>STATUS: VALIDATED (SAFE)</span>
              <span className="text-white text-[10px]">ALL SHIELD FRAGMENTS ILLUMINATING</span>
            </div>
          </div>
        </GlassPanel>
      </div>
    </section>
  );
};
