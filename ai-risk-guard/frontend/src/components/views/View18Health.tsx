import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId, SubsystemHealth } from '../../types';
import { RefreshCw } from 'lucide-react';
import { getHealthReady, getHealthDb, getHealthGemini, getSandboxHealth } from '../../api/client';

const BASE_SUBSYSTEMS: SubsystemHealth[] = [
  { id: 'orch', name: 'ORCHESTRATOR', status: 'HEALTHY', latency: '—', version: 'v2.4.0', uptime: '—', details: 'Webhook ingestion bus, scan queue dispatch, and PR event routing.' },
  { id: 'scanner', name: 'AST SCANNER', status: 'HEALTHY', latency: '—', version: 'v2.4.0', uptime: '—', details: 'Python ast visitor & Shannon entropy detection compiler nodes.' },
  { id: 'policy', name: 'POLICY ENGINE', status: 'HEALTHY', latency: '—', version: 'v2.4.0', uptime: '—', details: 'Enterprise rule gateway verifying imports, sinks, and sanitizers.' },
  { id: 'sandbox', name: 'SANDBOX VALIDATOR', status: 'HEALTHY', latency: '—', version: 'Docker', uptime: '—', details: 'Docker container pool with CPU/RAM quotas and read-only rootfs.' },
  { id: 'store', name: 'PERSISTENCE STORE', status: 'HEALTHY', latency: '—', version: 'SQLite WAL', uptime: '—', details: 'SQLite Write-Ahead Log database storing scans, findings, and audit logs.' },
  { id: 'core', name: 'DEFENSE CORE', status: 'HEALTHY', latency: '—', version: 'v2.4.0', uptime: '—', details: 'Continuous protection loop and GitHub App integration.' },
  { id: 'llm', name: 'LLM ENGINE // GEMINI', status: 'HEALTHY', latency: '—', version: '—', uptime: '—', details: 'Model fallback chain resolution via Gemini API.' },
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
      updated[6].details = gemini.configured
        ? `Gemini ${gemini.model ? `model: ${gemini.model}` : 'configured'}.${gemini.error ? ` ${gemini.error}` : ''}`
        : 'Gemini not configured — LLM analysis disabled.';
      updated[6].status = gemini.status === 'online' ? 'OPTIMAL' : gemini.status === 'degraded' ? 'DEGRADED' : 'OFFLINE';
      if (gemini.model) updated[6].version = gemini.model;
    } catch {
      updated[6].status = 'DEGRADED';
      updated[6].details = 'Gemini health probe failed.';
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
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] tracking-widest mb-1 bg-gradient-to-r from-[#F0F5FA] via-[#D9E1EA] to-[#A7B4C4] bg-clip-text text-transparent">
            <span>RUNTIME DIAGNOSTICS // 7 SUBSYSTEMS</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            System Health & Runtime Telemetry
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#050B16] border border-[#00E699]/60 font-mono text-xs text-[#00E699]">
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

      {/* Subsystems Cards Grid (7 Cards) */}
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
                <span className="text-[#9AA7B8]">STATUS:</span>
                <span
                  className={`px-2 py-0.5 font-bold text-[10px] border ${
                    sub.status === 'OFFLINE'
                      ? 'bg-[#FF1E2D]/15 border-[#FF1E2D] text-[#FF1E2D]'
                      : sub.status === 'DEGRADED'
                      ? 'bg-[#D9E1EA]/15 border-[#D9E1EA] text-[#EAF1F8] shadow-[0_0_8px_rgba(217,225,234,0.2)]'
                      : 'bg-[#00E699]/20 border-[#00E699] text-[#00E699]'
                  }`}
                >
                  {sub.status}
                </span>
              </div>

              <div className="p-2.5 bg-[#020B1A] border border-[#17406E] space-y-1.5 text-[11px] text-[#9AA7B8]">
                <div className="flex justify-between">
                  <span>PING:</span>
                  <span className="text-[#00A8FF] font-bold">{sub.latency}</span>
                </div>
                <div className="flex justify-between">
                  <span>VERSION:</span>
                  <span className="text-white font-bold">{sub.version}</span>
                </div>
              </div>

              <p className="text-[11px] text-[#C2CDD9] leading-relaxed pt-1">
                {sub.details}
              </p>
            </div>
          </GlassPanel>
        ))}
      </div>
    </div>
  );
};
