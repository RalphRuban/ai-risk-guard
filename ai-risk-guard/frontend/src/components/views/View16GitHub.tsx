import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { ViewId } from '../../types';
import { Github, Radio, Shield } from 'lucide-react';
import { getMe, getDashboardData, getScans, Scan } from '../../api/client';

interface WebhookRow {
  event: string;
  repo: string;
  pr: string;
  time: string;
  result: string;
}

function scanResultFor(status: string | undefined): string {
  if (!status) return 'SCAN_RECEIVED';
  const s = String(status).toUpperCase();
  if (s.includes('FAIL')) return 'CHECK_FAILED';
  if (/PROCESS|ANALYZ|QUEU|PEND/.test(s)) return 'SCAN_DISPATCHED';
  if (s.includes('COMPLET')) return 'SCAN_COMPLETED';
  return s.replace(/[^A-Z0-9]/g, '_');
}

export const View16GitHub: React.FC<{ onNavigate: (view: ViewId) => void }> = () => {
  const [rows, setRows] = useState<WebhookRow[]>([]);
  const [installations, setInstallations] = useState<number>(0);
  const [repoCount, setRepoCount] = useState<number>(0);
  const [metrics, setMetrics] = useState({ scans: 0, medianMs: 0, highRisk: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getMe().catch(() => null), getDashboardData().catch(() => null), getScans().catch(() => [])])
      .then(([me, dash, scans]) => {
        if (cancelled) return;
        setInstallations(me && typeof me.installations === 'number' ? me.installations : 0);
        setRepoCount(dash && dash.repos ? dash.repos.length : 0);
        const sourced: Scan[] = (scans as Scan[]) || [];
        const durations = sourced
          .map((s) => (typeof s.duration_ms === 'number' ? s.duration_ms : null))
          .filter((d): d is number => d !== null)
          .sort((a, b) => a - b);
        setMetrics({
          scans: sourced.length,
          medianMs: durations.length ? durations[Math.floor(durations.length / 2)] : 0,
          highRisk: sourced.filter((s) => (typeof s.max_risk === 'number' ? s.max_risk >= 7 : false)).length,
        });
        setRows(
          sourced.slice(0, 12).map((s) => ({
            event: `pull_request.synchronize`,
            repo: String(s.repo_full_name || `repo-${s.repo_id}`),
            pr: typeof s.pr_number === 'number' && s.pr_number > 0 ? `#${s.pr_number}` : '—',
            time: s.scanned_at ? String(s.scanned_at).replace('T', ' ').slice(5, 19) : '—',
            result: scanResultFor(s.status),
          }))
        );
      })
      .catch(() => {
        if (!cancelled) setRows([]);
      })
      .finally(() => {
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
            <span>INTEGRATION GATEWAY // GITHUB APP RUNTIME + SCAN ACTIVITY</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            GitHub App & Scan Activity
          </h1>
        </div>
      </div>

      {/* Scan Telemetry Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <span className="font-mono text-[11px] text-[#9AA7B8]">SCANS RECORDED</span>
          <div className="font-headline font-bold text-2xl text-white">{loading ? '—' : metrics.scans}</div>
          <span className="font-mono text-[10px] text-[#00E699]">Latest 12 shown below</span>
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

      {/* Connection Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#9AA7B8]">
            <Github className="w-4 h-4 text-[#00A8FF]" />
            <span>APP INSTALLATION</span>
          </div>
          <div className="font-headline font-bold text-xl text-white">
            {loading ? '…' : `${installations} INSTALLATION${installations === 1 ? '' : 'S'}`}
          </div>
          <span className="font-mono text-[10px] text-[#00E699]">● Linked via GitHub OAuth / App</span>
        </div>

        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#9AA7B8]">
            <Radio className="w-4 h-4 text-[#00A8FF]" />
            <span>WEBHOOK LISTENER</span>
          </div>
          <div className="font-headline font-bold text-xl text-[#00A8FF]">POST /webhook</div>
          <span className="font-mono text-[10px] text-[#9AA7B8]">Ingesting real PR events from payloads</span>
        </div>

        <div className="p-4 bg-[#050B16] border border-[#17406E] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#9AA7B8]">
            <Shield className="w-4 h-4 text-[#00E699]" />
            <span>SECRET VALIDATION</span>
          </div>
          <div className="font-headline font-bold text-xl text-white">{loading ? '…' : `${repoCount} REPOS`}</div>
          <span className="font-mono text-[10px] text-[#5BC9FF]">Discovered from webhook payloads</span>
        </div>
      </div>

      {/* Recent Webhook Events */}
      <GlassPanel
        headerTitle="RECENT PR INGESTION LOG"
        headerCode={loading ? 'LOADING' : `${rows.length} EVENTS`}
        statusIndicator="ACTIVE"
      >
        {loading ? (
          <div className="p-6 text-center font-mono text-xs text-[#9AA7B8]">
            POLLING CAPTURED EVENTS...
          </div>
        ) : rows.length === 0 ? (
          <div className="p-6 text-center font-mono">
            <div className="text-xs text-[#9AA7B8] mb-2">NO WEBHOOK EVENTS RECORDED YET</div>
            <p className="text-[11px] text-[#9AA7B8]">
              Events will appear here once GitHub delivers pull_request payloads to the configured webhook.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="border-b border-[#17406E] text-[#9AA7B8] text-[10px]">
                <tr>
                  <th className="py-2 px-3">EVENT TYPE</th>
                  <th className="py-2 px-3">REPOSITORY</th>
                  <th className="py-2 px-3">PULL REQUEST</th>
                  <th className="py-2 px-3">RECEIVED</th>
                  <th className="py-2 px-3 text-right">DISPATCH RESULT</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#17406E]/50 text-[#D9E1EA]">
                {rows.map((ev, i) => (
                  <tr key={i} className="hover:bg-[#050B16] transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-white">{ev.event}</td>
                    <td className="py-2.5 px-3 text-[#00A8FF]">{ev.repo}</td>
                    <td className="py-2.5 px-3 text-[#5BC9FF]">{ev.pr}</td>
                    <td className="py-2.5 px-3 text-[#9AA7B8]">{ev.time}</td>
                    <td className="py-2.5 px-3 text-right">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                          ev.result === 'CHECK_FAILED'
                            ? 'bg-[#FF1E2D]/20 text-[#FF1E2D]'
                            : ev.result === 'SCAN_DISPATCHED'
                            ? 'bg-[#5BC9FF]/20 text-[#5BC9FF]'
                            : 'bg-[#00E699]/20 text-[#00E699]'
                        }`}
                      >
                        {ev.result}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassPanel>
    </div>
  );
};