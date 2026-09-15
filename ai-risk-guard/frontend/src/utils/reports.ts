import { DashboardData } from '../api/client';

export interface ReportMetric {
  label: string;
  value: string;
}

export interface ReportRow {
  severity: string;
  label: string;
  detail: string;
  score: number;
}

export interface AuditReport {
  id: string;
  code: string;
  title: string;
  category: string;
  generatedAt: string;
  grade: string;
  gradeScore: number;
  compliance: number;
  mitigations: number;
  description: string;
  metrics: ReportMetric[];
  rows: ReportRow[];
  hash: string;
  payload: Record<string, unknown>;
}

function toNum(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function clampPercent(score: number): number {
  return Math.min(100, Math.max(0, Math.round(score)));
}

function gradeFromScore(score: number): string {
  if (score >= 97) return 'A+';
  if (score >= 93) return 'A';
  if (score >= 90) return 'A-';
  if (score >= 87) return 'B+';
  if (score >= 83) return 'B';
  if (score >= 80) return 'B-';
  if (score >= 77) return 'C+';
  if (score >= 73) return 'C';
  if (score >= 70) return 'C-';
  if (score >= 67) return 'D+';
  if (score >= 63) return 'D';
  if (score >= 60) return 'D-';
  return 'F';
}

function toISOday(iso: string): string {
  return iso.slice(0, 10);
}

function dayKey(iso: string): string {
  return iso.replace(/[-:]/g, '').slice(0, 8);
}

async function sha256Hex(input: string): Promise<string> {
  const bytes = new TextEncoder().encode(input);
  if (typeof crypto !== 'undefined' && typeof crypto.subtle !== 'undefined') {
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  }
  let h = 0xcbf29ce484222325n;
  for (const byte of bytes) {
    h ^= BigInt(byte);
    h = (h * 0x100000001b3n) & 0xffffffffffffffffn;
  }
  return h.toString(16).padStart(16, '0');
}

interface ReportDraft {
  id: string;
  code: string;
  title: string;
  category: string;
  generatedAt: string;
  gradeScore: number;
  mitigations: number;
  description: string;
  metrics: ReportMetric[];
  rows: ReportRow[];
}

function finalize(draft: ReportDraft): Omit<AuditReport, 'hash'> {
  const grade = gradeFromScore(draft.gradeScore);
  const compliance = clampPercent(draft.gradeScore);
  const payload: Record<string, unknown> = {
    id: draft.id,
    code: draft.code,
    title: draft.title,
    category: draft.category,
    generatedAt: draft.generatedAt,
    grade,
    compliance,
    mitigations: draft.mitigations,
    metrics: draft.metrics,
    rows: draft.rows,
  };
  return { ...draft, grade, compliance, payload };
}

function postureReport(data: DashboardData): ReportDraft {
  const high = toNum(data.risk_levels.HIGH);
  const med = toNum(data.risk_levels.MEDIUM);
  const low = toNum(data.risk_levels.LOW);
  const total = high + med + low;
  const avgRisk = toNum(data.avg_risk_score);
  const remediation = toNum(data.remediation_rate);
  const mitigations = (data.performance || []).reduce(
    (acc, p) => acc + toNum(p.accepted_count),
    0,
  );

  let score = 100 - high * 2 - med * 0.4;
  if (avgRisk >= 8) score += 2;
  if (remediation >= 95) score += 1;
  if (remediation > 0 && remediation < 80) score -= 10;
  if (remediation > 0 && remediation < 50) score -= 15;

  const now = new Date().toISOString();
  const attendance = data.attention || [];
  const rows: ReportRow[] = attendance.slice(0, 10).map((a) => ({
    severity: a.severity,
    label: a.repo_full_name ? `${a.repo_full_name} #${a.pr_number || 0}` : `PR #${a.pr_number || 0}`,
    detail: a.vuln_type || 'UNKNOWN',
    score: toNum(a.risk_score),
  }));

  return {
    id: 'posture',
    code: `REP-POSTURE-${dayKey(now)}`,
    title: 'Continuous Posture Attestation',
    category: 'POSTURE',
    generatedAt: now,
    gradeScore: score,
    mitigations,
    description:
      `Live snapshot computed from ${data.total_prs || 0} scanned pull requests across ` +
      `${(data.repos || []).length} tracked repositories. Current open exposure: ${high} high / ` +
      `${med} medium / ${low} low severity findings with a ${remediation}% patch acceptance rate.`,
    metrics: [
      { label: 'PRS SCANNED', value: String(data.total_prs || 0) },
      { label: 'OPEN VULNS', value: String(total) },
      { label: 'HIGH SEV', value: high > 0 ? String(high) : 'CLEAR' },
      { label: 'AVG RISK', value: avgRisk.toFixed(1) },
      { label: 'REMEDIATION', value: `${remediation}%` },
      { label: 'ACCEPTED PATCHES', value: String(mitigations) },
    ],
    rows,
  };
}

function activityReport(data: DashboardData): ReportDraft {
  const week = data.week_summary || { scans_7d: 0, new_7d: 0, open_now: 0 };
  const scans7d = toNum(week.scans_7d);
  const new7d = toNum(week.new_7d);
  const openNow = toNum(week.open_now);
  const remediation = toNum(data.remediation_rate);

  let score = 100 - openNow - (remediation > 0 && remediation < 70 ? 15 : 0);
  if (openNow === 0) score = score > 95 ? 95 : score;
  if (scans7d === 0 && new7d === 0) score -= 5;

  const now = new Date().toISOString();
  const trends = (data.trends || []).slice(0, 7);
  const rows: ReportRow[] = trends.map((t) => ({
    severity: toNum(t.count) > 0 ? 'INFO' : 'LOW',
    label: toISOday(t.day || ''),
    detail: `${toNum(t.count)} scannable PRs`,
    score: toNum(t.count),
  }));

  return {
    id: 'activity',
    code: `REP-ACTIV7D-${dayKey(now)}`,
    title: '7-Day Ingestion & Remediation Activity',
    category: 'ACTIVITY',
    generatedAt: now,
    gradeScore: score,
    mitigations: 0,
    description:
      `Seven-day ingestion window: ${scans7d} pull requests scanned, ${new7d} new findings ` +
      `recorded, and ${openNow} vulnerabilities currently open across all tracked repositories.`,
    metrics: [
      { label: 'PRS SCANNED (7D)', value: String(scans7d) },
      { label: 'NEW FINDINGS (7D)', value: String(new7d) },
      { label: 'OPEN NOW', value: String(openNow) },
      { label: 'REMEDIATION', value: `${remediation}%` },
      { label: 'TREND WINDOW', value: `${rows.length} DAYS` },
    ],
    rows,
  };
}

function threatsReport(data: DashboardData): ReportDraft {
  const attendance = data.attention || [];
  const scores = attendance.map((a) => toNum(a.risk_score));
  const maxRisk = scores.length ? Math.max(...scores) : 0;
  const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const highCount = attendance.filter((a) => a.severity === 'HIGH' || a.severity === 'CRITICAL').length;

  let score = 100 - maxRisk * 8;
  if (highCount > 5) score -= 10;
  if (attendance.length === 0) score = 100;

  const now = new Date().toISOString();
  const rows: ReportRow[] = attendance.slice(0, 10).map((a) => ({
    severity: a.severity,
    label: a.repo_full_name ? `${a.repo_full_name} #${a.pr_number || 0}` : `PR #${a.pr_number || 0}`,
    detail: `${a.vuln_type || 'UNKNOWN'} — ${a.file_path || 'unknown path'}`,
    score: toNum(a.risk_score),
  }));

  return {
    id: 'threats',
    code: `REP-THREAT-${dayKey(now)}`,
    title: 'Top Threats — Attention Register',
    category: 'THREATS',
    generatedAt: now,
    gradeScore: score,
    mitigations: 0,
    description:
      `Highest-risk open findings ranked by contextual risk score. ` +
      `${highCount} high/critical severity items surface across ${attendance.length} attention entries.`,
    metrics: [
      { label: 'ATTENTION ENTRIES', value: String(attendance.length) },
      { label: 'HIGH/CRITICAL', value: String(highCount) },
      { label: 'MAX RISK', value: maxRisk.toFixed(1) },
      { label: 'AVG RISK', value: avg.toFixed(1) },
    ],
    rows,
  };
}

function reposReport(data: DashboardData): ReportDraft {
  const repos = (data.repos || []).map((r) => ({
    full_name: String(r.full_name || 'unknown'),
    high: toNum(r.high_risk),
    med: toNum(r.med_risk),
    low: toNum(r.low_risk),
    last_scan: r.last_scan_at ? String(r.last_scan_at) : '',
  }));
  const totalHigh = repos.reduce((a, r) => a + r.high, 0);
  const totalMed = repos.reduce((a, r) => a + r.med, 0);
  const totalLow = repos.reduce((a, r) => a + r.low, 0);

  let score = 100 - totalHigh * 2 - totalMed * 0.5;
  if (repos.length === 0) score = 50;

  const now = new Date().toISOString();
  const rows: ReportRow[] = repos.map((r) => ({
    severity: r.high > 0 ? 'HIGH' : r.med > 0 ? 'MEDIUM' : 'LOW',
    label: r.full_name,
    detail: `${r.high}H / ${r.med}M / ${r.low}L open ${r.last_scan ? `— last scan ${toISOday(r.last_scan)}` : ''}`,
    score: r.high * 8 + r.med * 5 + r.low * 2,
  }));

  return {
    id: 'repos',
    code: `REP-REPOSTE-${dayKey(now)}`,
    title: 'Repository Posture Breakdown',
    category: 'COVERAGE',
    generatedAt: now,
    gradeScore: score,
    mitigations: 0,
    description:
      `Per-repository open finding ledger across ${repos.length} repositories. ` +
      `Cumulative exposure: ${totalHigh} high, ${totalMed} medium, ${totalLow} low.`,
    metrics: [
      { label: 'REPOSITORIES', value: String(repos.length) },
      { label: 'OPEN HIGH', value: String(totalHigh) },
      { label: 'OPEN MEDIUM', value: String(totalMed) },
      { label: 'OPEN LOW', value: String(totalLow) },
    ],
    rows,
  };
}

export async function buildReports(data: DashboardData): Promise<AuditReport[]> {
  const drafts = [postureReport(data), activityReport(data), threatsReport(data), reposReport(data)];
  const reports: AuditReport[] = [];
  for (const draft of drafts) {
    const base = finalize(draft);
    const hash = await sha256Hex(JSON.stringify(base.payload));
    reports.push({ ...base, hash });
  }
  return reports;
}

export function hasScanData(data: DashboardData): boolean {
  return (
    toNum(data.total_prs) > 0 ||
    toNum(data.total_vulnerabilities) > 0 ||
    (data.attention || []).length > 0 ||
    (data.repos || []).length > 0
  );
}

export function statusForScore(score: number): 'ACTIVE' | 'WARNING' | 'ALERT' | 'STANDBY' {
  if (score >= 90) return 'ACTIVE';
  if (score >= 75) return 'WARNING';
  return 'ALERT';
}

export function statusLabelForScore(score: number): string {
  if (score >= 90) return 'CLEAR';
  if (score >= 75) return 'MONITORED';
  return 'ATTENTION';
}