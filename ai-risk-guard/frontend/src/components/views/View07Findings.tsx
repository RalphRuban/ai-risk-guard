import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId, VulnerabilityFinding } from '../../types';
import { ShieldAlert, AlertTriangle, CheckCircle, Wrench, ArrowRight, Filter, RefreshCw } from 'lucide-react';
import { getFindings } from '../../api/client';

export const View07Findings: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [findings, setFindings] = useState<VulnerabilityFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFindings = async (severity: string = filterSeverity) => {
    setLoading(true);
    setError(null);
    try {
      const raw = await getFindings({ status: 'open' });
      setFindings(
        raw.map((f) => ({
          id: `F-${f.id}`,
          cwe: String(f.vuln_type || 'GENERIC'),
          name: f.vuln_type ? String(f.vuln_type).replace(/_/g, ' ').toUpperCase() : 'Finding',
          file: f.file_path || 'unknown',
          line: typeof f.line_number === 'number' ? f.line_number : 0,
          severity: (String(f.severity).toUpperCase() as never) || 'LOW',
          confidence: f.risk_score != null ? 0.5 + Math.min(f.risk_score, 10) / 20 : 0.5,
          riskContribution: typeof f.risk_score === 'number' ? f.risk_score : 0,
          snippet: f.file_path ? `//SEC_FLAG @${f.file_path}` : 'no snippet available',
          remediationSnippet:
            f.repo_full_name && f.pr_number
              ? `${f.repo_full_name} #PR-${f.pr_number}`
              : 'Dispatch to Patch Workstation',
          status: f.status === 'open' ? ('UNPATCHED' as const) : ('PATCH_READY' as const),
        }))
      );
    } catch (e) {
      setError('Unable to load findings. Please check the backend service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFindings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = findings.filter(
    (f) => filterSeverity === 'ALL' || f.severity === filterSeverity
  );

  return (
    <div className="py-8 px-4 sm:px-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1E3C5C]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00CFFF] tracking-widest mb-1">
            <span>STATIC ANALYSIS RESULTS // FINDINGS MATRIX</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Vulnerability Findings & Intelligence
          </h1>
        </div>

        <div className="flex items-center space-x-2">
          <CyberButton
            variant="secondary"
            size="sm"
            icon={<RefreshCw className="w-3.5 h-3.5" />}
            loading={loading}
            onClick={() => loadFindings()}
          >
            SYNC
          </CyberButton>
          <CyberButton
            variant="primary"
            size="sm"
            icon={<Wrench className="w-3.5 h-3.5" />}
            onClick={() => onNavigate('patch')}
          >
            BATCH REMEDIATE (VIEW 08)
          </CyberButton>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-[#8F1424]/20 border border-[#FF304F] text-[#FF304F] font-mono text-xs">
          {error}
        </div>
      )}

      {loading && findings.length === 0 && (
        <div className="flex items-center justify-center py-16 font-mono text-xs text-[#8D9AAA] animate-pulse">
          LOADING FINDINGS MATRIX...
        </div>
      )}

      {/* Severity Filter Bar */}
      <div className="flex items-center space-x-2 border-b border-[#1E3C5C]/50 pb-3 font-mono text-xs">
        <span className="text-[#8D9AAA] text-[11px]">FILTER:</span>
        {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilterSeverity(sev)}
            className={`px-3 py-1 border transition-all text-[11px] ${
              filterSeverity === sev
                ? 'bg-[#087BFF]/30 border-[#00CFFF] text-[#65E7FF]'
                : 'bg-[#06101F] border-[#1E3C5C] text-[#8D9AAA] hover:text-white'
            }`}
          >
            {sev}
          </button>
        ))}
      </div>

      {/* Findings Cards */}
      <div className="space-y-4">
        {filtered.map((finding) => (
          <GlassPanel
            key={finding.id}
            headerTitle={`${finding.id} // ${finding.name}`}
            headerCode={finding.cwe}
            statusIndicator={finding.severity === 'CRITICAL' ? 'ALERT' : 'WARNING'}
            accentColor={finding.severity === 'CRITICAL' ? '#FF304F' : '#00CFFF'}
          >
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center font-mono text-xs">
              <div className="lg:col-span-8 space-y-2">
                <div className="text-[11px] text-[#00CFFF]">
                  FILE: <span className="text-white">{finding.file}:{finding.line}</span>
                </div>

                <div className="p-2.5 bg-[#02050B] border border-[#1E3C5C] text-[#FF304F] text-[11px]">
                  <code>- {finding.snippet}</code>
                </div>

                <div className="p-2.5 bg-[#02050B] border border-[#1E3C5C] text-[#00E699] text-[11px]">
                  <code>+ {finding.remediationSnippet}</code>
                </div>
              </div>

              <div className="lg:col-span-4 p-3 bg-[#030914] border border-[#1E3C5C] space-y-2 text-[11px] text-[#8D9AAA]">
                <div className="flex justify-between">
                  <span>CONFIDENCE:</span>
                  <span className="text-[#00E699] font-bold">{(finding.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>RISK CONTRIBUTION:</span>
                  <span className="text-[#FF304F] font-bold">{finding.riskContribution} / 10.0</span>
                </div>
                <div className="flex justify-between">
                  <span>REMEDIATION:</span>
                  <span className="text-[#65E7FF] font-bold">NodeTransformer</span>
                </div>

                <div className="pt-2">
                  <CyberButton
                    variant="primary"
                    size="sm"
                    className="w-full"
                    onClick={() => onNavigate('patch')}
                  >
                    DISPATCH TO PATCH WORKSTATION
                  </CyberButton>
                </div>
              </div>
            </div>
          </GlassPanel>
        ))}
      </div>
    </div>
  );
};
