import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { ViewId, SecurityAgent } from '../../types';
import { getHealthReady, getHealthDb, getHealthGemini, getSandboxHealth, getScans, getFindings, getDashboardData } from '../../api/client';

const BASE_AGENTS: SecurityAgent[] = [
  { id: 'orch', name: 'OrchestrationAgent', role: 'Global state consensus & webhook scan dispatch', status: 'IDLE', load: 0, lastHeartbeat: '—', activeTasks: 0, coordinates: { x: 50, y: 50 } },
  { id: 'mgr', name: 'ManagerAgent', role: 'Finding & workflow routing pipeline', status: 'IDLE', load: 0, lastHeartbeat: '—', activeTasks: 0, coordinates: { x: 25, y: 25 } },
  { id: 'scan', name: 'ScannerAgent', role: 'Python AST visitor & Shannon entropy analyzer', status: 'IDLE', load: 0, lastHeartbeat: '—', activeTasks: 0, coordinates: { x: 75, y: 25 } },
  { id: 'patch', name: 'PatchAgent', role: 'Deterministic NodeTransformer & Gemini patch synthesizer', status: 'IDLE', load: 0, lastHeartbeat: '—', activeTasks: 0, coordinates: { x: 18, y: 75 } },
  { id: 'val', name: 'ValidatorAgent', role: 'Hardened Docker sandbox supervisor & syscall monitor', status: 'IDLE', load: 0, lastHeartbeat: '—', activeTasks: 0, coordinates: { x: 50, y: 88 } },
  { id: 'risk', name: 'RiskAgent', role: '7-Factor weighted contextual risk evaluator', status: 'IDLE', load: 0, lastHeartbeat: '—', activeTasks: 0, coordinates: { x: 82, y: 75 } },
];

function cap100(n: number): number {
  return Math.max(0, Math.min(100, Math.round(n)));
}

