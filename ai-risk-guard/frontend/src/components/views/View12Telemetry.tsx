import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { Scan, getScans } from '../../api/client';

interface TelemetryRow {
  time: string;
  event: string;
  repo: string;
  status: string;
  latency: string;
}

export const View12Telemetry: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const [telemetryPoints, setTelemetryPoints] = useState<TelemetryRow[]>([]);
  const [metrics, setMetrics] = useState({ scans: 0, medianMs: 0, highRisk: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getScans()
      .then((scans: Scan[]) => {
        const rows: TelemetryRow[] = scans.slice(0, 25).map((s) => ({
          time: s.scanned_at ? String(s.scanned_at).replace('T', ' ').slice(0, 19) : '—',
          event: `SCAN_${String(s.status || 'UNKNOWN').toUpperCase().replace(/[^A-Z0-9]/g, '_')}`,
          repo: String(s.repo_full_name || `repo-${s.repo_id}`),
          status: String(s.status || 'unknown').toUpperCase(),
          latency: s.duration_ms != null ? `${s.duration_ms}ms` : '—',
        }));
        const durations = scans
          .map((s) => (typeof s.duration_ms === 'number' ? s.duration_ms : null))
          .filter((d): d is number => d !== null)
          .sort((a, b) => a - b);
        const medianMs = durations.length ? durations[Math.floor(durations.length / 2)] : 0;
        const highRisk = scans.filter((s) => (typeof s.max_risk === 'number' ? s.max_risk >= 7 : false)).length;
        setMetrics({ scans: scans.length, medianMs, highRisk });
        setTelemetryPoints(rows);
      })
      .catch(() => {
        setTelemetryPoints([]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>TIME-SERIES EVENT BUS // 100HZ TELEMETRY</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Security Telemetry & Event Stream
          </h1>
        </div>

        <CyberButton
          variant="secondary"
          size="sm"
          onClick={() => onNavigate('agents')}
        >
          MULTI-AGENT MESH (VIEW 13)
        </CyberButton>
      </div>

      {/* 3 Telemetry Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <span className="font-mono text-[11px] text-[#9AA7B8]">SCANS RECORDED</span>
          <div className="font-headline font-bold text-2xl text-white">{loading ? '—' : metrics.scans}</div>
          <span className="font-mono text-[10px] text-[#00E699]">Latest 25 shown below</span>
        </div>

        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <span className="font-mono text-[11px] text-[#9AA7B8]">MEDIAN SCAN DURATION</span>
          <div className="font-headline font-bold text-2xl text-[#00A8FF]">{loading ? '—' : `${metrics.medianMs} ms`}</div>
          <span className="font-mono text-[10px] text-[#5BC9FF]">Across all stored scans</span>
        </div>

        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <span className="font-mono text-[11px] text-[#9AA7B8]">HIGH-RISK SCANS (≥ 7.0)</span>
          <div className="font-headline font-bold text-2xl text-[#00E699]">{loading ? '—' : metrics.highRisk}</div>
          <span className="font-mono text-[10px] text-[#00E699]">Risk-engine max_risk threshold</span>
        </div>
      </div>

      {/* Stream Table */}
      <GlassPanel
        headerTitle="LIVE REAL-TIME TELEMETRY STREAM"
        headerCode="SOCKET_BUS_INGEST"
        statusIndicator="ACTIVE"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead className="border-b border-[#17406E] text-[#9AA7B8] text-[10px]">
              <tr>
                <th className="py-2 px-3">TIMESTAMP</th>
                <th className="py-2 px-3">EVENT IDENTIFIER</th>
                <th className="py-2 px-3">REPOSITORY</th>
                <th className="py-2 px-3">STATUS</th>
                <th className="py-2 px-3 text-right">LATENCY</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#17406E]/50 text-[#D9E1EA]">
              {telemetryPoints.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 px-3 text-center text-[#9AA7B8]">
                    {loading ? 'STREAMING TELEMETRY...' : 'NO SCANS RECORDED YET'}
                  </td>
                </tr>
              )}
              {telemetryPoints.map((pt, i) => (
                <tr key={i} className="hover:bg-[#050B16] transition-colors">
                  <td className="py-2.5 px-3 text-[#9AA7B8]">{pt.time}</td>
                  <td className="py-2.5 px-3 font-semibold text-white">{pt.event}</td>
                  <td className="py-2.5 px-3 text-[#00A8FF]">{pt.repo}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-[#00E699]/20 text-[#00E699]">
                      {pt.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right text-[#5BC9FF]">{pt.latency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>
    </div>
  );
};
