import React from 'react';
import { CyberButton } from '../common/CyberButton';
import { GlassPanel } from '../common/GlassPanel';
import { ViewId } from '../../types';
import { AuditReport } from '../../utils/reports';
import { Download, Printer, ArrowLeft } from 'lucide-react';
import { TacticalBracket } from '../common/TacticalBracket';

interface View15ReportDetailProps {
  onNavigate: (view: ViewId) => void;
  report: AuditReport | null;
}

export const View15ReportDetail: React.FC<View15ReportDetailProps> = ({ onNavigate, report }) => {
  const handleExportJSON = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report.payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.code.toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  if (!report) {
    return (
      <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
        <div className="flex items-center space-x-2 font-mono text-xs text-[#9AA7B8] hover:text-white transition-colors">
          <button
            onClick={() => onNavigate('reports')}
            className="inline-flex items-center space-x-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>RETURN TO REPORTS HUB</span>
          </button>
        </div>

        <GlassPanel statusIndicator="STANDBY">
          <div className="text-center space-y-3">
            <p className="font-mono text-xs text-[#9AA7B8]">
              NO REPORT SELECTED
            </p>
            <p className="font-mono text-[10px] text-[#6B7A8D] max-w-md mx-auto">
              Select a report from the Security Reports Hub to view its detail.
            </p>
            <CyberButton variant="secondary" size="sm" onClick={() => onNavigate('reports')}>
              OPEN REPORTS HUB
            </CyberButton>
          </div>
        </GlassPanel>
      </div>
    );
  }

  const gradeColor = report.gradeScore >= 90 ? '#00E699' : report.gradeScore >= 75 ? '#FFC107' : '#FF1E2D';

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Top Header */}
      <div className="no-print flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
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

      {/* Formal Audit Document */}
      <div className="print-area relative p-8 sm:p-12 bg-[#050B16] border border-[#17406E] space-y-8 text-[#D9E1EA] font-mono text-xs shadow-2xl">
        <TacticalBracket color="#00A8FF" size="lg" />

        {/* Audit Document Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4 pb-6 border-b border-[#17406E]">
          <div>
            <div className="text-[10px] text-[#00A8FF] tracking-widest font-bold">
              AUREX // LIVE POSTURE COMPUTATION
            </div>
            <h1 className="font-headline font-bold text-2xl text-white mt-1">
              {report.title}
            </h1>
            <div className="text-[#9AA7B8] text-[11px] mt-1">
              RECORD ID: <span className="text-white">{report.code}</span> // PERIOD: {report.generatedAt.slice(0, 10)}
            </div>
          </div>

          <div className="text-right p-3 bg-[#050B16] border border-[#17406E]">
            <span className="text-[10px] text-[#9AA7B8] block">SECURITY GRADE</span>
            <span className="font-headline font-black text-3xl" style={{ color: gradeColor }}>
              {report.grade}
            </span>
          </div>
        </div>

        {/* Metrics Summary Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {report.metrics.slice(0, 4).map((m, i) => (
            <div key={i} className="p-3 bg-[#020B1A] border border-[#17406E] space-y-0.5">
              <span className="text-[10px] text-[#9AA7B8]">{m.label}</span>
              <div className="font-headline text-lg font-bold text-white">{m.value}</div>
            </div>
          ))}
        </div>

        {report.metrics.length > 4 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {report.metrics.slice(4).map((m, i) => (
              <div key={i} className="p-3 bg-[#020B1A] border border-[#17406E] space-y-0.5">
                <span className="text-[10px] text-[#9AA7B8]">{m.label}</span>
                <div className="font-headline text-lg font-bold text-white">{m.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Executive Attestation */}
        <div className="space-y-2">
          <h3 className="font-headline text-sm text-white font-bold">Executive Attestation Statement</h3>
          <p className="text-[#C2CDD9] leading-relaxed text-[11px]">
            {report.description}
          </p>
        </div>

        {/* Detail Rows */}
        {report.rows.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-headline text-sm text-white font-bold">Register Entries</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-[10px]">
                <thead>
                  <tr className="text-[#9AA7B8] border-b border-[#17406E]">
                    <th className="py-2 pr-4">SEVERITY</th>
                    <th className="py-2 pr-4">LABEL</th>
                    <th className="py-2 pr-4">DETAIL</th>
                    <th className="py-2 text-right">RISK</th>
                  </tr>
                </thead>
                <tbody className="text-[#D9E1EA]">
                  {report.rows.slice(0, 10).map((row, i) => {
                    const rowColor =
                      row.severity === 'HIGH' || row.severity === 'CRITICAL'
                        ? '#FF1E2D'
                        : row.severity === 'MEDIUM'
                          ? '#FFC107'
                          : row.severity === 'INFO'
                            ? '#00A8FF'
                            : '#00E699';
                    return (
                      <tr key={i} className="border-b border-[#17406E]/40">
                        <td className="py-2 pr-4" style={{ color: rowColor }}>
                          {row.severity}
                        </td>
                        <td className="py-2 pr-4 text-[#EAF1F8] max-w-[220px] truncate">{row.label}</td>
                        <td className="py-2 pr-4 text-[#9AA7B8] max-w-[280px] truncate">{row.detail}</td>
                        <td className="py-2 text-right text-[#9AA7B8]">{row.score.toFixed(1)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Cryptographic Proof Footer */}
        <div className="pt-6 border-t border-[#17406E] space-y-2 text-[10px] text-[#9AA7B8]">
          <div className="flex flex-col sm:flex-row justify-between gap-1">
            <span>REPORT FINGERPRINT (SHA-256):</span>
            <code className="text-[#00A8FF]">sha256:{report.hash.slice(0, 8)}...{report.hash.slice(-4)}</code>
          </div>
          <div className="flex flex-col sm:flex-row justify-between gap-1">
            <span>VERIFIED BY:</span>
            <span className="text-white">AUREX Console — live computation over stored scan and finding records</span>
          </div>
        </div>
      </div>
    </div>
  );
};
