import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { ArrowLeft, RefreshCw, GitPullRequest, CheckCircle, XCircle, Shield } from 'lucide-react';
import { Scan, Finding, getScans, getScanFindings, submitFeedback } from '../../api/client';

type Severity = Finding['severity'];

function normalizeSeverity(raw: unknown): Severity {
  const value = String(raw ?? '').toUpperCase();
  return value === 'LOW' || value === 'MEDIUM' || value === 'HIGH' || value === 'CRITICAL'
    ? value
    : 'LOW';
}

function humanize(vulnType: string): string {
  return vulnType.replace(/_/g, ' ').toUpperCase();
}

function formatTime(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
}

function formatDuration(ms?: number): string {
  return typeof ms === 'number' ? `${(ms / 1000).toFixed(1)} s` : '—';
}

function scanStatus(scan: Scan): 'ACTIVE' | 'WARNING' | 'ALERT' {
  const s = String(scan.status || '').toUpperCase();
  if (s.includes('FAIL') || s.includes('ERROR')) return 'ALERT';
  if (s.includes('COMPLET')) return 'ACTIVE';
  return 'WARNING';
}

function latestPerPr(scans: Scan[]): Scan[] {
  const seen = new Set<string>();
  const out: Scan[] = [];
  for (const s of scans) {
    if (typeof s.pr_number === 'number' && s.pr_number > 0) {
      const key = `${s.repo_id}:${s.pr_number}`;
      if (seen.has(key)) continue;
      seen.add(key);
    }
    out.push(s);
  }
  return out;
}

interface FeedbackState {
  status: 'idle' | 'sending' | 'sent' | 'error';
  outcome?: 'ACCEPTED' | 'REJECTED';
}

