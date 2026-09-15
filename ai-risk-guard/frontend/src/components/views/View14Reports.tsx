import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { DashboardData, getDashboardData } from '../../api/client';
import {
  AuditReport,
  buildReports,
  hasScanData,
  statusForScore,
} from '../../utils/reports';

interface View14ReportsProps {
  onNavigate: (view: ViewId) => void;
  onSelectReport: (report: AuditReport | null) => void;
}

export const View14Reports: React.FC<View14ReportsProps> = ({ onNavigate, onSelectReport }) => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [reports, setReports] = useState<AuditReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDashboardData();
      setDashboard(data);
      if (!hasScanData(data)) {
        setReports([]);
      } else {
        setReports(await buildReports(data));
      }
    } catch {
      setError('Unable to load security posture data from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleInspect = (report: AuditReport) => {
    onSelectReport(report);
    onNavigate('report-detail');
  };

  const header = (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
      <div>
        <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
          <span>AUDIT DOCUMENTATION // COMPLIANCE ARCHIVE</span>
        </div>
        <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
          Security Reports Hub
        </h1>
      </div>

      {!loading && !error && (
        <CyberButton variant="secondary" size="sm" onClick={load}>
          REFRESH
        </CyberButton>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
        {header}
        <div className="flex items-center justify-center h-64 font-mono text-xs text-[#9AA7B8] animate-pulse">
          LOADING POSTURE REPORTS ...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
        {header}
        <GlassPanel statusIndicator="ALERT">
          <div className="text-center space-y-3">
            <p className="font-mono text-xs text-[#FF1E2D]">{error}</p>
            <CyberButton variant="secondary" size="sm" onClick={load}>
              RETRY
            </CyberButton>
          </div>
        </GlassPanel>
      </div>
    );
  }

  if (!dashboard || !hasScanData(dashboard)) {
    return (
      <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
        {header}
        <GlassPanel statusIndicator="STANDBY">
          <div className="text-center space-y-3">
            <p className="font-mono text-xs text-[#9AA7B8]">
              NO SCAN DATA AVAILABLE YET
            </p>
            <p className="font-mono text-[10px] text-[#6B7A8D] max-w-md mx-auto">
              Once PR scans are processed by the analysis engine, posture and activity
              reports will appear here computed from real findings.
            </p>
            <CyberButton variant="secondary" size="sm" onClick={load}>
              REFRESH
            </CyberButton>
          </div>
        </GlassPanel>
      </div>
    );
  }

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {header}

      {/* Reports */}
      <div className="space-y-4">
        {reports.map((rep) => (
          <GlassPanel
            key={rep.id}
            headerTitle={rep.title}
            headerCode={rep.code}
            statusIndicator={statusForScore(rep.gradeScore)}
          >
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center font-mono text-xs">
              <div className="lg:col-span-8 space-y-2">
                <div className="flex flex-wrap items-center gap-4 text-[11px] text-[#9AA7B8]">
                  <span>DATE: <strong className="text-white">{rep.generatedAt.slice(0, 10)}</strong></span>
                  <span>AUDIT HASH: <code className="text-[#00A8FF]">sha256:{rep.hash.slice(0, 8)}...{rep.hash.slice(-4)}</code></span>
                  {rep.mitigations > 0 && (
                    <span>ACCEPTED PATCHES: <strong className="text-white">{rep.mitigations}</strong></span>
                  )}
                </div>
                <p className="text-[11px] text-[#9AA7B8]">{rep.description}</p>
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
                  onClick={() => handleInspect(rep)}
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