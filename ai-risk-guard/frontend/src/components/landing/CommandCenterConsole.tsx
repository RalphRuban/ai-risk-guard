import React, { useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { Terminal, Shield, Play, Wrench, Box, Cpu, ArrowRight, CheckCircle2, Lock, Sliders } from 'lucide-react';
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
      <div className="relative p-6 sm:p-10 rounded-xl bg-gradient-to-br from-[#0B2556]/85 via-[#061533]/92 to-[#020716]/98 backdrop-blur-2xl border-2 border-[#184384] shadow-[0_25px_70px_rgba(2,7,22,0.95),inset_0_1px_0_rgba(203,213,225,0.2)]">
        {/* 4 Corner Hex Bolts */}
        <div className="absolute top-3 left-3 w-3 h-3 rounded-full bg-[#CBD5E1] p-[1px] shadow-[0_0_6px_rgba(203,213,225,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#030C22] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#CBD5E1] block transform rotate-45" />
          </div>
        </div>
        <div className="absolute top-3 right-3 w-3 h-3 rounded-full bg-[#CBD5E1] p-[1px] shadow-[0_0_6px_rgba(203,213,225,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#030C22] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#CBD5E1] block transform -rotate-45" />
          </div>
        </div>
        <div className="absolute bottom-3 left-3 w-3 h-3 rounded-full bg-[#CBD5E1] p-[1px] shadow-[0_0_6px_rgba(203,213,225,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#030C22] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#CBD5E1] block transform -rotate-12" />
          </div>
        </div>
        <div className="absolute bottom-3 right-3 w-3 h-3 rounded-full bg-[#CBD5E1] p-[1px] shadow-[0_0_6px_rgba(203,213,225,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#030C22] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#CBD5E1] block transform rotate-30" />
          </div>
        </div>

        <TacticalBracket color="#CBD5E1" size="lg" />

        {/* Tab Header Navigation (80% Navy, 10% Silver, 10% Red) */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b-2 border-[#184384]/60">
          <div className="flex items-center space-x-2 font-mono text-xs overflow-x-auto">
            <button
              onClick={() => setActiveTab('SCANNER')}
              className={`px-3 py-2 border transition-all flex items-center space-x-1.5 ${
                activeTab === 'SCANNER'
                  ? 'bg-[#FF2A4B]/20 border-[#FF2A4B] text-[#FF2A4B] font-semibold shadow-[0_0_15px_rgba(255,42,75,0.25)]'
                  : 'bg-[#030C22] border-[#184384] text-[#94A3B8] hover:text-[#E2E8F0]'
              }`}
            >
              <Terminal className="w-3.5 h-3.5 text-[#CBD5E1]" />
              <span>[01] AST SCANNER</span>
            </button>

            <button
              onClick={() => setActiveTab('DIFF')}
              className={`px-3 py-2 border transition-all flex items-center space-x-1.5 ${
                activeTab === 'DIFF'
                  ? 'bg-[#FF2A4B]/20 border-[#FF2A4B] text-[#FF2A4B] font-semibold shadow-[0_0_15px_rgba(255,42,75,0.25)]'
                  : 'bg-[#030C22] border-[#184384] text-[#94A3B8] hover:text-[#E2E8F0]'
              }`}
            >
              <Wrench className="w-3.5 h-3.5 text-[#CBD5E1]" />
              <span>[02] NodeTransformer DIFF</span>
            </button>

            <button
              onClick={() => setActiveTab('SANDBOX')}
              className={`px-3 py-2 border transition-all flex items-center space-x-1.5 ${
                activeTab === 'SANDBOX'
                  ? 'bg-[#FF2A4B]/20 border-[#FF2A4B] text-[#FF2A4B] font-semibold shadow-[0_0_15px_rgba(255,42,75,0.25)]'
                  : 'bg-[#030C22] border-[#184384] text-[#94A3B8] hover:text-[#E2E8F0]'
              }`}
            >
              <Box className="w-3.5 h-3.5 text-[#CBD5E1]" />
              <span>[03] HARDENED SANDBOX</span>
            </button>

            <button
              onClick={() => setActiveTab('POLICY')}
              className={`px-3 py-2 border transition-all flex items-center space-x-1.5 ${
                activeTab === 'POLICY'
                  ? 'bg-[#FF2A4B]/20 border-[#FF2A4B] text-[#FF2A4B] font-semibold shadow-[0_0_15px_rgba(255,42,75,0.25)]'
                  : 'bg-[#030C22] border-[#184384] text-[#94A3B8] hover:text-[#E2E8F0]'
              }`}
            >
              <Shield className="w-3.5 h-3.5 text-[#CBD5E1]" />
              <span>[04] POLICY GATE</span>
            </button>
          </div>

          <CyberButton
            variant="outline"
            size="sm"
            onClick={() => onNavigate(activeTab === 'SCANNER' ? 'scanner' : activeTab === 'DIFF' ? 'patch' : activeTab === 'SANDBOX' ? 'sandbox' : 'policy')}
            icon={<ArrowRight className="w-3.5 h-3.5 text-[#CBD5E1]" />}
          >
            EXPAND WORKSTATION
          </CyberButton>
        </div>

        {/* Tab 1: Interactive AST Scanner */}
        {activeTab === 'SCANNER' && (
          <div className="pt-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-xs">
              <div className="flex items-center space-x-2">
                <span className="text-[#94A3B8] text-[11px]">BENCHMARK:</span>
                <button
                  onClick={() => { setSample('CMD_INJECTION'); }}
                  className={`px-2.5 py-1 border text-[11px] transition-all ${sample === 'CMD_INJECTION' ? 'bg-[#FF2A4B]/20 border-[#FF2A4B] text-[#FF2A4B] font-semibold' : 'bg-[#030C22] border-[#184384] text-[#94A3B8] hover:text-[#E2E8F0]'}`}
                >
                  Command Injection (CWE-78)
                </button>
                <button
                  onClick={() => { setSample('CODE_INJECTION'); }}
                  className={`px-2.5 py-1 border text-[11px] transition-all ${sample === 'CODE_INJECTION' ? 'bg-[#FF2A4B]/20 border-[#FF2A4B] text-[#FF2A4B] font-semibold' : 'bg-[#030C22] border-[#184384] text-[#94A3B8] hover:text-[#E2E8F0]'}`}
                >
                  Code Injection (CWE-94)
                </button>
                <button
                  onClick={() => { setSample('CLEAN'); }}
                  className={`px-2.5 py-1 border text-[11px] transition-all ${sample === 'CLEAN' ? 'bg-[#CBD5E1]/20 border-[#CBD5E1] text-[#F8FAFC] font-semibold' : 'bg-[#030C22] border-[#184384] text-[#94A3B8] hover:text-[#E2E8F0]'}`}
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
              <div className="lg:col-span-7 p-4 bg-[#020716] border border-[#184384] space-y-1.5 min-h-[220px]">
                <div className="text-[#94A3B8] text-[10px] pb-1 border-b border-[#184384]">INPUT CODE BUFFER</div>
                {sample === 'CMD_INJECTION' && (
                  <>
                    <div><span className="text-[#CBD5E1]">import</span> os, sys</div>
                    <div><span className="text-[#CBD5E1]">def</span> <span className="text-[#F8FAFC]">execute_backup</span>(target):</div>
                    <div className="pl-4 text-[#94A3B8]"># Insecure subshell call</div>
                    <div className="pl-4 p-1.5 bg-[#991B1B]/35 border-l-2 border-[#FF2A4B] text-[#FF2A4B] font-bold">
                      {'os.system(f"ping {target}")'}
                    </div>
                    <div className="pl-4 text-[#CBD5E1]">return <span className="text-[#E2E8F0]">True</span></div>
                  </>
                )}
                {sample === 'CODE_INJECTION' && (
                  <>
                    <div><span className="text-[#CBD5E1]">import</span> ast</div>
                    <div><span className="text-[#CBD5E1]">def</span> <span className="text-[#F8FAFC]">calc_metrics</span>(expression):</div>
                    <div className="pl-4 text-[#94A3B8]"># Arbitrary eval injection</div>
                    <div className="pl-4 p-1.5 bg-[#991B1B]/35 border-l-2 border-[#FF2A4B] text-[#FF2A4B] font-bold">
                      eval(expression)
                    </div>
                    <div className="pl-4 text-[#CBD5E1]">return <span className="text-[#E2E8F0]">True</span></div>
                  </>
                )}
                {sample === 'CLEAN' && (
                  <>
                    <div><span className="text-[#CBD5E1]">import</span> subprocess, shlex</div>
                    <div><span className="text-[#CBD5E1]">def</span> <span className="text-[#F8FAFC]">execute_backup</span>(target):</div>
                    <div className="pl-4 text-[#94A3B8]"># Hardened argument vector</div>
                    <div className="pl-4 p-1.5 bg-[#0B2556] border-l-2 border-[#CBD5E1] text-[#E2E8F0] font-bold">
                      {'subprocess.run(["ping", "-c", "1", shlex.quote(target)], check=True)'}
                    </div>
                    <div className="pl-4 text-[#CBD5E1]">return <span className="text-[#E2E8F0]">True</span></div>
                  </>
                )}
              </div>

              {/* Finding / AST Intelligence (80% Navy, 10% Red Risk, 10% Silver Text) */}
              <div className="lg:col-span-5 p-4 bg-[#061533] border border-[#184384] space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-2 border-b border-[#184384] text-[10px]">
                    <span className="text-[#94A3B8]">AST SCAN RESULT</span>
                    <span className={scanResult.pass ? 'text-[#E2E8F0] font-bold' : 'text-[#FF2A4B] font-bold'}>
                      {scanResult.pass ? 'PASSED (CLEAN)' : 'CRITICAL SINK DETECTED'}
                    </span>
                  </div>

                  <div className="mt-3 space-y-2">
                    <div className="flex justify-between">
                      <span className="text-[#94A3B8]">CWE IDENTIFIER:</span>
                      <span className="text-[#F8FAFC] font-bold">{scanResult.cwe}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94A3B8]">RISK SCORE:</span>
                      <span className={scanResult.pass ? 'text-[#CBD5E1] font-bold' : 'text-[#FF2A4B] font-bold'}>
                        {scanResult.risk} / 10.0
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94A3B8]">SINK LOCATION:</span>
                      <span className="text-[#CBD5E1]">{scanResult.pass ? 'None' : `Line ${scanResult.line}`}</span>
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
                  <div className="p-2 bg-[#0B2556] border border-[#CBD5E1]/40 text-[#E2E8F0] text-center font-bold text-[10px]">
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
              <div className="p-4 bg-[#020716] border border-[#184384] space-y-1">
                <span className="text-[#FF2A4B] text-[10px] block font-bold">VULNERABLE AST (BEFORE)</span>
                <div className="text-[#94A3B8] text-[11px]">- os.system(f"ping &#123;target&#125;")</div>
              </div>
              <div className="p-4 bg-[#020716] border border-[#184384] space-y-1">
                <span className="text-[#E2E8F0] text-[10px] block font-bold">REMEDIATED AST (AFTER)</span>
                <div className="text-[#F8FAFC] text-[11px]">{'+ subprocess.run(["ping", "-c", "1", shlex.quote(target)], check=True)'}</div>
              </div>
            </div>

            <div className="p-4 bg-[#020716] border border-[#184384] font-mono text-xs space-y-1 text-[#E2E8F0]">
              <div className="text-[#94A3B8] text-[10px]">UNIFIED GIT DIFF</div>
              <div className="text-[#FF2A4B] bg-[#991B1B]/25 px-2 py-0.5">- import os</div>
              <div className="text-[#CBD5E1] bg-[#0B2556] px-2 py-0.5">+ import subprocess, shlex</div>
              <div className="text-[#FF2A4B] bg-[#991B1B]/25 px-2 py-0.5">- return os.system(f"ping &#123;target&#125;")</div>
              <div className="text-[#CBD5E1] bg-[#0B2556] px-2 py-0.5">{'+ return subprocess.run(["ping", shlex.quote(target)], check=True)'}</div>
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
              <div className="p-3 bg-[#020716] border border-[#184384]">
                <span className="text-[#94A3B8] text-[10px] block">CPU</span>
                <span className="text-white font-bold">0.5 CORE</span>
              </div>
              <div className="p-3 bg-[#020716] border border-[#184384]">
                <span className="text-[#94A3B8] text-[10px] block">MEMORY</span>
                <span className="text-white font-bold">128 MB</span>
              </div>
              <div className="p-3 bg-[#020716] border border-[#184384]">
                <span className="text-[#94A3B8] text-[10px] block">NETWORK</span>
                <span className="text-[#FF2A4B] font-bold">AIRGAP (NONE)</span>
              </div>
              <div className="p-3 bg-[#020716] border border-[#184384]">
                <span className="text-[#94A3B8] text-[10px] block">TIMEOUT</span>
                <span className="text-[#CBD5E1] font-bold">10.0 SEC</span>
              </div>
            </div>

            <div className="p-4 bg-[#020716] border border-[#184384] space-y-1.5 text-[#E2E8F0]">
              <div className="flex items-center justify-between text-[#94A3B8] text-[10px] pb-2 border-b border-[#184384]">
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
                <div key={i} className={line.includes('VALIDATED') ? 'text-[#E2E8F0] font-bold bg-[#0B2556]/50 px-2 py-0.5' : 'text-[#94A3B8]'}>
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
              <div className="p-3 bg-[#020716] border border-[#184384] space-y-2">
                <span className="text-[#FF2A4B] font-bold text-[10px] block">BANNED SINKS (CRITICAL)</span>
                <div className="space-y-1 text-[#94A3B8]">
                  <div>• os.system()</div>
                  <div>• eval() / exec()</div>
                  <div>• pickle.loads()</div>
                </div>
              </div>

              <div className="p-3 bg-[#020716] border border-[#184384] space-y-2">
                <span className="text-[#CBD5E1] font-bold text-[10px] block">MANDATORY SANITIZERS</span>
                <div className="space-y-1 text-[#94A3B8]">
                  <div>• shlex.quote()</div>
                  <div>• html.escape()</div>
                  <div>• psycopg2.sql</div>
                </div>
              </div>

              <div className="p-3 bg-[#020716] border border-[#184384] space-y-2">
                <span className="text-[#CBD5E1] font-bold text-[10px] block">PR GATE THRESHOLDS</span>
                <div className="space-y-1 text-[#94A3B8]">
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