export const View07Findings: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedScan, setSelectedScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [findingsLoading, setFindingsLoading] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [feedback, setFeedback] = useState<Record<number, FeedbackState>>({});

  const loadScans = async () => {
    setLoading(true);
    setError(null);
    try {
      setScans(await getScans());
    } catch (e) {
      setError('Unable to load scans from the backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openScan = async (scan: Scan) => {
    setSelectedScan(scan);
    setFindingsLoading(true);
    setFindings([]);
    setFilterSeverity('ALL');
    setFeedback({});
    try {
      setFindings(await getScanFindings(scan.id));
    } catch (e) {
      setFindings([]);
    } finally {
      setFindingsLoading(false);
    }
  };

  const closeScan = () => {
    setSelectedScan(null);
    setFindings([]);
    setFeedback({});
  };

  const sendFeedback = async (finding: Finding, outcome: 'ACCEPTED' | 'REJECTED') => {
    setFeedback((prev) => ({ ...prev, [finding.id]: { status: 'sending' } }));
    try {
      await submitFeedback({
        vuln_type: finding.vuln_type,
        outcome,
        repo_id: selectedScan?.repo_id,
        pr_number: selectedScan?.pr_number,
        scan_id: selectedScan?.id,
      });
      setFeedback((prev) => ({ ...prev, [finding.id]: { status: 'sent', outcome } }));
    } catch {
      setFeedback((prev) => ({ ...prev, [finding.id]: { status: 'error' } }));
    }
  };

  const latest = latestPerPr(scans);
  const filteredFindings = findings.filter(
    (f) => filterSeverity === 'ALL' || normalizeSeverity(f.severity) === filterSeverity
  );

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>PER-SCAN RESULTS // LATEST SCAN PER PULL REQUEST</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Vulnerability Findings &amp; Intelligence
          </h1>
        </div>

        <div className="flex items-center space-x-2">
          {!selectedScan && (
            <button
              onClick={() => onNavigate('repositories')}
              className="flex items-center space-x-2 px-3 py-1.5 font-mono text-[11px] border border-[#17406E] text-[#9AA7B8] hover:text-white hover:border-[#D9E1EA]/60 transition-all"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>BACK TO REPOSITORIES</span>
            </button>
          )}
          <CyberButton
            variant="secondary"
            size="sm"
            icon={<RefreshCw className="w-3.5 h-3.5" />}
            loading={loading}
            onClick={loadScans}
          >
            SYNC
          </CyberButton>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-[#7E1120]/20 border border-[#FF1E2D] text-[#FF1E2D] font-mono text-xs">
          {error}
        </div>
      )}

      {loading && scans.length === 0 && (
        <div className="flex items-center justify-center py-16 font-mono text-xs text-[#9AA7B8] animate-pulse">
          LOADING SCAN LEDGER...
        </div>
      )}

      {/* Detail View */}
      {selectedScan ? (
        <div className="space-y-6">
          <div className="flex items-center space-x-3">
            <button
              onClick={closeScan}
              className="flex items-center space-x-2 px-3 py-1.5 font-mono text-[11px] border border-[#17406E] text-[#9AA7B8] hover:text-white hover:border-[#D9E1EA]/60 transition-all"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>ALL SCANS</span>
            </button>
            <button
              onClick={() => onNavigate('repositories')}
              className="flex items-center space-x-2 px-3 py-1.5 font-mono text-[11px] border border-[#17406E] text-[#9AA7B8] hover:text-white hover:border-[#D9E1EA]/60 transition-all"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>BACK TO REPOSITORIES</span>
            </button>
          </div>

          {/* Scan Meta Header */}
          <GlassPanel
            headerTitle={`${selectedScan.repo_full_name || `REPO #${selectedScan.repo_id}`} #${selectedScan.pr_number}`}
            headerCode={selectedScan.branch || 'SCAN DETAIL'}
            statusIndicator="ALERT"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
              <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-1">
                <span className="text-[#9AA7B8] text-[11px]">PULL REQUEST</span>
                <div className="text-white font-bold flex items-center space-x-1.5">
                  <GitPullRequest className="w-4 h-4 text-[#00A8FF]" />
                  <span>#{selectedScan.pr_number}</span>
                </div>
                <span className="text-[#A7B4C4] text-[10px]">{selectedScan.pr_title || '—'}</span>
              </div>

              <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-1">
                <span className="text-[#9AA7B8] text-[11px]">SCAN STATUS</span>
                <span
                  className={`inline-block px-2 py-0.5 text-[10px] font-bold rounded border ${
                    scanStatus(selectedScan) === 'ALERT'
                      ? 'bg-[#FF1E2D]/20 text-[#FF1E2D] border-[#FF1E2D]/60'
                      : scanStatus(selectedScan) === 'WARNING'
                      ? 'bg-[#5BC9FF]/20 text-[#5BC9FF] border-[#5BC9FF]/60'
                      : 'bg-[#00E699]/20 text-[#00E699] border-[#00E699]/60'
                  }`}
                >
                  {String(selectedScan.status || 'UNKNOWN').toUpperCase().replace(/[^A-Z0-9]/g, '_')}
                </span>
                <span className="text-[#A7B4C4] text-[10px]">
                  {selectedScan.validation_status
                    ? `VALIDATION: ${selectedScan.validation_status.toUpperCase()}`
                    : 'VALIDATION: —'}
                </span>
              </div>

              <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-1">
                <span className="text-[#9AA7B8] text-[11px]">VULNERABILITIES</span>
                <div className="font-headline font-bold text-2xl text-[#FF1E2D]">
                  {typeof selectedScan.findings_count === 'number' ? selectedScan.findings_count : '—'}
                </div>
                <span className="text-[#A7B4C4] text-[10px]">
                  FOUND IN THIS SCAN &nbsp;//&nbsp; MAX RISK{' '}
                  {typeof selectedScan.max_risk === 'number' ? selectedScan.max_risk.toFixed(2) : '—'}
                </span>
              </div>

              <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-1">
                <span className="text-[#9AA7B8] text-[11px]">SCANNED</span>
                <div className="text-white font-bold">{formatTime(selectedScan.scanned_at)}</div>
                <span className="text-[#A7B4C4] text-[10px]">
                  DURATION {formatDuration(selectedScan.duration_ms)}
                  &nbsp;//&nbsp; {selectedScan.commit_sha ? selectedScan.commit_sha.slice(0, 7) : 'NO COMMIT'}
                </span>
              </div>
            </div>
          </GlassPanel>

          {findingsLoading && (
            <div className="flex items-center justify-center py-12 font-mono text-xs text-[#9AA7B8] animate-pulse">
              LOADING SCAN FINDINGS...
            </div>
          )}

          {!findingsLoading && findings.length === 0 && (
            <div className="p-10 text-center font-mono">
              <div className="text-xs text-[#9AA7B8] mb-2">NO FINDINGS DETECTED IN THIS SCAN</div>
              <p className="text-[11px] text-[#00E699]">The patch passed static analysis clean.</p>
            </div>
          )}

          {!findingsLoading && findings.length > 0 && (
            <>
              {/* Severity Filter Bar */}
              <div className="flex items-center space-x-2 border-b border-[#17406E]/50 pb-3 font-mono text-xs">
                <span className="text-[#9AA7B8] text-[11px]">FILTER:</span>
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setFilterSeverity(sev)}
                    className={`px-3 py-1 border transition-all text-[11px] ${
                      filterSeverity === sev
                        ? 'bg-[#007BFF]/30 border-[#00A8FF] text-[#5BC9FF]'
                        : 'bg-[#050B16] border-[#17406E] text-[#9AA7B8] hover:text-white'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
                <span className="ml-auto text-[#9AA7B8] text-[11px]">
                  {filteredFindings.length} OF {findings.length} FINDINGS
                </span>
              </div>

              {/* Findings Cards */}
              <div className="space-y-4">
                {filteredFindings.map((finding) => {
                  const sev = normalizeSeverity(finding.severity);
                  const fb = feedback[finding.id];
                  return (
                    <GlassPanel
                      key={finding.id}
                      headerTitle={`${humanize(finding.vuln_type)} @${finding.file_path || 'unknown'}:${finding.line_number || '?'}`}
                      headerCode={String(finding.id)}
                      statusIndicator={sev === 'CRITICAL' || sev === 'HIGH' ? 'ALERT' : 'WARNING'}
                      accentColor={sev === 'CRITICAL' || sev === 'HIGH' ? '#FF1E2D' : '#00A8FF'}
                    >
                      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center font-mono text-xs">
                        <div className="lg:col-span-8 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`px-2 py-0.5 text-[9px] font-bold rounded border ${
                                sev === 'CRITICAL'
                                  ? 'bg-[#7E1120]/40 text-[#FF1E2D] border-[#FF1E2D]/80'
                                  : sev === 'HIGH'
                                  ? 'bg-[#7E1120]/20 text-[#FF1E2D] border-[#FF1E2D]/50'
                                  : sev === 'MEDIUM'
                                  ? 'bg-[#0B2A5E] text-[#5BC9FF] border-[#5BC9FF]/50'
                                  : 'bg-[#0B2A5E] text-[#9AA7B8] border-[#17406E]'
                              }`}
                            >
                              {sev}
                            </span>
                            <span className="text-[#A7B4C4]">
                              FILE: <span className="text-white">{finding.file_path}:{finding.line_number}</span>
                            </span>
                            <span className="text-[#A7B4C4]">STATUS:</span>
                            <span className="text-[#00E699]">{String(finding.status || 'open').toUpperCase()}</span>
                            <span className="ml-auto text-[#9AA7B8]">{formatTime(finding.created_at)}</span>
                          </div>
                        </div>

                        <div className="lg:col-span-4 p-3 bg-[#050B16] border border-[#17406E] space-y-2 text-[11px] text-[#9AA7B8]">
                          <div className="flex justify-between items-center">
                            <span>RISK SCORE:</span>
                            <span className="text-[#FF1E2D] font-bold">
                              {typeof finding.risk_score === 'number' ? finding.risk_score.toFixed(2) : '—'} / 10.0
                            </span>
                          </div>
                          <div className="flex items-center justify-between gap-2 pt-1">
                            <span className="text-[#9AA7B8]">OPERATOR FEEDBACK:</span>
                            <div className="flex items-center space-x-2">
                              <button
                                disabled={fb?.status === 'sending'}
                                onClick={() => sendFeedback(finding, 'ACCEPTED')}
                                className={`flex items-center space-x-1 px-2 py-1 text-[10px] font-bold rounded border transition-all ${
                                  fb?.outcome === 'ACCEPTED'
                                    ? 'bg-[#00E699]/20 border-[#00E699] text-[#00E699]'
                                    : 'bg-[#020B1A] border-[#00E699]/60 text-[#00E699] hover:bg-[#00E699]/10'
                                }`}
                              >
                                <CheckCircle className="w-3 h-3" />
                                <span>ACCEPT</span>
                              </button>
                              <button
                                disabled={fb?.status === 'sending'}
                                onClick={() => sendFeedback(finding, 'REJECTED')}
                                className={`flex items-center space-x-1 px-2 py-1 text-[10px] font-bold rounded border transition-all ${
                                  fb?.outcome === 'REJECTED'
                                    ? 'bg-[#FF1E2D]/20 border-[#FF1E2D] text-[#FF1E2D]'
                                    : 'bg-[#020B1A] border-[#FF1E2D]/60 text-[#FF1E2D] hover:bg-[#FF1E2D]/10'
                                }`}
                              >
                                <XCircle className="w-3 h-3" />
                                <span>REJECT</span>
                              </button>
                            </div>
                          </div>
                          {fb?.status === 'sent' && (
                            <div className="text-[10px] text-[#00E699]">
                              FEEDBACK RECORDED // {fb.outcome === 'ACCEPTED' ? 'PATCH ACCEPTED' : 'PATCH REJECTED'}
                            </div>
                          )}
                          {fb?.status === 'error' && (
                            <div className="flex items-center space-x-1 text-[10px] text-[#FF1E2D]">
                              <Shield className="w-3 h-3" />
                              <span>FEEDBACK NOT RECORDED — RATE LIMIT/ERROR. RETRY IN A MOMENT.</span>
                            </div>
                          )}
                          {fb?.status === 'sending' && (
                            <div className="text-[10px] text-[#9AA7B8] animate-pulse">RECORDING FEEDBACK...</div>
                          )}
                        </div>
                      </div>
                    </GlassPanel>
                  );
                })}
              </div>
            </>
          )}
        </div>
      ) : (
        /* List View — Latest Scan per PR */
        <>
          <div className="font-mono text-[10px] text-[#9AA7B8] border-b border-[#17406E]/50 pb-3">
            DISPLAYING LATEST SCAN REVISION PER PULL REQUEST
            <span className="text-[#5BC9FF]"> // {latest.length} SCAN{latest.length === 1 ? '' : 'S'}</span>
          </div>

          {!loading && scans.length === 0 && (
            <div className="p-10 text-center font-mono">
              <div className="text-xs text-[#9AA7B8] mb-2">NO SCANS RECORDED YET</div>
              <p className="text-[11px] text-[#9AA7B8]">
                Scans appear here once GitHub delivers pull_request payloads to the configured webhook.
              </p>
            </div>
          )}

          <div className="space-y-4">
            {latest.map((scan) => {
              const count = typeof scan.findings_count === 'number' ? scan.findings_count : 0;
              const status = scanStatus(scan);
              const isAlert = count > 0;
              return (
                <GlassPanel
                  key={scan.id}
                  headerTitle={`${scan.repo_full_name || `REPO #${scan.repo_id}`} #${scan.pr_number}`}
                  headerCode={scan.branch || 'LATEST SCAN'}
                  statusIndicator={isAlert ? 'ALERT' : status === 'WARNING' ? 'WARNING' : 'ACTIVE'}
                  accentColor={isAlert ? '#FF1E2D' : '#00A8FF'}
                  onClick={() => openScan(scan)}
                  className="cursor-pointer"
                >
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center font-mono text-xs">
                    <div className="lg:col-span-7 space-y-2">
                      <div className="text-[12px] text-[#EAF1F8] font-semibold flex items-center space-x-2">
                        <GitPullRequest className="w-4 h-4 text-[#00A8FF]" />
                        <span>{scan.pr_title || 'Untitled pull request'}</span>
                      </div>
                      <div className="font-headline font-black text-xl text-[#FF1E2D]">
                        FOUND {count} VULNERABILIT{count === 1 ? 'Y' : 'IES'} IN THIS SCAN
                      </div>
                      <div className="text-[10px] text-[#9AA7B8]">
                        SCANNED: {formatTime(scan.scanned_at)}
                        {typeof scan.duration_ms === 'number' && ` // DURATION ${formatDuration(scan.duration_ms)}`}
                        {typeof scan.max_risk === 'number' && ` // MAX RISK ${scan.max_risk.toFixed(2)}`}
                      </div>
                    </div>

                    <div className="lg:col-span-5 flex flex-col items-start lg:items-end space-y-3">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
                          status === 'ALERT'
                            ? 'bg-[#7E1120]/40 text-[#FF1E2D] border-[#FF1E2D]'
                            : status === 'WARNING'
                            ? 'bg-[#5BC9FF]/20 text-[#5BC9FF] border-[#5BC9FF]'
                            : 'bg-[#00E699]/20 text-[#00E699] border-[#00E699]'
                        }`}
                      >
                        {String(scan.status || 'UNKNOWN').toUpperCase().replace(/[^A-Z0-9]/g, '_')}
                      </span>
                      <CyberButton
                        variant={isAlert ? 'threat' : 'secondary'}
                        size="sm"
                        onClick={(e: React.MouseEvent) => {
                          e.stopPropagation();
                          openScan(scan);
                        }}
                      >
                        VIEW SCAN DETAIL
                      </CyberButton>
                    </div>
                  </div>
                </GlassPanel>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};