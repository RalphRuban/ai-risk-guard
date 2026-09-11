import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { SecurityAgent, ViewId } from '../../types';
import { Cpu, Network, Activity, ArrowRight, Zap, Shield } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';

const AGENTS: SecurityAgent[] = [
  { id: 'orch', name: 'OrchestrationAgent', role: 'Global state consensus & thread convergence dispatcher', status: 'ACTIVE', load: 38, lastHeartbeat: '0.02s ago', activeTasks: 4, coordinates: { x: 50, y: 50 } },
  { id: 'mgr', name: 'ManagerAgent', role: 'Workflow routing & worker task allocation pipeline', status: 'ACTIVE', load: 45, lastHeartbeat: '0.05s ago', activeTasks: 6, coordinates: { x: 20, y: 22 } },
  { id: 'scan', name: 'ScannerAgent', role: 'AST syntax tree extraction & Shannon entropy scanner', status: 'PROCESSING', load: 74, lastHeartbeat: '0.01s ago', activeTasks: 12, coordinates: { x: 80, y: 22 } },
  { id: 'patch', name: 'PatchAgent', role: 'Deterministic NodeTransformer & Gemini 1.5 patch synthesizer', status: 'ACTIVE', load: 52, lastHeartbeat: '0.04s ago', activeTasks: 3, coordinates: { x: 15, y: 78 } },
  { id: 'val', name: 'ValidatorAgent', role: 'Hardened Docker sandbox supervisor & syscall monitor', status: 'ACTIVE', load: 29, lastHeartbeat: '0.08s ago', activeTasks: 1, coordinates: { x: 50, y: 92 } },
  { id: 'risk', name: 'RiskAgent', role: '7-Factor weighted mathematical contextual risk evaluator', status: 'ACTIVE', load: 41, lastHeartbeat: '0.03s ago', activeTasks: 5, coordinates: { x: 85, y: 78 } },
];

export const StageAgents: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  return (
    <section className="relative py-20 px-4 sm:px-6 border-b border-[#1E3C5C]/40">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Stage Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-[#06101F] border border-[#1E3C5C] font-mono text-[10px] text-[#00CFFF] tracking-widest mb-2">
              <span>SCROLL STAGE 04 // AGENTIC MESH</span>
            </div>
            <h2 className="font-headline text-2xl sm:text-4xl text-white">
              Multi-Agent Autonomous Mesh
            </h2>
            <p className="font-mono text-xs sm:text-sm text-[#8D9AAA] mt-1">
              Six cooperating specialized security agents synchronize over an asynchronous telemetry bus, collapsing intelligence inward to form the shield.
            </p>
          </div>

          <CyberButton
            variant="secondary"
            size="sm"
            onClick={() => onNavigate('agents')}
            icon={<Network className="w-3.5 h-3.5 text-[#00CFFF]" />}
          >
            VIEW AGENT TOPOLOGY (VIEW 13)
          </CyberButton>
        </div>

        {/* Topological Diagram & Agent Nodes */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          {/* Topological SVG Visualizer (7 cols) */}
          <div className="lg:col-span-7 relative h-[400px] sm:h-[460px] bg-[#030914] border border-[#1E3C5C] p-4 flex items-center justify-center overflow-hidden">
            {/* Background Grid & Radar Circle */}
            <div className="absolute inset-0 bg-technical-grid opacity-40" />
            <div className="absolute w-72 h-72 rounded-full border border-[#00CFFF]/20 animate-pulse" />
            <div className="absolute w-96 h-96 rounded-full border border-[#087BFF]/10" />

            {/* SVG Connecting Lines with Traveling Energy Particles */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              {/* Radial connections from Center (Orchestrator) to 5 Satellite Agents */}
              {[
                { x1: '50%', y1: '50%', x2: '20%', y2: '22%' },
                { x1: '50%', y1: '50%', x2: '80%', y2: '22%' },
                { x1: '50%', y1: '50%', x2: '15%', y2: '78%' },
                { x1: '50%', y1: '50%', x2: '50%', y2: '92%' },
                { x1: '50%', y1: '50%', x2: '85%', y2: '78%' },
              ].map((line, idx) => (
                <g key={idx}>
                  <line
                    x1={line.x1}
                    y1={line.y1}
                    x2={line.x2}
                    y2={line.y2}
                    stroke="#00CFFF"
                    strokeWidth="1.5"
                    strokeDasharray="4 8"
                    className="energy-line"
                  />
                  {/* Outer perimeter rings */}
                  <line
                    x1={line.x2}
                    y1={line.y2}
                    x2="50%"
                    y2="50%"
                    stroke="#087BFF"
                    strokeWidth="0.8"
                    opacity="0.3"
                  />
                </g>
              ))}
            </svg>

            {/* Center Node: OrchestrationAgent */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-20">
              <div className="p-3 bg-[#06101F] border-2 border-[#00CFFF] shadow-[0_0_30px_rgba(0,207,255,0.4)] text-center w-40">
                <div className="flex items-center justify-center space-x-1 text-[#00E699] font-mono text-[9px] mb-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00E699] animate-pulse" />
                  <span>CONSENSUS CORE</span>
                </div>
                <div className="font-headline font-bold text-xs text-white">
                  OrchestrationAgent
                </div>
                <div className="font-mono text-[9px] text-[#00CFFF] mt-0.5">
                  LOAD: 38% // SYNC
                </div>
              </div>
            </div>

            {/* 5 Outer Agents */}
            {AGENTS.filter((a) => a.id !== 'orch').map((agent) => (
              <div
                key={agent.id}
                className="absolute z-10 transform -translate-x-1/2 -translate-y-1/2 p-2 bg-[#06101F]/90 border border-[#1E3C5C] hover:border-[#00CFFF] transition-all text-center w-32 shadow-lg"
                style={{ top: `${agent.coordinates.y}%`, left: `${agent.coordinates.x}%` }}
              >
                <div className="font-mono text-[8px] text-[#8D9AAA]">{agent.id.toUpperCase()}_UNIT</div>
                <div className="font-headline font-semibold text-[11px] text-white truncate">
                  {agent.name}
                </div>
                <div className="font-mono text-[9px] text-[#65E7FF]">
                  LOAD: {agent.load}%
                </div>
              </div>
            ))}
          </div>

          {/* Right Agent Card Specs (5 cols) */}
          <div className="lg:col-span-5 space-y-3">
            <div className="font-mono text-[11px] text-[#8D9AAA]">
              LIVE MESH TELEMETRY & INWARD CONVERGENCE
            </div>

            {AGENTS.map((agent) => (
              <div
                key={agent.id}
                className="p-3 bg-[#06101F]/70 border border-[#1E3C5C] flex items-center justify-between font-mono text-xs"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-[#D7DEE7] font-semibold">{agent.name}</span>
                    <span className={`text-[9px] px-1.5 py-0.2 rounded ${agent.status === 'PROCESSING' ? 'bg-[#087BFF]/30 text-[#00CFFF]' : 'bg-[#00E699]/20 text-[#00E699]'}`}>
                      {agent.status}
                    </span>
                  </div>
                  <p className="text-[10px] text-[#8D9AAA] line-clamp-1">{agent.role}</p>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-[#65E7FF] font-bold">{agent.load}% LOAD</div>
                  <div className="text-[10px] text-[#8D9AAA]">{agent.activeTasks} tasks</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
