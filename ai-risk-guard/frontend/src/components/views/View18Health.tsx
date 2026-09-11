import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId, SubsystemHealth } from '../../types';
import { Activity, Cpu, CheckCircle2, Shield, RefreshCw, Terminal, Server } from 'lucide-react';
import { getHealthReady, getHealthDb, getHealthGemini, getSandboxHealth } from '../../api/client';

const BASE_SUBSYSTEMS: SubsystemHealth[] = [
  { id: 'orch', name: 'ORCHESTRATOR', status: 'HEALTHY', latency: '—', version: 'v2.4.0', uptime: '—', details: 'Webhook ingestion bus, scan queue dispatch, and PR event routing.' },
  { id: 'scanner', name: 'AST SCANNER', status: 'HEALTHY', latency: '—', version: 'v2.4.0', uptime: '—', details: 'Python ast visitor & Shannon entropy detection compiler nodes.' },
  { id: 'policy', name: 'POLICY ENGINE', status: 'HEALTHY', latency: '—', version: 'v2.4.0', uptime: '—', details: 'Enterprise rule gateway verifying imports, sinks, and sanitizers.' },
  { id: 'sandbox', name: 'SANDBOX VALIDATOR', status: 'HEALTHY', latency: '—', version: 'Docker', uptime: '—', details: 'Docker container pool with CPU/RAM quotas and read-only rootfs.' },
  { id: 'store', name: 'PERSISTENCE STORE', status: 'HEALTHY', latency: '—', version: 'SQLite WAL', uptime: '—', details: 'SQLite Write-Ahead Log database storing scans, findings, and audit logs.' },
  { id: 'core', name: 'DEFENSE CORE', status: 'HEALTHY', latency: '—', version: 'v2.4.0', uptime: '—', details: 'Continuous protection loop and GitHub App integration.' },
];

export const View18Health: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const [subsystems, setSubsystems] = useState<SubsystemHealth[]>(BASE_SUBSYSTEMS);
  const [allOperational, setAllOperational] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadHealth = async () => {
    setLoading(true);
    const updated = [...BASE_SUBSYSTEMS];

    try {
      const ready = await getHealthReady();
      updated[0].status = ready.status === 'ready' ? 'HEALTHY' : 'DEGRADED';
      updated[1].status = ready.github_configured ? 'HEALTHY' : 'DEGRADED';
      updated[4].status = ready.db_writable ? 'HEALTHY' : 'OFFLINE';
    } catch {
      updated[0].status = 'DEGRADED';
    }

    try {
      const db = await getHealthDb();
      updated[4].status = db.status === 'ok' ? 'HEALTHY' : 'OFFLINE';
    } catch {
      updated[4].status = 'OFFLINE';
    }

    try {
      const gemini = await getHealthGemini();
      updated[1].status = gemini.status === 'online' ? 'OPTIMAL' : 'HEALTHY';
      updated[5].details = `Gemini: ${gemini.configured ? 'configured' : 'not configured'}`;
    } catch {
      updated[5].status = 'DEGRADED';
    }

    try {
      const sandbox = await getSandboxHealth();
      updated[3].status = sandbox.docker_available ? 'HEALTHY' : 'DEGRADED';
      updated[3].details = sandbox.docker_available
        ? `Docker ${sandbox.image_ready ? 'image ready' : 'image not built'} (mode: ${sandbox.mode})`
        : 'Docker unavailable — sandbox validation offline.';
    } catch {
      updated[3].status = 'DEGRADED';
    }

    const operational = updated.every((s) => s.status !== 'OFFLINE');
    setAllOperational(operational);
    setSubsystems(updated);
    setLoading(false);
  };

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <div className="py-8 px-4 sm:px-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1E3C5C]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00CFFF] tracking-widest mb-1">
            <span>RUNTIME DIAGNOSTICS // 6 CORE SUBSYSTEMS</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            System Health & Runtime Telemetry
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#06101F] border border-[#00E699]/60 font-mono text-xs text-[#00E699]">
            <span className="w-2 h-2 rounded-full bg-[#00E699] animate-pulse" />
            <span>{loading ? 'POLLING SUBSYSTEMS...' : allOperational ? 'ALL SUBSYSTEMS OPERATIONAL' : 'SUBSYSTEM DEGRADATION DETECTED'}</span>
          </div>

          <CyberButton
            variant="secondary"
            size="sm"
            icon={<RefreshCw className="w-3.5 h-3.5" />}
            loading={loading}
            onClick={loadHealth}
          >
            RE-SCAN
          </CyberButton>

          <CyberButton
            variant="secondary"
            size="sm"
            onClick={() => onNavigate('dashboard')}
          >
            ENTER DASHBOARD (VIEW 04)
          </CyberButton>
        </div>
      </div>

      {/* Subsystems Cards Grid (6 Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {(loading ? BASE_SUBSYSTEMS : subsystems).map((sub) => (
          <GlassPanel
            key={sub.id}
            headerTitle={sub.name}
            headerCode={sub.version}
            statusIndicator="ACTIVE"
            className="flex flex-col justify-between h-full"
          >
            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#8D9AAA]">STATUS:</span>
                <span className="px-2 py-0.5 bg-[#00E699]/20 border border-[#00E699] text-[#00E699] font-bold text-[10px]">
                  {sub.status}
                </span>
              </div>

              <div className="p-2.5 bg-[#02050B] border border-[#1E3C5C] space-y-1.5 text-[11px] text-[#8D9AAA]">
                <div className="flex justify-between">
                  <span>PING:</span>
                  <span className="text-[#00CFFF] font-bold">{sub.latency}</span>
                </div>
                <div className="flex justify-between">
                  <span>VERSION:</span>
                  <span className="text-white font-bold">{sub.version}</span>
                </div>
              </div>

              <p className="text-[11px] text-[#B8C2CE] leading-relaxed pt-1">
                {sub.details}
              </p>
            </div>
          </GlassPanel>
        ))}
      </div>
    </div>
  );
};
