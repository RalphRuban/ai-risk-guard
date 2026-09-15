import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { ViewId, RiskFactorItem } from '../../types';
import { getDashboardData, getFindings, getPolicy, DashboardData, Finding, PolicyData } from '../../api/client';

const SEVERITY_RANK: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
const SEVERITY_SCORE: Record<string, number> = { CRITICAL: 9.5, HIGH: 8.0, MEDIUM: 5.5, LOW: 3.5 };
const WEIGHTS = [0.25, 0.20, 0.15, 0.10, 0.10, 0.10, 0.10];

function statusForScore(score: number): RiskFactorItem['status'] {
  if (score >= 8) return 'CRITICAL';
  if (score >= 6) return 'ELEVATED';
  if (score >= 4) return 'MODERATE';
  return 'OPTIMAL';
}

interface RiskModel {
  factors: RiskFactorItem[];
  aggregate: number;
  open: number;
  total: number;
  remediation: number | null;
  confidence: number;
  hasData: boolean;
}

function buildRiskModel(dashboard: DashboardData, findings: Finding[], policy: PolicyData): RiskModel {
  const total = findings.length;
  const openFindings = findings.filter((f) => f.status !== 'resolved');
  const open = openFindings.length;
  const resolved = total - open;
  const hasData = total > 0 || (dashboard.repos && dashboard.repos.length > 0);

  const maxRank = findings.reduce((acc, f) => Math.max(acc, SEVERITY_RANK[f.severity] || 0), 0);
  const severestLabel = (Object.keys(SEVERITY_RANK) as Array<keyof typeof SEVERITY_RANK>).find(
    (k) => SEVERITY_RANK[k] === maxRank
  );
  const severityScore = findings.length
    ? SEVERITY_SCORE[severestLabel || 'LOW'] || 3.5
    : typeof dashboard.avg_risk_score === 'number'
    ? dashboard.avg_risk_score
    : 3.0;

  const byType: Record<string, number> = {};
  findings.forEach((f) => {
    byType[f.vuln_type] = (byType[f.vuln_type] || 0) + 1;
  });
  const typeEntries = Object.entries(byType).sort((a, b) => b[1] - a[1]);
  const topType = typeEntries[0] as [string, number] | undefined;
  const typeScore = topType ? Math.min(10, 2 + (topType[1] / Math.max(1, total)) * 8) : 1.5;

  const readinessScore = findings.length ? 10 - (resolved / total) * 10 : 5.0;

  const highCritical = findings.filter((f) => f.severity === 'HIGH' || f.severity === 'CRITICAL').length;
  const confidence = findings.length ? (highCritical / total) * 100 : 0;
  const confidenceScore = findings.length ? Math.min(10, 2 + confidence / 10) : 2.0;

  const byFile: Record<string, number> = {};
  findings.forEach((f) => {
    byFile[f.file_path] = Math.max(byFile[f.file_path] || 0, typeof f.risk_score === 'number' ? f.risk_score : 0);
  });
  const fileEntries = Object.entries(byFile).sort((a, b) => b[1] - a[1]);
  const topFile = fileEntries[0] as [string, number] | undefined;
  const targetScore = topFile ? Math.max(4, Math.min(10, topFile[1])) : 3.0;

  const repoCount = Math.max(1, (dashboard.repos && dashboard.repos.length) || 1);
  const highTotal = (dashboard.risk_levels && dashboard.risk_levels.HIGH) || 0;
  const exposureScore = Math.min(10, (open * 2 + highTotal) / repoCount);

  const bannedTokens = new Set<string>();
  (policy.forbidden_modules || []).forEach((m) => bannedTokens.add(String(m).toLowerCase()));
  (policy.forbidden_functions || []).forEach((f) => bannedTokens.add(String(f).toLowerCase()));
  (policy.sensitive_paths || []).forEach((p) => bannedTokens.add(String(p).toLowerCase()));
  const policyHits = findings.filter((f) => {
    const haystack = `${f.vuln_type} ${f.file_path}`.toLowerCase();
    return [...bannedTokens].some((b) => haystack.includes(b));
  }).length;
  const policyScore =
    policyHits > 0 ? 9.0 : policy.forbidden_modules && policy.forbidden_modules.length > 0 ? 5.0 : 3.0;

  const factors: RiskFactorItem[] = [
    {
      id: 'f1',
      name: '01 SEVERITY (CVSS BASE)',
      weight: WEIGHTS[0],
      score: severityScore,
      status: statusForScore(severityScore),
      description: findings.length
        ? `Peak severity ${severestLabel} present across ${total} recorded findings.`
        : 'No findings recorded — using dashboard average risk as baseline.',
      threadColor: '#FF1E2D',
    },
    {
      id: 'f2',
      name: '02 VULNERABILITY TYPE (CWE)',
      weight: WEIGHTS[1],
      score: typeScore,
      status: statusForScore(typeScore),
      description: topType
        ? `Dominant class ${topType[0]} (${topType[1]} occurrence${topType[1] > 1 ? 's' : ''}).`
        : 'No vulnerability classes detected.',
      threadColor: '#00A8FF',
    },
    {
      id: 'f3',
      name: '03 VALIDATION RESULT',
      weight: WEIGHTS[2],
      score: readinessScore,
      status: statusForScore(readinessScore),
      description: `${resolved} of ${Math.max(1, total)} findings closed or validated — residual ${open} open.`,
      threadColor: '#007BFF',
    },
    {
      id: 'f4',
      name: '04 CONFIDENCE ADJUSTMENT',
      weight: WEIGHTS[3],
      score: confidenceScore,
      status: statusForScore(confidenceScore),
      description: `${highCritical} high/critical findings — detection confidence ${confidence.toFixed(0)}% of sample.`,
      threadColor: '#00E699',
    },
    {
      id: 'f5',
      name: '05 TARGET FILE CRITICALITY',
      weight: WEIGHTS[4],
      score: targetScore,
      status: statusForScore(targetScore),
      description: topFile ? `Highest-risk path: ${topFile[0]} (risk ${topFile[1].toFixed(1)}).` : 'No scan data to score.',
      threadColor: '#5BC9FF',
    },
    {
      id: 'f6',
      name: '06 EXPOSURE DENSITY',
      weight: WEIGHTS[5],
      score: exposureScore,
      status: statusForScore(exposureScore),
      description: `${open} open findings across ${dashboard.repos ? dashboard.repos.length : 0} repositories.`,
      threadColor: '#00A8FF',
    },
    {
      id: 'f7',
      name: '07 POLICY VIOLATIONS',
      weight: WEIGHTS[6],
      score: policyScore,
      status: statusForScore(policyScore),
      description:
        policyHits > 0
          ? `${policyHits} findings reference forbidden modules or sensitive paths.`
          : 'No policy rule breaches detected.',
      threadColor: '#FF1E2D',
    },
  ];

  const aggregate = factors.reduce((acc, f) => acc + f.weight * f.score, 0);
  const discounted = aggregate * (1 - (confidence / 100) * 0.15);

  const hasRemediation = typeof dashboard.remediation_rate === 'number' && dashboard.remediation_rate > 0;

  return {
    factors,
    aggregate: hasData ? discounted : 0,
    open,
    total,
    remediation: hasRemediation ? dashboard.remediation_rate : null,
    confidence: hasData ? confidence : 0,
    hasData,
  };
}

