import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';

export const View14Reports: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const reports = [
    { id: 'REP-2026-0901', title: 'Q3 Enterprise AST Audit & Remediation Certification', grade: 'A+', compliance: 98.4, mitigated: 412, date: '2026-09-01', hash: 'sha256:8f3b...9d01' },
    { id: 'REP-2026-0815', title: 'Bi-Weekly Sandbox Isolation & Syscall Compliance Report', grade: 'A', compliance: 95.8, mitigated: 289, date: '2026-08-15', hash: 'sha256:4a12...22fa' },
    { id: 'REP-2026-0801', title: 'Monthly Multi-Agent Remediation Verification Digest', grade: 'A+', compliance: 99.1, mitigated: 531, date: '2026-08-01', hash: 'sha256:e90c...771b' },
  ];

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>AUDIT DOCUMENTATION // COMPLIANCE ARCHIVE</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Security Reports Hub
          </h1>
        </div>

        <CyberButton
          variant="secondary"
          size="sm"
          onClick={() => onNavigate('report-detail')}
        >
          VIEW DETAILED AUDIT (VIEW 15)
        </CyberButton>
      </div>

      {/* Reports List */}
      <div className="space-y-4">
        {reports.map((rep) => (
          <GlassPanel
            key={rep.id}
            headerTitle={rep.title}
            headerCode={rep.id}
            statusIndicator="ACTIVE"
          >
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center font-mono text-xs">
              <div className="lg:col-span-8 space-y-2">
                <div className="flex flex-wrap items-center gap-4 text-[11px] text-[#9AA7B8]">
                  <span>DATE: <strong className="text-white">{rep.date}</strong></span>
                  <span>AUDIT HASH: <code className="text-[#00A8FF]">{rep.hash}</code></span>
                  <span>MITIGATED VULNS: <strong className="text-white">{rep.mitigated}</strong></span>
                </div>
                <p className="text-[11px] text-[#9AA7B8]">
                  Cryptographically signed audit statement validating zero unmitigated critical CWEs across 128 production repositories.
                </p>
              </div>

              <div className="lg:col-span-4 flex items-center justify-between lg:justify-end gap-4">
                <div className="text-center p-2 bg-[#020B1A] border border-[#17406E] w-20">
                  <span className="text-[10px] text-[#9AA7B8] block">GRADE</span>
                  <span className="font-headline font-bold text-xl text-[#00E699]">{rep.grade}</span>
                </div>

                <div className="text-center p-2 bg-[#020B1A] border border-[#17406E] w-24">
                  <span className="text-[10px] text-[#9AA7B8] block">COMPLIANCE</span>
                  <span className="font-headline font-bold text-base text-white">{rep.compliance}%</span>
                </div>

                <CyberButton
                  variant="primary"
                  size="sm"
                  onClick={() => onNavigate('report-detail')}
                >
                  INSPECT
                </CyberButton>
              </div>
            </div>
          </GlassPanel>
        ))}
      </div>
    </div>
  );
};
