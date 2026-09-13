import React from 'react';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { Download, Printer, ArrowLeft } from 'lucide-react';
import { TacticalBracket } from '../common/TacticalBracket';

export const View15ReportDetail: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const handleExportJSON = () => {
    const data = {
      reportId: 'REP-2026-0901',
      date: '2026-09-01',
      securityGrade: 'A+',
      complianceScore: '98.4%',
      remediationPassRate: '94.2%',
      mitigatedVulnerabilities: 412,
      auditHash: 'sha256:8f3b29c049e917d018b76c81fae409941a29d01b',
      verifiedBy: 'AUREX Autonomous Orchestrator v2.4.0'
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'aurex-audit-rep-2026-0901.json';
    a.click();
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <button
          onClick={() => onNavigate('reports')}
          className="inline-flex items-center space-x-2 font-mono text-xs text-[#9AA7B8] hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>RETURN TO REPORTS HUB</span>
        </button>

        <div className="flex items-center space-x-3">
          <CyberButton
            variant="secondary"
            size="sm"
            icon={<Download className="w-3.5 h-3.5" />}
            onClick={handleExportJSON}
          >
            EXPORT JSON
          </CyberButton>

          <CyberButton
            variant="primary"
            size="sm"
            icon={<Printer className="w-3.5 h-3.5" />}
            onClick={handlePrint}
          >
            PRINT / PDF
          </CyberButton>
        </div>
      </div>

      {/* Restrained Formal Audit Document */}
      <div className="relative p-8 sm:p-12 bg-[#050B16] border border-[#17406E] space-y-8 text-[#D9E1EA] font-mono text-xs shadow-2xl">
        <TacticalBracket color="#00A8FF" size="lg" />

        {/* Audit Document Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4 pb-6 border-b border-[#17406E]">
          <div>
            <div className="text-[10px] text-[#00A8FF] tracking-widest font-bold">
              AUREX // AUTONOMOUS SECURITY ATTESTATION
            </div>
            <h1 className="font-headline font-bold text-2xl text-white mt-1">
              Executive Cybersecurity Audit Report
            </h1>
            <div className="text-[#9AA7B8] text-[11px] mt-1">
              RECORD ID: <span className="text-white">REP-2026-0901</span> // PERIOD: Q3-2026
            </div>
          </div>

          <div className="text-right p-3 bg-[#050B16] border border-[#17406E]">
            <span className="text-[10px] text-[#9AA7B8] block">SECURITY GRADE</span>
            <span className="font-headline font-black text-3xl text-[#00E699]">A+</span>
          </div>
        </div>

        {/* Metrics Summary Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-0.5">
            <span className="text-[10px] text-[#9AA7B8]">COMPLIANCE SCORE</span>
            <div className="font-headline text-lg font-bold text-white">98.4%</div>
          </div>
          <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-0.5">
            <span className="text-[10px] text-[#9AA7B8]">REMEDIATION RATE</span>
            <div className="font-headline text-lg font-bold text-[#00E699]">94.2%</div>
          </div>
          <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-0.5">
            <span className="text-[10px] text-[#9AA7B8]">SINK MITIGATIONS</span>
            <div className="font-headline text-lg font-bold text-[#00A8FF]">412 NODES</div>
          </div>
          <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-0.5">
            <span className="text-[10px] text-[#9AA7B8]">SANDBOX RUNS</span>
            <div className="font-headline text-lg font-bold text-white">412 PASS / 0 FAIL</div>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="space-y-2">
          <h3 className="font-headline text-sm text-white font-bold">Executive Attestation Statement</h3>
          <p className="text-[#C2CDD9] leading-relaxed text-[11px]">
            This document certifies that all inbound Pull Requests targeting protected branches within the enterprise organization were autonomously scanned using Abstract Syntax Tree compiler visitation, scored through the 7-Factor Contextual Risk formulation, rewritten by deterministic NodeTransformers, and validated under hardened 128MB container isolation. Zero high or critical unmitigated vulnerabilities remain active in production.
          </p>
        </div>

        {/* Cryptographic Proof Footer */}
        <div className="pt-6 border-t border-[#17406E] space-y-2 text-[10px] text-[#9AA7B8]">
          <div className="flex flex-col sm:flex-row justify-between gap-1">
            <span>CRYPTOGRAPHIC AUDIT HASH:</span>
            <code className="text-[#00A8FF]">sha256:8f3b29c049e917d018b76c81fae409941a29d01b6354</code>
          </div>
          <div className="flex flex-col sm:flex-row justify-between gap-1">
            <span>VERIFIED BY:</span>
            <span className="text-white">OrchestrationAgent Consensus Daemon (SHA-RSA 4096)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