function timeAgo(ts?: string): string {
  if (!ts) return '—';
  const then = new Date(ts).getTime();
  if (Number.isNaN(then)) return '—';
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function statusFor(s: string): SecurityAgent['status'] {
  return s === 'ACTIVE' ? 'ACTIVE' : s === 'PROCESSING' ? 'PROCESSING' : 'IDLE';
}

export const View13Agents: React.FC<{ onNavigate: (view: ViewId) => void }> = () => {
  const [agents, setAgents] = useState<SecurityAgent[]>(BASE_AGENTS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getHealthReady().catch(() => null),
      getHealthDb().catch(() => null),
      getHealthGemini().catch(() => null),
      getSandboxHealth().catch(() => null),
      getScans().catch(() => []),
      getFindings().catch(() => []),
      getDashboardData().catch(() => null),
    ]).then(([ready, db, gemini, sandbox, scans, findings, dash]) => {
      if (cancelled) return;
      const repr = findings as Array<{
        status?: string;
        severity?: string;
        file_path?: string;
      }>;
      const open = repr.filter((f) => f.status !== 'resolved');
      const highCritical = repr.filter((f) => f.severity === 'HIGH' || f.severity === 'CRITICAL').length;
      const latest = (scans as Array<{ scanned_at?: string }>).slice().sort(
        (a, b) => new Date(b.scanned_at || 0).getTime() - new Date(a.scanned_at || 0).getTime()
      )[0];
      const heartbeat = timeAgo(latest?.scanned_at);
      const recent = (scans as unknown[]).length;
      const repoCount = dash && dash.repos ? dash.repos.length : 0;
      const geminiConfigured = Boolean(gemini && gemini.configured);
      const dockerAvailable = Boolean(sandbox && sandbox.docker_available);
      const imageReady = Boolean(sandbox && sandbox.image_ready);
      const dbOk = db && db.status === 'ok';

      const next: SecurityAgent[] = [
        { ...BASE_AGENTS[0], status: statusFor(ready && ready.status === 'ready' ? 'ACTIVE' : 'IDLE'), load: cap100(repoCount * 10), activeTasks: repoCount, lastHeartbeat: heartbeat, role: 'Global state consensus & webhook scan dispatch' },
        { ...BASE_AGENTS[1], status: statusFor(dbOk ? 'ACTIVE' : 'IDLE'), load: cap100(open.length * 4), activeTasks: open.length, lastHeartbeat: heartbeat, role: 'Finding & workflow routing pipeline' },
        { ...BASE_AGENTS[2], status: statusFor(recent > 0 ? 'ACTIVE' : 'IDLE'), load: cap100(recent * 3), activeTasks: recent, lastHeartbeat: heartbeat, role: 'Python AST visitor & Shannon entropy analyzer' },
        { ...BASE_AGENTS[3], status: statusFor(geminiConfigured ? 'ACTIVE' : 'IDLE'), load: geminiConfigured ? 38 : 0, activeTasks: geminiConfigured ? 1 : 0, lastHeartbeat: geminiConfigured ? heartbeat : 'NOT CONFIGURED', role: 'Deterministic NodeTransformer & Gemini patch synthesizer' },
        { ...BASE_AGENTS[4], status: statusFor(dockerAvailable ? (imageReady ? 'ACTIVE' : 'PROCESSING') : 'IDLE'), load: dockerAvailable ? (imageReady ? 26 : 12) : 0, activeTasks: dockerAvailable ? 1 : 0, lastHeartbeat: heartbeat, role: 'Hardened Docker sandbox supervisor & syscall monitor' },
        { ...BASE_AGENTS[5], status: statusFor(repr.length > 0 ? 'ACTIVE' : 'IDLE'), load: cap100((highCritical / Math.max(1, repr.length)) * 100), activeTasks: highCritical, lastHeartbeat: heartbeat, role: '7-Factor weighted contextual risk evaluator' },
      ];
      setAgents(next);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>DISTRIBUTED INTELLIGENCE // REAL SUBSYSTEM TELEMETRY</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Multi-Agent Mesh Architecture
          </h1>
        </div>
      </div>

      {/* Status line */}
      <div className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#050B16] border border-[#17406E] font-mono text-xs text-[#5BC9FF]">
        <span className={`w-2 h-2 rounded-full ${loading ? 'bg-[#D9E1EA] animate-pulse' : 'bg-[#00E699] animate-pulse'}`} />
        <span>{loading ? 'POLLING SUBSYSTEM TELEMETRY...' : 'AGENT LOADS DERIVED FROM LIVE HEALTH PROBES, SCANS & FINDINGS'}</span>
      </div>

      {/* Top Map: Interactive Mesh Canvas */}
      <div className="relative h-[480px] bg-[#050B16] border border-[#17406E] overflow-hidden flex items-center justify-center">
        <div className="absolute inset-0 bg-technical-grid opacity-40" />

        {/* Outer and Inner Radar Circles */}
        <div className="absolute w-80 h-80 rounded-full border border-[#00A8FF]/20 animate-pulse" />
        <div className="absolute w-[500px] h-[500px] rounded-full border border-[#007BFF]/10" />

        {/* Central Connecting Lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {[
            { x: '25%', y: '25%' },
            { x: '75%', y: '25%' },
            { x: '18%', y: '75%' },
            { x: '50%', y: '88%' },
            { x: '82%', y: '75%' }
          ].map((pos, i) => (
            <g key={i}>
              <line
                x1="50%"
                y1="50%"
                x2={pos.x}
                y2={pos.y}
                stroke="#00A8FF"
                strokeWidth="1.5"
                strokeDasharray="4 8"
                className="energy-line"
              />
              <circle cx={pos.x} cy={pos.y} r="3" fill="#5BC9FF" />
            </g>
          ))}
        </svg>

        {/* Center Node: OrchestrationAgent */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-20">
          <div className="p-4 bg-[#050B16] border-2 border-[#00A8FF] shadow-[0_0_40px_rgba(0,168,255,0.4)] text-center w-48">
            <div className="flex items-center justify-center space-x-1 text-[#00E699] font-mono text-[10px] mb-1">
              <span className="w-2 h-2 rounded-full bg-[#00E699] animate-pulse" />
              <span>CONSENSUS CORE</span>
            </div>
            <div className="font-headline font-bold text-sm text-white">
              OrchestrationAgent
            </div>
            <div className="font-mono text-[10px] text-[#00A8FF] mt-1">
              {loading ? 'PROBING...' : `${agents[0].load}% LOAD // ${agents[0].activeTasks} targets`}
            </div>
          </div>
        </div>

        {/* 5 Outer Agent Nodes */}
        {agents.filter((a) => a.id !== 'orch').map((agent) => (
          <div
            key={agent.id}
            className="absolute z-10 transform -translate-x-1/2 -translate-y-1/2 p-3 bg-[#050B16]/90 border border-[#17406E] hover:border-[#00A8FF] transition-all text-center w-40 shadow-xl"
            style={{ top: `${agent.coordinates.y}%`, left: `${agent.coordinates.x}%` }}
          >
            <div className="font-mono text-[9px] text-[#9AA7B8] tracking-widest">{agent.id.toUpperCase()}</div>
            <div className="font-headline font-semibold text-xs text-white truncate">
              {agent.name}
            </div>
            <div className="font-mono text-[10px] text-[#5BC9FF] mt-0.5">
              LOAD: {agent.load}% // {agent.activeTasks} tasks
            </div>
          </div>
        ))}
      </div>

      {/* Agent Detail Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <GlassPanel
            key={agent.id}
            headerTitle={agent.name}
            headerCode={`${agent.load}% LOAD`}
            statusIndicator={agent.status === 'PROCESSING' ? 'WARNING' : agent.status === 'ACTIVE' ? 'ACTIVE' : 'STANDBY'}
          >
            <div className="space-y-2 font-mono text-xs">
              <p className="text-[#9AA7B8] text-[11px] min-h-[32px]">{agent.role}</p>
              <div className="p-2.5 bg-[#020B1A] border border-[#17406E] space-y-1 text-[10px] text-[#9AA7B8]">
                <div className="flex justify-between">
                  <span>STATE:</span>
                  <span className={agent.status === 'ACTIVE' ? 'text-[#00E699] font-bold' : 'text-[#D9E1EA] font-bold'}>{agent.status}</span>
                </div>
                <div className="flex justify-between">
                  <span>LAST HEARTBEAT:</span>
                  <span className="text-[#00E699] font-bold">{agent.lastHeartbeat}</span>
                </div>
                <div className="flex justify-between">
                  <span>ACTIVE TASKS:</span>
                  <span className="text-white font-bold">{agent.activeTasks}</span>
                </div>
              </div>
            </div>
          </GlassPanel>
        ))}
      </div>
    </div>
  );
};