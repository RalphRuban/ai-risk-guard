import React, { useState } from 'react';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { Terminal, Shield, Play, Wrench, Box, ArrowRight } from 'lucide-react';
import { TacticalBracket } from '../common/TacticalBracket';

interface CommandCenterConsoleProps {
  onNavigate: (view: ViewId) => void;
}

export const CommandCenterConsole: React.FC<CommandCenterConsoleProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<'SCANNER' | 'DIFF' | 'SANDBOX' | 'POLICY'>('SCANNER');

  // Scanner state
  const [sample, setSample] = useState<'CMD_INJECTION' | 'CODE_INJECTION' | 'CLEAN'>('CMD_INJECTION');
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState({
    cwe: 'CWE-78',
    sink: 'os.system(f"ping {target}")',
    line: 5,
    risk: 8.8,
    pass: false
  });

  const handleScan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      if (sample === 'CLEAN') {
        setScanResult({
          cwe: 'NONE',
          sink: 'subprocess.run(args, check=True)',
          line: 0,
          risk: 0.8,
          pass: true
        });
      } else {
        setScanResult({
          cwe: sample === 'CMD_INJECTION' ? 'CWE-78' : 'CWE-94',
          sink: sample === 'CMD_INJECTION' ? 'os.system(f"ping {target}")' : 'eval(expression)',
          line: 5,
          risk: 8.8,
          pass: false
        });
      }
    }, 450);
  };

  // Sandbox simulation state
  const [testingSandbox, setTestingSandbox] = useState(false);
  const [sandboxOutput, setSandboxOutput] = useState([
    '[0.02s] Spawn container: docker run --memory=128m --cpus=0.5 --network=none ai-risk-guard:safe',
    '[0.18s] AST compilation check: SUCCESS',
    '[0.45s] Fuzz test: Command injection rejected (quoted argument vector)',
    '[0.92s] Status: VALIDATED (SAFE) — 0 security violations'
  ]);

  const handleRunSandbox = () => {
    setTestingSandbox(true);
    setSandboxOutput(['[0.00s] Initializing airgapped sandbox container...']);
    setTimeout(() => {
      setTestingSandbox(false);
      setSandboxOutput([
        '[0.02s] Allocating cgroups quota: 0.5 CPU / 128MB RAM limit...',
        '[0.14s] Mounting AST transformed candidate /tmp/patch.py...',
        '[0.35s] Executing py_compile syntax test suite -> PASS',
        '[0.68s] Injection vector test: Disarmed by shlex quotation array',
        '[0.95s] Exit code 0 -> STATUS: VALIDATED (SAFE)'
      ]);
    }, 700);
  };

  return (
    <section className="relative py-20 px-4 sm:px-8 xl:px-12 max-w-[1760px] mx-auto space-y-6">
      <div className="relative p-6 sm:p-10 rounded-xl bg-gradient-to-br from-[#0B2A5E]/85 via-[#071A2E]/92 to-[#020B1A]/98 backdrop-blur-2xl border-2 border-[#17406E] shadow-[0_25px_70px_rgba(2,11,26,0.95),inset_0_1px_0_rgba(217,225,234,0.2)]">
        {/* 4 Corner Hex Bolts */}
        <div className="absolute top-3 left-3 w-3 h-3 rounded-full bg-[#D9E1EA] p-[1px] shadow-[0_0_6px_rgba(217,225,234,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform rotate-45" />
          </div>
        </div>
        <div className="absolute top-3 right-3 w-3 h-3 rounded-full bg-[#D9E1EA] p-[1px] shadow-[0_0_6px_rgba(217,225,234,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform -rotate-45" />
          </div>
        </div>
        <div className="absolute bottom-3 left-3 w-3 h-3 rounded-full bg-[#D9E1EA] p-[1px] shadow-[0_0_6px_rgba(217,225,234,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform -rotate-12" />
          </div>
        </div>
        <div className="absolute bottom-3 right-3 w-3 h-3 rounded-full bg-[#D9E1EA] p-[1px] shadow-[0_0_6px_rgba(217,225,234,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform rotate-30" />
          </div>
        </div>

        <TacticalBracket color="#D9E1EA" size="lg" />

        {/* Tab Header Navigation (80% Navy, 10% Silver, 10% Red) */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b-2 border-[#17406E]/60">
          <div className="flex items-center space-x-2 font-mono text-xs overflow-x-auto">
            <button
              onClick={() => setActiveTab('SCANNER')}
              className={`px-3 py-2 border transition-all flex items-center space-x-1.5 ${
                activeTab === 'SCANNER'
                  ? 'bg-[#FF1E2D]/20 border-[#FF1E2D] text-[#FF1E2D] font-semibold shadow-[0_0_15px_rgba(255,30,45,0.25)]'
                  : 'bg-[#050B16] border-[#17406E] text-[#A7B4C4] hover:text-[#DEE7F0]'
              }`}
            >
              <Terminal className="w-3.5 h-3.5 text-[#D9E1EA]" />
              <span>[01] AST SCANNER</span>
            </button>

            <button
              onClick={() => setActiveTab('DIFF')}
              className={`px-3 py-2 border transition-all flex items-center space-x-1.5 ${
                activeTab === 'DIFF'
                  ? 'bg-[#FF1E2D]/20 border-[#FF1E2D] text-[#FF1E2D] font-semibold shadow-[0_0_15px_rgba(255,30,45,0.25)]'
                  : 'bg-[#050B16] border-[#17406E] text-[#A7B4C4] hover:text-[#DEE7F0]'
              }`}
            >
              <Wrench className="w-3.5 h-3.5 text-[#D9E1EA]" />
              <span>[02] NodeTransformer DIFF</span>
            </button>

            <button
              onClick={() => setActiveTab('SANDBOX')}
              className={`px-3 py-2 border transition-all flex items-center space-x-1.5 ${
                activeTab === 'SANDBOX'
                  ? 'bg-[#FF1E2D]/20 border-[#FF1E2D] text-[#FF1E2D] font-semibold shadow-[0_0_15px_rgba(255,30,45,0.25)]'
                  : 'bg-[#050B16] border-[#17406E] text-[#A7B4C4] hover:text-[#DEE7F0]'
              }`}
            >
              <Box className="w-3.5 h-3.5 text-[#D9E1EA]" />
              <span>[03] HARDENED SANDBOX</span>
            </button>

            <button
              onClick={() => setActiveTab('POLICY')}
              className={`px-3 py-2 border transition-all flex items-center space-x-1.5 ${
                activeTab === 'POLICY'
                  ? 'bg-[#FF1E2D]/20 border-[#FF1E2D] text-[#FF1E2D] font-semibold shadow-[0_0_15px_rgba(255,30,45,0.25)]'
                  : 'bg-[#050B16] border-[#17406E] text-[#A7B4C4] hover:text-[#DEE7F0]'
              }`}
            >
              <Shield className="w-3.5 h-3.5 text-[#D9E1EA]" />
              <span>[04] POLICY GATE</span>
            </button>
          </div>

          <CyberButton
            variant="outline"
            size="sm"
            onClick={() => onNavigate(activeTab === 'SCANNER' ? 'scanner' : activeTab === 'DIFF' ? 'patch' : activeTab === 'SANDBOX' ? 'sandbox' : 'policy')}
            icon={<ArrowRight className="w-3.5 h-3.5 text-[#D9E1EA]" />}
          >
            EXPAND WORKSTATION
          </CyberButton>
        </div>

        {/* Tab 1: Interactive AST Scanner */}
        {activeTab === 'SCANNER' && (
          <div className="pt-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-xs">
              <div className="flex items-center space-x-2">
                <span className="text-[#A7B4C4] text-[11px]">BENCHMARK:</span>
                <button
                  onClick={() => { setSample('CMD_INJECTION'); }}
                  className={`px-2.5 py-1 border text-[11px] transition-all ${sample === 'CMD_INJECTION' ? 'bg-[#FF1E2D]/20 border-[#FF1E2D] text-[#FF1E2D] font-semibold' : 'bg-[#050B16] border-[#17406E] text-[#A7B4C4] hover:text-[#DEE7F0]'}`}
                >
                  Command Injection (CWE-78)
                </button>
                <button
                  onClick={() => { setSample('CODE_INJECTION'); }}
                  className={`px-2.5 py-1 border text-[11px] transition-all ${sample === 'CODE_INJECTION' ? 'bg-[#FF1E2D]/20 border-[#FF1E2D] text-[#FF1E2D] font-semibold' : 'bg-[#050B16] border-[#17406E] text-[#A7B4C4] hover:text-[#DEE7F0]'}`}
                >
                  Code Injection (CWE-94)
                </button>
                <button
                  onClick={() => { setSample('CLEAN'); }}
                  className={`px-2.5 py-1 border text-[11px] transition-all ${sample === 'CLEAN' ? 'bg-[#D9E1EA]/20 border-[#D9E1EA] text-[#EAF1F8] font-semibold' : 'bg-[#050B16] border-[#17406E] text-[#A7B4C4] hover:text-[#DEE7F0]'}`}
                >
                  Clean Code
                </button>
              </div>

              <CyberButton
                variant="primary"
                size="sm"
                loading={isScanning}
                icon={<Play className="w-3 h-3 text-white" />}
                onClick={handleScan}
              >
                {isScanning ? 'PARSING AST...' : 'RUN SCAN'}
              </CyberButton>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 font-mono text-xs">
              {/* Code Panel (80% Navy, 10% Red Sink, 10% Silver text) */}
              <div className="lg:col-span-7 p-4 bg-[#020B1A] border border-[#17406E] space-y-1.5 min-h-[220px]">
                <div className="text-[#A7B4C4] text-[10px] pb-1 border-b border-[#17406E]">INPUT CODE BUFFER</div>
                {sample === 'CMD_INJECTION' && (
                  <>
                    <div><span className="text-[#D9E1EA]">import</span> os, sys</div>
                    <div><span className="text-[#D9E1EA]">def</span> <span className="text-[#EAF1F8]">execute_backup</span>(target):</div>
                    <div className="pl-4 text-[#A7B4C4]"># Insecure subshell call</div>
                    <div className="pl-4 p-1.5 bg-[#A01D29]/35 border-l-2 border-[#FF1E2D] text-[#FF1E2D] font-bold">
                      {'os.system(f"ping {target}")'}
                    </div>
                    <div className="pl-4 text-[#D9E1EA]">return <span className="text-[#DEE7F0]">True</span></div>
                  </>
                )}
                {sample === 'CODE_INJECTION' && (
                  <>
                    <div><span className="text-[#D9E1EA]">import</span> ast</div>
                    <div><span className="text-[#D9E1EA]">def</span> <span className="text-[#EAF1F8]">calc_metrics</span>(expression):</div>
                    <div className="pl-4 text-[#A7B4C4]"># Arbitrary eval injection</div>
                    <div className="pl-4 p-1.5 bg-[#A01D29]/35 border-l-2 border-[#FF1E2D] text-[#FF1E2D] font-bold">
                      eval(expression)
                    </div>
                    <div className="pl-4 text-[#D9E1EA]">return <span className="text-[#DEE7F0]">True</span></div>
                  </>
                )}
                {sample === 'CLEAN' && (
                  <>
                    <div><span className="text-[#D9E1EA]">import</span> subprocess, shlex</div>
                    <div><span className="text-[#D9E1EA]">def</span> <span className="text-[#EAF1F8]">execute_backup</span>(target):</div>
                    <div className="pl-4 text-[#A7B4C4]"># Hardened argument vector</div>
                    <div className="pl-4 p-1.5 bg-[#0B2A5E] border-l-2 border-[#D9E1EA] text-[#DEE7F0] font-bold">
                      {'subprocess.run(["ping", "-c", "1", shlex.quote(target)], check=True)'}
                    </div>
                    <div className="pl-4 text-[#D9E1EA]">return <span className="text-[#DEE7F0]">True</span></div>
                  </>
                )}
              </div>

              {/* Finding / AST Intelligence (80% Navy, 10% Red Risk, 10% Silver Text) */}
              <div className="lg:col-span-5 p-4 bg-[#071A2E] border border-[#17406E] space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-2 border-b border-[#17406E] text-[10px]">
                    <span className="text-[#A7B4C4]">AST SCAN RESULT</span>
                    <span className={scanResult.pass ? 'text-[#DEE7F0] font-bold' : 'text-[#FF1E2D] font-bold'}>
                      {scanResult.pass ? 'PASSED (CLEAN)' : 'CRITICAL SINK DETECTED'}
                    </span>
                  </div>

                  <div className="mt-3 space-y-2">
                    <div className="flex justify-between">
                      <span className="text-[#A7B4C4]">CWE IDENTIFIER:</span>
                      <span className="text-[#EAF1F8] font-bold">{scanResult.cwe}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#A7B4C4]">RISK SCORE:</span>
                      <span className={scanResult.pass ? 'text-[#D9E1EA] font-bold' : 'text-[#FF1E2D] font-bold'}>
                        {scanResult.risk} / 10.0
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#A7B4C4]">SINK LOCATION:</span>
                      <span className="text-[#D9E1EA]">{scanResult.pass ? 'None' : `Line ${scanResult.line}`}</span>
                    </div>
                  </div>
                </div>

                {!scanResult.pass ? (
                  <CyberButton
                    variant="primary"
                    size="sm"
                    className="w-full"
                    onClick={() => setActiveTab('DIFF')}
                  >
                    GENERATE AST PATCH
                  </CyberButton>
                ) : (
                  <div className="p-2 bg-[#0B2A5E] border border-[#D9E1EA]/40 text-[#DEE7F0] text-center font-bold text-[10px]">
                    AST IS COMPLIANT WITH ENTERPRISE POLICY
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Unified Diff & Remediation (Navy, Red, Silver) */}
        {activeTab === 'DIFF' && (
          <div className="pt-6 space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 font-mono text-xs">
              <div className="p-4 bg-[#020B1A] border border-[#17406E] space-y-1">
                <span className="text-[#FF1E2D] text-[10px] block font-bold">VULNERABLE AST (BEFORE)</span>
                <div className="text-[#A7B4C4] text-[11px]">- os.system(f"ping &#123;target&#125;")</div>
              </div>
              <div className="p-4 bg-[#020B1A] border border-[#17406E] space-y-1">
                <span className="text-[#DEE7F0] text-[10px] block font-bold">REMEDIATED AST (AFTER)</span>
                <div className="text-[#EAF1F8] text-[11px]">{'+ subprocess.run(["ping", "-c", "1", shlex.quote(target)], check=True)'}</div>
              </div>
            </div>

            <div className="p-4 bg-[#020B1A] border border-[#17406E] font-mono text-xs space-y-1 text-[#DEE7F0]">
              <div className="text-[#A7B4C4] text-[10px]">UNIFIED GIT DIFF</div>
              <div className="text-[#FF1E2D] bg-[#A01D29]/25 px-2 py-0.5">- import os</div>
              <div className="text-[#D9E1EA] bg-[#0B2A5E] px-2 py-0.5">+ import subprocess, shlex</div>
              <div className="text-[#FF1E2D] bg-[#A01D29]/25 px-2 py-0.5">- return os.system(f"ping &#123;target&#125;")</div>
              <div className="text-[#D9E1EA] bg-[#0B2A5E] px-2 py-0.5">{'+ return subprocess.run(["ping", shlex.quote(target)], check=True)'}</div>
            </div>

            <div className="flex justify-end">
              <CyberButton
                variant="primary"
                size="sm"
                onClick={() => setActiveTab('SANDBOX')}
              >
                SUBMIT TO HARDENED SANDBOX &gt;
              </CyberButton>
            </div>
          </div>
        )}

        {/* Tab 3: Hardened Sandbox Console (Navy, Red, Silver) */}
        {activeTab === 'SANDBOX' && (
          <div className="pt-6 space-y-4 font-mono text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-3 bg-[#020B1A] border border-[#17406E]">
                <span className="text-[#A7B4C4] text-[10px] block">CPU</span>
                <span className="text-white font-bold">0.5 CORE</span>
              </div>
              <div className="p-3 bg-[#020B1A] border border-[#17406E]">
                <span className="text-[#A7B4C4] text-[10px] block">MEMORY</span>
                <span className="text-white font-bold">128 MB</span>
              </div>
              <div className="p-3 bg-[#020B1A] border border-[#17406E]">
                <span className="text-[#A7B4C4] text-[10px] block">NETWORK</span>
                <span className="text-[#FF1E2D] font-bold">AIRGAP (NONE)</span>
              </div>
              <div className="p-3 bg-[#020B1A] border border-[#17406E]">
                <span className="text-[#A7B4C4] text-[10px] block">TIMEOUT</span>
                <span className="text-[#D9E1EA] font-bold">10.0 SEC</span>
              </div>
            </div>

            <div className="p-4 bg-[#020B1A] border border-[#17406E] space-y-1.5 text-[#DEE7F0]">
              <div className="flex items-center justify-between text-[#A7B4C4] text-[10px] pb-2 border-b border-[#17406E]">
                <span>CONTAINER RUNTIME LOG STREAM</span>
                <CyberButton
                  variant="secondary"
                  size="sm"
                  loading={testingSandbox}
                  onClick={handleRunSandbox}
                >
                  RUN TEST IN CONTAINER
                </CyberButton>
              </div>

              {sandboxOutput.map((line, i) => (
                <div key={i} className={line.includes('VALIDATED') ? 'text-[#DEE7F0] font-bold bg-[#0B2A5E]/50 px-2 py-0.5' : 'text-[#A7B4C4]'}>
                  {line}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Policy Enforcement (Navy, Red, Silver) */}
        {activeTab === 'POLICY' && (
          <div className="pt-6 space-y-4 font-mono text-xs">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-2">
                <span className="text-[#FF1E2D] font-bold text-[10px] block">BANNED SINKS (CRITICAL)</span>
                <div className="space-y-1 text-[#A7B4C4]">
                  <div>• os.system()</div>
                  <div>• eval() / exec()</div>
                  <div>• pickle.loads()</div>
                </div>
              </div>

              <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-2">
                <span className="text-[#D9E1EA] font-bold text-[10px] block">MANDATORY SANITIZERS</span>
                <div className="space-y-1 text-[#A7B4C4]">
                  <div>• shlex.quote()</div>
                  <div>• html.escape()</div>
                  <div>• psycopg2.sql</div>
                </div>
              </div>

              <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-2">
                <span className="text-[#D9E1EA] font-bold text-[10px] block">PR GATE THRESHOLDS</span>
                <div className="space-y-1 text-[#A7B4C4]">
                  <div>• Max Permissible: 4.0/10</div>
                  <div>• Auto-Patch: &gt;= 7.0</div>
                  <div>• Airgap Verification: Strict</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
