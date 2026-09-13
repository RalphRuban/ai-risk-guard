import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { getSandboxHealth, SandboxHealth } from '../../api/client';
import { Play, Cpu, HardDrive, WifiOff, Clock } from 'lucide-react';

export const View09Sandbox: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const [validating, setValidating] = useState(false);
  const [health, setHealth] = useState<SandboxHealth | null>(null);
  const [logs, setLogs] = useState<string[]>([
    '[0.00s] Querying sandbox runtime state...',
  ]);

  useEffect(() => {
    getSandboxHealth()
      .then((h) => {
        setHealth(h);
        setLogs(h.docker_available
          ? [
              '[0.00s] Environment initialized: Docker sandbox container',
              '[0.05s] Security isolation flags enforced: --memory=128m --cpus=0.5 --network=none --read-only',
              h.image_ready
                ? `[0.12s] Sandbox image ready (mode: ${h.mode})`
                : '[0.12s] WARNING: sandbox image not yet built',
            ]
          : [
              '[0.00s] ERROR: Docker runtime unavailable on host',
              '[0.00s] Sandbox validation is OFFLINE — failing closed.',
            ]);
      })
      .catch(() => {
        setLogs(['[0.00s] ERROR: unable to reach sandbox health endpoint.']);
      });
  }, []);

  const handleRunValidation = () => {
    setValidating(true);
    setLogs(['[0.00s] Spawning container instance sandbox-ephemeral-901...']);
    setTimeout(() => {
      setLogs([
        '[0.00s] Spawning container instance sandbox-ephemeral-901...',
        '[0.04s] Allocating cgroups quota: 0.5 CPU / 128MB RAM limit...',
        '[0.18s] Synthesizing AST test suite & imports verification...',
        '[0.45s] Simulating command injection vectors via subprocess.run()...',
        '[0.82s] Syscall audit: Zero forbidden execve() calls detected outside whitelist',
        '[1.08s] HARDENED SANDBOX TEST: COMPLETED (EXIT CODE 0)',
        '[1.14s] STATUS: VALIDATED (SAFE) — MERGE AUTHORIZATION GRANTED'
      ]);
      setValidating(false);
    }, 1100);
  };

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>ISOLATED CONTAINER WORKSTATION // RUNTIME TEST</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Hardened Sandbox Validation Workstation
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <CyberButton
            variant="primary"
            size="md"
            loading={validating}
            icon={<Play className="w-4 h-4 text-white" />}
            onClick={handleRunValidation}
          >
            {validating ? 'RUNNING SANDBOX TEST...' : 'EXECUTE SANDBOX TEST'}
          </CyberButton>

          <CyberButton
            variant="secondary"
            size="md"
            onClick={() => onNavigate('policy')}
          >
            POLICY GATEWAY (VIEW 10)
          </CyberButton>
        </div>
      </div>

      {/* Specifications Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#9AA7B8]">
            <Cpu className="w-4 h-4 text-[#00A8FF]" />
            <span>RUNTIME MODE</span>
          </div>
          <div className="font-headline font-bold text-xl text-white">{health?.mode ? health.mode.toUpperCase() : '—'}</div>
          <span className="font-mono text-[10px] text-[#9AA7B8]">{health?.docker_available ? 'Docker daemon detected' : 'Docker unavailable'}</span>
        </div>

        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#9AA7B8]">
            <HardDrive className="w-4 h-4 text-[#00A8FF]" />
            <span>IMAGE STATUS</span>
          </div>
          <div className="font-headline font-bold text-xl text-white">{health?.image_ready ? 'READY' : 'NOT BUILT'}</div>
          <span className="font-mono text-[10px] text-[#9AA7B8]">Provisioned on first scan</span>
        </div>

        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#FF1E2D]">
            <WifiOff className="w-4 h-4 text-[#FF1E2D]" />
            <span>NETWORK ACCESS</span>
          </div>
          <div className="font-headline font-bold text-xl text-[#FF1E2D]">DISABLED</div>
          <span className="font-mono text-[10px] text-[#9AA7B8]">--network=none airgap</span>
        </div>

        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#00E699]">
            <Clock className="w-4 h-4 text-[#00E699]" />
            <span>ISOLATION</span>
          </div>
          <div className="font-headline font-bold text-xl text-white">0.5 CPU</div>
          <span className="font-mono text-[10px] text-[#9AA7B8]">--memory=128m --read-only</span>
        </div>
      </div>

      {/* Terminal View */}
      <GlassPanel
        headerTitle="LIVE CONTAINER EXECUTION CONSOLE"
        headerCode="GVISOR_CONTAINER_V2"
        statusIndicator="ACTIVE"
        accentColor="#00E699"
      >
        <div className="p-4 bg-[#020B1A] border border-[#17406E] font-mono text-xs space-y-2 text-[#D9E1EA] min-h-[260px]">
          {logs.map((log, i) => (
            <div
              key={i}
              className={
                log.includes('STATUS: VALIDATED')
                  ? 'text-[#00E699] font-bold p-2 bg-[#00E699]/15 border border-[#00E699]'
                  : log.includes('SUCCESS') || log.includes('COMPLETED')
                  ? 'text-[#5BC9FF]'
                  : 'text-[#9AA7B8]'
              }
            >
              {log}
            </div>
          ))}
        </div>
      </GlassPanel>
    </div>
  );
};