function classificationFor(score: number): { label: string; color: string } {
  if (score >= 8) return { label: 'HIGH RISK CLASSIFICATION', color: '#FF1E2D' };
  if (score >= 6) return { label: 'ELEVATED RISK LEVEL', color: '#FF9A5C' };
  if (score >= 4) return { label: 'MODERATE RISK LEVEL', color: '#D9E1EA' };
  return { label: 'LOW RISK LEVEL', color: '#00E699' };
}

export const View11Risk: React.FC<{ onNavigate: (view: ViewId) => void }> = () => {
  const [model, setModel] = useState<RiskModel | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getDashboardData(), getFindings(), getPolicy().catch(() => ({}))])
      .then(([dashboard, findings, policy]) => {
        if (!cancelled) setModel(buildRiskModel(dashboard, findings, policy as PolicyData));
      })
      .catch(() => {
        if (!cancelled) setModel(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const aggregate = model ? model.aggregate : 0;
  const classification = classificationFor(aggregate);

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>MATHEMATICAL FORMULATION // DYNAMIC RISK MATRIX</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            7-Factor Contextual Risk Engine
          </h1>
        </div>
      </div>

      {/* Math Formulation Callout */}
      <GlassPanel
        headerTitle="MATHEMATICAL RISK FORMULATION"
        headerCode="FORMULA_SPEC_V2"
        statusIndicator="ACTIVE"
      >
        <div className="p-4 bg-[#020B1A] border border-[#17406E] font-mono text-xs text-[#5BC9FF] leading-relaxed">
          <div className="text-white font-semibold mb-1">FORMULATION:</div>
          <div><code>Risk_Score = ∑ (Weight_i × Raw_Score_i) × (1 - (Confidence_Factor / 100) × 0.15)</code></div>
          <div className="text-[#9AA7B8] text-[11px] mt-2">
            Factors derived live from dashboard aggregates, stored findings, and active policy rules.
          </div>
        </div>
      </GlassPanel>

      {loading ? (
        <div className="p-8 bg-[#050B16] border border-[#17406E] text-center font-mono text-xs text-[#9AA7B8]">
          COMPUTING CONTEXTUAL RISK MODEL...
        </div>
      ) : !model || !model.hasData ? (
        <div className="p-8 bg-[#050B16] border border-[#17406E] text-center font-mono">
          <div className="text-[#9AA7B8] text-xs mb-2">NO SCAN DATA AVAILABLE</div>
          <p className="text-[11px] text-[#9AA7B8]">
            Run a GitHub PR scan or ingest webhook events to populate the risk model.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          {/* Aggregate Score & Classification (4 cols) */}
          <div className="lg:col-span-4">
            <GlassPanel
              headerTitle="COMPUTED RISK SCORE"
              headerCode="AGGREGATE"
              statusIndicator="ALERT"
              accentColor={classification.color}
              className="text-center py-6"
            >
              <div className="font-headline font-black text-5xl text-white mb-1">
                {aggregate.toFixed(2)}
              </div>
              <div
                className="font-mono text-xs font-bold tracking-widest mb-4"
                style={{ color: classification.color }}
              >
                {classification.label}
              </div>
              <div className="p-3 bg-[#020B1A] border border-[#17406E] text-left font-mono text-[11px] text-[#9AA7B8] space-y-1">
                <div className="flex justify-between">
                  <span>OPEN FINDINGS:</span>
                  <span className={model.open > 0 ? 'text-[#FF1E2D] font-bold' : 'text-[#00E699] font-bold'}>
                    {model.open} / {model.total}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>REMEDIATION RATE:</span>
                  <span className="text-[#00E699] font-bold">
                    {model.remediation != null ? `${model.remediation}%` : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>MODEL CONFIDENCE:</span>
                  <span className="text-white font-bold">{model.confidence.toFixed(0)}%</span>
                </div>
              </div>
            </GlassPanel>
          </div>

          {/* Factors (8 cols) */}
          <div className="lg:col-span-8 space-y-2">
            {model.factors.map((factor) => (
              <div
                key={factor.id}
                className="p-3 bg-[#050B16] border border-[#17406E] font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-white font-semibold">{factor.name}</span>
                    <span className="text-[10px] text-[#00A8FF]">({Math.round(factor.weight * 100)}% WEIGHT)</span>
                  </div>
                  <p className="text-[11px] text-[#9AA7B8]">{factor.description}</p>
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  <div className="w-24 bg-[#020B1A] h-2 border border-[#17406E]">
                    <div
                      className="h-full"
                      style={{
                        width: `${(factor.score / 10) * 100}%`,
                        backgroundColor: factor.threadColor
                      }}
                    />
                  </div>
                  <span className="font-bold text-white w-8 text-right">{factor.score.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};