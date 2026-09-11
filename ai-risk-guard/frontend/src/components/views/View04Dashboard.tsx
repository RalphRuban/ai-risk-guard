import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { RuggedFrame } from '../common/RuggedFrame';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { DashboardData, AttentionFinding, getDashboardData } from '../../api/client';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  RefreshCw, 
  Cpu, 
  GitPullRequest, 
  ArrowRight, 
  TrendingUp, 
  Terminal, 
  Box, 
  Activity, 
  Lock, 
  Zap, 
  ExternalLink,
  Layers,
  Filter
} from 'lucide-react';

interface View04DashboardProps {
  onNavigate: (view: ViewId) => void;
}

interface InterventionRow {
  id: number;
  class: string;
  cve: string;
  file: string;
  line: number;
  severity: string;
  decision: string;
  time: string;
  status: string;
}

export const View04Dashboard: React.FC<View04DashboardProps> = ({ onNavigate }) => {
  const [refreshing, setRefreshing] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM'>('ALL');
  const [selectedIntervention, setSelectedIntervention] = useState<number | null>(0);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      setDashboard(await getDashboardData());
    } catch (e) {
      setError('Unable to load dashboard telemetry from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboard();
    setRefreshing(false);
  };

  const interventions: InterventionRow[] = (dashboard?.attention || []).map((a: AttentionFinding, i: number) => ({
    id: i + 1,
    class: a.vuln_type || 'UNKNOWN',
    cve: a.repo_full_name ? `${a.repo_full_name} #${a.pr_number}` : `PR #${a.pr_number}`,
    file: a.file_path || 'unknown',
    line: 0,
    severity: a.severity,
    decision: `Risk ${a.risk_score.toFixed(2)} // patch candidate`,
    time: a.scan_id ? `scan ${a.scan_id}` : '—',
    status: a.risk_score >= 7 ? 'CRITICAL' : 'MONITORED',
  }));

  const filteredInterventions = interventions.filter(item => {
    if (severityFilter === 'ALL') return true;
    return item.severity === severityFilter;
  });

  const total = (dashboard?.risk_levels?.LOW ?? 0) + (dashboard?.risk_levels?.MEDIUM ?? 0) + (dashboard?.risk_levels?.HIGH ?? 0);
  const low = dashboard?.risk_levels?.LOW ?? 0;
  const medium = dashboard?.risk_levels?.MEDIUM ?? 0;
  const high = dashboard?.risk_levels?.HIGH ?? 0;
  const lowPct = total ? ((low / total) * 100).toFixed(1) : '0.0';
  const mediumPct = total ? ((medium / total) * 100).toFixed(1) : '0.0';
  const highPct = total ? ((high / total) * 100).toFixed(1) : '0.0';
  const remediationRate = dashboard?.remediation_rate ?? 0;
  const score = dashboard?.avg_risk_score ?? 0;

  return (
    <div className="py-6 px-4 sm:px-8 xl:px-12 w-full max-w-[1780px] mx-auto space-y-8">
      {/* Master Rugged Chassis Enclosure */}
      <RuggedFrame
        unitCode="UNIT-04 // SEC-OPS COMMAND"
        title="ENTERPRISE SECURITY POSTURE DASHBOARD"
        statusBadge="DEFCON 2 // AIRGAP VERIFIED"
        statusColor="red"
        headerAction={
          <div className="flex items-center space-x-3">
            <CyberButton
              variant="secondary"
              size="sm"
              loading={refreshing}
              icon={<RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />}
              onClick={handleRefresh}
            >
              SYNC TELEMETRY
            </CyberButton>
            <CyberButton
              variant="primary"
              size="sm"
              icon={<Shield className="w-3.5 h-3.5" />}
              onClick={() => onNavigate('scanner')}
            >
              RUN AST SCAN
            </CyberButton>
          </div>
        }
      >
        {/* Top Control & HUD Sub-bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 mb-6 border-b border-[#184384]/60 font-mono text-xs">
          <div className="space-y-1">
<div className="flex items-center space-x-2 text-[11px] text-[#CBD5E1]">
            <span className="w-2 h-2 rounded-full bg-[#FF2A4B] animate-ping" />
            <span className="font-semibold tracking-widest text-[#F8FAFC]">ACTIVE SURVEILLANCE MESH: {(dashboard?.repos?.length ?? 0)} REPOSITORIES MONITORED</span>
          </div>
            <p className="text-[11px] text-[#94A3B8]">
              Continuous AST Abstract Syntax Analysis & Airgapped Container Sandbox Isolation Engine
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-[10px]">
            <div className="px-3 py-1.5 rounded bg-[#030C22] border border-[#184384] flex items-center space-x-2">
              <span className="text-[#94A3B8]">CLOCK:</span>
              <span className="text-[#E2E8F0] font-bold">2026-09-06 22:28 UTC</span>
            </div>
            <div className="px-3 py-1.5 rounded bg-[#030C22] border border-[#184384] flex items-center space-x-2">
              <span className="text-[#94A3B8]">GATE STATUS:</span>
              <span className={high > 0 ? 'text-[#FF2A4B] font-bold' : 'text-[#00E699] font-bold'}>
                {loading ? 'LOADING...' : `${dashboard?.week_summary?.open_now ?? 0} OPEN FINDINGS / ${dashboard?.week_summary?.new_7d ?? 0} NEW (7D)`}
              </span>
            </div>
          </div>
        </div>

        {/* 4 High-End Rugged Telemetry KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
          {/* KPI 1: Monitored Repos */}
          <div className="relative p-5 rounded-lg bg-gradient-to-br from-[#0B2556]/80 via-[#061533]/90 to-[#020716]/98 border-2 border-[#184384] shadow-[0_12px_36px_rgba(2,7,22,0.8)] group hover:border-[#FF2A4B]/60 transition-all">
            <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#CBD5E1] shadow-[0_0_6px_#E2E8F0]" />
            <div className="flex items-center justify-between text-[#94A3B8] text-[11px] font-mono mb-2">
              <span className="tracking-wider uppercase font-semibold">PROTECTED REPOS</span>
              <GitPullRequest className="w-4 h-4 text-[#CBD5E1]" />
            </div>
            <div className="font-headline font-black text-3xl xl:text-4xl text-[#F8FAFC] tracking-wide mb-2">
              {dashboard?.repos?.length ?? 0}
            </div>
            <div className="flex items-center justify-between text-[10px] font-mono border-t border-[#184384]/50 pt-2 text-[#CBD5E1]">
              <span className="flex items-center space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#FF2A4B] animate-pulse" />
                <span>{dashboard?.week_summary?.open_now ?? 0} OPEN FINDINGS</span>
              </span>
              <span className="text-[#F8FAFC] font-bold">{dashboard?.week_summary?.scans_7d ?? 0} SCANS/7D</span>
            </div>
          </div>

          {/* KPI 2: Cumulative AST Scans */}
          <div className="relative p-5 rounded-lg bg-gradient-to-br from-[#0B2556]/80 via-[#061533]/90 to-[#020716]/98 border-2 border-[#184384] shadow-[0_12px_36px_rgba(2,7,22,0.8)] group hover:border-[#FF2A4B]/60 transition-all">
            <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#CBD5E1] shadow-[0_0_6px_#E2E8F0]" />
            <div className="flex items-center justify-between text-[#94A3B8] text-[11px] font-mono mb-2">
              <span className="tracking-wider uppercase font-semibold">CUMULATIVE AST SCANS</span>
              <Terminal className="w-4 h-4 text-[#FF2A4B]" />
            </div>
            <div className="font-headline font-black text-3xl xl:text-4xl text-[#FF2A4B] tracking-wide mb-2">
              {dashboard?.total_prs ?? 0}
            </div>
            <div className="flex items-center justify-between text-[10px] font-mono border-t border-[#184384]/50 pt-2 text-[#CBD5E1]">
              <span>AVG RISK SCORE: {score.toFixed(2)}</span>
              <span className="text-[#E2E8F0] font-bold">{(dashboard?.cache_hit_rate ?? 0).toFixed(0)}% CACHE HIT</span>
            </div>
          </div>

          {/* KPI 3: Mitigated Vulnerabilities */}
          <div className="relative p-5 rounded-lg bg-gradient-to-br from-[#0B2556]/80 via-[#061533]/90 to-[#020716]/98 border-2 border-[#184384] shadow-[0_12px_36px_rgba(2,7,22,0.8)] group hover:border-[#FF2A4B]/60 transition-all">
            <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#FF2A4B] shadow-[0_0_6px_#FF2A4B]" />
            <div className="flex items-center justify-between text-[#94A3B8] text-[11px] font-mono mb-2">
              <span className="tracking-wider uppercase font-semibold">VULNERABILITIES MITIGATED</span>
              <Shield className="w-4 h-4 text-[#CBD5E1]" />
            </div>
            <div className="font-headline font-black text-3xl xl:text-4xl text-[#F8FAFC] tracking-wide mb-2">
              {dashboard?.total_vulnerabilities ?? 0}
            </div>
            <div className="flex items-center justify-between text-[10px] font-mono border-t border-[#184384]/50 pt-2 text-[#CBD5E1]">
              <span className="text-[#00E699] font-bold">{(remediationRate * 100).toFixed(0)}% REMEDIATED</span>
              <span className="text-[#CBD5E1]">{high} OPEN HIGH</span>
            </div>
          </div>

          {/* KPI 4: Autonomous Pass Rate */}
          <div className="relative p-5 rounded-lg bg-gradient-to-br from-[#0B2556]/80 via-[#061533]/90 to-[#020716]/98 border-2 border-[#184384] shadow-[0_12px_36px_rgba(2,7,22,0.8)] group hover:border-[#CBD5E1]/60 transition-all">
            <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#CBD5E1] shadow-[0_0_6px_#E2E8F0]" />
            <div className="flex items-center justify-between text-[#94A3B8] text-[11px] font-mono mb-2">
              <span className="tracking-wider uppercase font-semibold">SANDBOX VALIDATION PASS</span>
              <Box className="w-4 h-4 text-[#CBD5E1]" />
            </div>
            <div className="font-headline font-black text-3xl xl:text-4xl text-[#E2E8F0] tracking-wide mb-2">
              {(remediationRate * 100).toFixed(1)}%
            </div>
            <div className="flex items-center justify-between text-[10px] font-mono border-t border-[#184384]/50 pt-2 text-[#CBD5E1]">
              <span>REMEDIATION RATE</span>
              <span className="text-[#FF2A4B] font-bold">{low} LOW / {medium} MEDIUM</span>
            </div>
          </div>
        </div>

        {/* Mid Section: Real-Time Risk Distribution & 6-Agent Dispatch Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
          {/* Left: Risk Severity Distribution (5 cols) */}
          <div className="lg:col-span-5 flex flex-col">
            <GlassPanel
              headerTitle="RISK SEVERITY SPECTRUM"
              headerCode="AST_AGGREGATION"
              statusIndicator="ALERT"
              className="h-full flex flex-col justify-between"
            >
              <div className="space-y-6">
                {/* Visual SVG Doughnut in Navy, Red, Silver */}
                <div className="flex items-center justify-center py-2">
                  <div className="relative w-44 h-44 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                      {/* Base Background Track */}
                      <circle cx="88" cy="88" r="68" stroke="#081D45" strokeWidth="16" fill="none" />
                      {/* Medium/Low Track (Navy/Silver) */}
                      <circle cx="88" cy="88" r="68" stroke="#1E64D4" strokeWidth="16" fill="none" strokeDasharray="427" strokeDashoffset="130" strokeLinecap="round" />
                      {/* High Track (Titanium Silver) */}
                      <circle cx="88" cy="88" r="68" stroke="#CBD5E1" strokeWidth="16" fill="none" strokeDasharray="427" strokeDashoffset="280" strokeLinecap="round" />
                      {/* Critical Track (Threat Red) */}
                      <circle cx="88" cy="88" r="68" stroke="#FF2A4B" strokeWidth="16" fill="none" strokeDasharray="427" strokeDashoffset="375" strokeLinecap="round" />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center font-mono text-center">
                      <span className="font-headline font-bold text-2xl text-[#F8FAFC]">{total}</span>
                      <span className="text-[9px] text-[#94A3B8] tracking-widest uppercase">SCANNED SINK NODES</span>
                    </div>
                  </div>
                </div>

                {/* Risk Distribution Breakdown Bars */}
                <div className="space-y-2.5 font-mono text-xs">
                  <div className="flex items-center justify-between p-3 rounded bg-[#020716] border border-[#184384] hover:border-[#FF2A4B]/60 transition-colors">
                    <span className="flex items-center space-x-2.5">
                      <span className="w-3 h-3 rounded-sm bg-[#FF2A4B] shadow-[0_0_8px_#FF2A4B]" />
                      <span className="text-[#F8FAFC] font-medium">HIGH RISK (severity=HIGH)</span>
                    </span>
                    <span className="text-[#FF2A4B] font-bold">{high} ({highPct}%)</span>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded bg-[#020716] border border-[#184384] hover:border-[#1E64D4]/60 transition-colors">
                    <span className="flex items-center space-x-2.5">
                      <span className="w-3 h-3 rounded-sm bg-[#1E64D4] shadow-[0_0_8px_#1E64D4]" />
                      <span className="text-[#CBD5E1] font-medium">MEDIUM</span>
                    </span>
                    <span className="text-[#CBD5E1] font-bold">{medium} ({mediumPct}%)</span>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded bg-[#020716] border border-[#184384] hover:border-[#CBD5E1]/60 transition-colors">
                    <span className="flex items-center space-x-2.5">
                      <span className="w-3 h-3 rounded-sm bg-[#CBD5E1] shadow-[0_0_8px_rgba(203,213,225,0.6)]" />
                      <span className="text-[#E2E8F0] font-medium">LOW</span>
                    </span>
                    <span className="text-[#CBD5E1] font-bold">{low} ({lowPct}%)</span>
                  </div>
                </div>
              </div>
            </GlassPanel>
          </div>

          {/* Right: 6-Agent Autonomous Mesh Pulse (7 cols) */}
          <div className="lg:col-span-7 flex flex-col">
            <GlassPanel
              headerTitle="AUTONOMOUS AGENT MESH DISPATCH STATUS"
              headerCode="6_NODES_SYNCHRONIZED"
              statusIndicator="ACTIVE"
              className="h-full flex flex-col justify-between"
            >
              <div className="space-y-4 font-mono text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {[
                    { name: 'OrchestratorAgent', role: 'Workflow Mesh', load: '38%', status: 'CONSENSUS', tagColor: 'navy' },
                    { name: 'ASTScannerAgent', role: 'Syntax Trees', load: '74%', status: 'PARSING', tagColor: 'red' },
                    { name: 'PatchSynthesizer', role: 'NodeTransformer', load: '52%', status: 'SYNTHESIZING', tagColor: 'silver' },
                    { name: 'SandboxValidator', role: 'Docker gVisor', load: '29%', status: 'AIRGAP IDLE', tagColor: 'navy' },
                    { name: 'RiskEngineAgent', role: '7-Factor Context', load: '41%', status: 'CALCULATING', tagColor: 'red' },
                    { name: 'PolicyGatekeeper', role: 'PR Clearance', load: '45%', status: 'GATE LOCKED', tagColor: 'silver' },
                  ].map((ag) => (
                    <div 
                      key={ag.name} 
                      className="p-3.5 rounded bg-[#020716] border border-[#184384] hover:border-[#CBD5E1]/60 transition-all space-y-2 group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[#F8FAFC] font-semibold text-[11px] group-hover:text-white transition-colors">
                          {ag.name}
                        </span>
                        <span className={`w-2 h-2 rounded-full ${ag.tagColor === 'red' ? 'bg-[#FF2A4B] animate-ping' : 'bg-[#CBD5E1]'}`} />
                      </div>
                      <div className="text-[10px] text-[#94A3B8]">{ag.role}</div>
                      
                      {/* Mini Load Bar */}
                      <div className="space-y-1">
                        <div className="flex justify-between text-[10px]">
                          <span className="text-[#94A3B8]">UTILIZATION:</span>
                          <span className={ag.tagColor === 'red' ? 'text-[#FF2A4B] font-bold' : 'text-[#E2E8F0] font-bold'}>{ag.load}</span>
                        </div>
                        <div className="w-full h-1.5 bg-[#081D45] rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${ag.tagColor === 'red' ? 'bg-[#FF2A4B]' : 'bg-[#CBD5E1]'}`} 
                            style={{ width: ag.load }}
                          />
                        </div>
                      </div>

                      <span className="text-[9px] text-[#CBD5E1] block pt-1 border-t border-[#184384]/40 font-bold">
                        {ag.status}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Tactical Airgap Consensus Banner */}
                <div className="p-3.5 rounded bg-[#030C22] border border-[#184384] flex items-center justify-between text-[11px] text-[#94A3B8]">
                  <div className="flex items-center space-x-2">
                    <Shield className="w-4 h-4 text-[#FF2A4B]" />
                    <span className="text-[#F8FAFC] font-semibold">MULTI-AGENT AIRGAP PROTOCOL:</span>
                    <span>100% of candidate AST patches undergo 0.5 CPU Docker sandbox verification before PR creation.</span>
                  </div>
                  <CyberButton
                    variant="outline"
                    size="sm"
                    onClick={() => onNavigate('agents')}
                    icon={<ExternalLink className="w-3 h-3 text-[#CBD5E1]" />}
                  >
                    INSPECT MESH
                  </CyberButton>
                </div>
              </div>
            </GlassPanel>
          </div>
        </div>

        {/* Bottom Section: Full-Width Audit Log Stream with Interactive Severity Filter */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 font-mono text-xs">
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-[#CBD5E1]" />
              <span className="text-[#F8FAFC] font-semibold text-sm">AUTONOMOUS INTERVENTIONS & AST REMEDIATION STREAM</span>
            </div>

            {/* Severity Filter Buttons */}
            <div className="flex items-center space-x-2">
              <span className="text-[#94A3B8] text-[11px]">FILTER:</span>
              {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'] as const).map(sev => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-3 py-1 rounded border text-[10px] transition-all ${
                    severityFilter === sev
                      ? sev === 'CRITICAL' 
                        ? 'bg-[#FF2A4B] border-[#FF2A4B] text-white font-bold shadow-[0_0_10px_#FF2A4B]' 
                        : 'bg-[#CBD5E1] border-[#CBD5E1] text-[#020716] font-bold shadow-[0_0_10px_rgba(203,213,225,0.6)]'
                      : 'bg-[#020716] border-[#184384] text-[#94A3B8] hover:text-[#E2E8F0]'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {/* High-End Tactical Audit Table */}
          <div className="rounded-lg border-2 border-[#184384] overflow-hidden bg-[#020716] shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead className="bg-[#030C22] border-b-2 border-[#184384] text-[#94A3B8] text-[10px] tracking-wider uppercase">
                  <tr>
                    <th className="py-3 px-4">CVE / CWE CLASS</th>
                    <th className="py-3 px-4">VULNERABLE SINK FILE</th>
                    <th className="py-3 px-4">SEVERITY</th>
                    <th className="py-3 px-4">AUTONOMOUS AST REMEDIATION DECISION</th>
                    <th className="py-3 px-4">CONTAINER TIME</th>
                    <th className="py-3 px-4">STATUS</th>
                    <th className="py-3 px-4 text-right">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#184384]/40 text-[#CBD5E1]">
                  {filteredInterventions.map((item, idx) => (
                    <tr 
                      key={item.id} 
                      onClick={() => setSelectedIntervention(idx)}
                      className={`hover:bg-[#061533] cursor-pointer transition-colors ${
                        selectedIntervention === idx ? 'bg-[#0B2556]/60' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-[#F8FAFC]">{item.class}</div>
                        <div className="text-[10px] text-[#94A3B8]">{item.cve}</div>
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        <span className="text-[#CBD5E1] font-medium">{item.file}</span>
                        {item.line > 0 && <span className="text-[#FF2A4B] font-bold">:{item.line}</span>}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 text-[9px] font-bold rounded border ${
                          item.severity === 'CRITICAL'
                            ? 'bg-[#991B1B]/40 text-[#FF2A4B] border-[#FF2A4B]/80 shadow-[0_0_8px_rgba(255,42,75,0.3)]'
                            : item.severity === 'HIGH'
                            ? 'bg-[#0B2556] text-[#CBD5E1] border-[#CBD5E1]/60'
                            : 'bg-[#081D45] text-[#94A3B8] border-[#184384]'
                        }`}>
                          {item.severity}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[#E2E8F0]">
                        {item.decision}
                      </td>
                      <td className="py-3.5 px-4 text-[#94A3B8]">
                        {item.time}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-[#061533] border border-[#CBD5E1]/30 text-[10px] text-[#E2E8F0] font-semibold">
                          <CheckCircle className="w-3 h-3 text-[#FF2A4B]" />
                          <span>{item.status}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onNavigate('patch');
                          }}
                          className="px-3 py-1 bg-[#DC2626] hover:bg-[#B91C1C] text-white border border-[#FF2A4B] text-[10px] font-bold rounded tracking-wider transition-all shadow-[0_0_10px_rgba(255,42,75,0.4)]"
                        >
                          INSPECT DIFF
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </RuggedFrame>
    </div>
  );
};
