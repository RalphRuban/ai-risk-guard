import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId, SecurityAgent } from '../../types';
import { Cpu, Network, Activity, Zap, CheckCircle2, Shield, ArrowRight } from 'lucide-react';

const FULL_AGENTS: SecurityAgent[] = [
  { id: 'orch', name: 'OrchestrationAgent', role: 'Global state consensus & thread convergence dispatcher', status: 'ACTIVE', load: 38, lastHeartbeat: '0.02s ago', activeTasks: 4, coordinates: { x: 50, y: 50 } },
  { id: 'mgr', name: 'ManagerAgent', role: 'Workflow routing & worker task allocation pipeline', status: 'ACTIVE', load: 45, lastHeartbeat: '0.05s ago', activeTasks: 6, coordinates: { x: 25, y: 25 } },
  { id: 'scan', name: 'ScannerAgent', role: 'AST syntax tree extraction & Shannon entropy scanner', status: 'PROCESSING', load: 74, lastHeartbeat: '0.01s ago', activeTasks: 12, coordinates: { x: 75, y: 25 } },
  { id: 'patch', name: 'PatchAgent', role: 'Deterministic NodeTransformer & Gemini 1.5 patch synthesizer', status: 'ACTIVE', load: 52, lastHeartbeat: '0.04s ago', activeTasks: 3, coordinates: { x: 18, y: 75 } },
  { id: 'val', name: 'ValidatorAgent', role: 'Hardened Docker sandbox supervisor & syscall monitor', status: 'ACTIVE', load: 29, lastHeartbeat: '0.08s ago', activeTasks: 1, coordinates: { x: 50, y: 88 } },
  { id: 'risk', name: 'RiskAgent', role: '7-Factor weighted mathematical contextual risk evaluator', status: 'ACTIVE', load: 41, lastHeartbeat: '0.03s ago', activeTasks: 5, coordinates: { x: 82, y: 75 } },
];

export const View13Agents: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  return (
    <div className="py-8 px-4 sm:px-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1E3C5C]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00CFFF] tracking-widest mb-1">
            <span>DISTRIBUTED INTELLIGENCE // 6 AUTONOMOUS SUBSYSTEMS</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Multi-Agent Mesh Architecture
          </h1>
        </div>

        <CyberButton
          variant="secondary"
          size="sm"
          onClick={() => onNavigate('reports')}
        >
          SECURITY REPORTS (VIEW 14)
        </CyberButton>
      </div>

      {/* Top Map: Interactive Mesh Canvas */}
      <div className="relative h-[480px] bg-[#030914] border border-[#1E3C5C] overflow-hidden flex items-center justify-center">
        <div className="absolute inset-0 bg-technical-grid opacity-40" />

        {/* Outer and Inner Radar Circles */}
        <div className="absolute w-80 h-80 rounded-full border border-[#00CFFF]/20 animate-pulse" />
        <div className="absolute w-[500px] h-[500px] rounded-full border border-[#087BFF]/10" />

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
                stroke="#00CFFF"
                strokeWidth="1.5"
                strokeDasharray="4 8"
                className="energy-line"
              />
              <circle cx={pos.x} cy={pos.y} r="3" fill="#65E7FF" />
            </g>
          ))}
        </svg>

        {/* Center Node: OrchestrationAgent */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-20">
          <div className="p-4 bg-[#06101F] border-2 border-[#00CFFF] shadow-[0_0_40px_rgba(0,207,255,0.4)] text-center w-48">
            <div className="flex items-center justify-center space-x-1 text-[#00E699] font-mono text-[10px] mb-1">
              <span className="w-2 h-2 rounded-full bg-[#00E699] animate-pulse" />
              <span>CONSENSUS CORE</span>
            </div>
            <div className="font-headline font-bold text-sm text-white">
              OrchestrationAgent
            </div>
            <div className="font-mono text-[10px] text-[#00CFFF] mt-1">
              38% LOAD // 100HZ BUS
            </div>
          </div>
        </div>

        {/* 5 Outer Agent Nodes */}
        {FULL_AGENTS.filter((a) => a.id !== 'orch').map((agent) => (
          <div
            key={agent.id}
            className="absolute z-10 transform -translate-x-1/2 -translate-y-1/2 p-3 bg-[#06101F]/90 border border-[#1E3C5C] hover:border-[#00CFFF] transition-all text-center w-40 shadow-xl"
            style={{ top: `${agent.coordinates.y}%`, left: `${agent.coordinates.x}%` }}
          >
            <div className="font-mono text-[9px] text-[#8D9AAA] tracking-widest">{agent.id.toUpperCase()}</div>
            <div className="font-headline font-semibold text-xs text-white truncate">
              {agent.name}
            </div>
            <div className="font-mono text-[10px] text-[#65E7FF] mt-0.5">
              LOAD: {agent.load}% // {agent.activeTasks} tasks
            </div>
          </div>
        ))}
      </div>

      {/* Agent Detail Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {FULL_AGENTS.map((agent) => (
          <GlassPanel
            key={agent.id}
            headerTitle={agent.name}
            headerCode={`${agent.load}% LOAD`}
            statusIndicator={agent.status === 'PROCESSING' ? 'WARNING' : 'ACTIVE'}
          >
            <div className="space-y-2 font-mono text-xs">
              <p className="text-[#8D9AAA] text-[11px] min-h-[32px]">{agent.role}</p>
              <div className="p-2.5 bg-[#02050B] border border-[#1E3C5C] space-y-1 text-[10px] text-[#8D9AAA]">
                <div className="flex justify-between">
                  <span>LAST HEARTBEAT:</span>
                  <span className="text-[#00E699] font-bold">{agent.lastHeartbeat}</span>
                </div>
                <div className="flex justify-between">
                  <span>QUEUED TASKS:</span>
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
