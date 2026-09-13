import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId, RepositoryItem } from '../../types';
import { Plus, RefreshCw } from 'lucide-react';
import { getDashboardData } from '../../api/client';

interface View05RepositoriesProps {
  onNavigate: (view: ViewId) => void;
}

export const View05Repositories: React.FC<View05RepositoriesProps> = ({ onNavigate }) => {
  const [repositories, setRepositories] = useState<RepositoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRepos = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDashboardData();
      setRepositories(
        (data.repos || []).map((repo, idx) => {
          const highRisk = Number(repo.high_risk || 0);
          const medRisk = Number(repo.med_risk || 0);
          const lowRisk = Number(repo.low_risk || 0);
          const openFindings = highRisk + medRisk + lowRisk;
          const lastScanRaw =
            typeof repo.last_scan_at === 'string' && repo.last_scan_at
              ? repo.last_scan_at
              : 'Not scanned';
          const lastScan = lastScanRaw === 'Not scanned'
            ? lastScanRaw
            : new Date(lastScanRaw).toLocaleString();
          return {
            id: String(repo.id),
            name: repo.full_name || repo.name || 'unnamed-repo',
            branch: 'main',
            status: openFindings > 0 ? ('ACTION_REQUIRED' as const) : ('PROTECTED' as const),
            lastScan,
            openFindings,
            astHealth: Math.max(0, Math.min(100, 100 - openFindings * 8 - idx * 2)),
          };
        })
      );
    } catch (e) {
      setError('Unable to load repositories. Check your GitHub App installation.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRepos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>REPOSITORY MATRIX // PR GATES</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Protected Repository Inventory
          </h1>
        </div>

        <div className="flex items-center space-x-2">
          <CyberButton
            variant="secondary"
            size="sm"
            icon={<RefreshCw className="w-4 h-4" />}
            onClick={loadRepos}
            loading={loading}
          >
            SYNC
          </CyberButton>
          <CyberButton
            variant="primary"
            size="sm"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => onNavigate('github')}
          >
            CONNECT NEW REPO
          </CyberButton>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-[#7E1120]/20 border border-[#FF1E2D] text-[#FF1E2D] font-mono text-xs">
          {error}
        </div>
      )}

      {loading && repositories.length === 0 && (
        <div className="flex items-center justify-center py-16 font-mono text-xs text-[#9AA7B8] animate-pulse">
          LOADING REPOSITORY MATRIX...
        </div>
      )}

      {/* Repositories Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {repositories.map((repo) => {
          const isAlert = repo.status === 'ACTION_REQUIRED';
          const isScanning = repo.status === 'SCANNING';

          return (
            <GlassPanel
              key={repo.id}
              headerTitle={repo.name}
              headerCode={repo.branch}
              statusIndicator={isAlert ? 'ALERT' : isScanning ? 'WARNING' : 'ACTIVE'}
              accentColor={isAlert ? '#FF1E2D' : '#00A8FF'}
              className="flex flex-col justify-between h-full"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-[#9AA7B8]">STATUS:</span>
                  <span
                    className={`px-2 py-0.5 font-bold rounded ${
                      isAlert
                        ? 'bg-[#7E1120]/40 text-[#FF1E2D] border border-[#FF1E2D]'
                        : isScanning
                        ? 'bg-[#007BFF]/20 text-[#00A8FF] border border-[#00A8FF] animate-pulse'
                        : 'bg-[#00E699]/20 text-[#00E699] border border-[#00E699]'
                    }`}
                  >
                    {repo.status}
                  </span>
                </div>

                <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-2 font-mono text-xs">
                  <div className="flex justify-between">
                    <span className="text-[#9AA7B8]">AST HEALTH SCORE:</span>
                    <span className="text-white font-bold">{repo.astHealth}%</span>
                  </div>
                  <div className="w-full bg-[#050B16] h-1.5">
                    <div
                      className={`h-full ${isAlert ? 'bg-[#FF1E2D]' : 'bg-[#00E699]'}`}
                      style={{ width: `${repo.astHealth}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#9AA7B8]">OPEN FINDINGS:</span>
                    <span className={isAlert ? 'text-[#FF1E2D] font-bold' : 'text-[#D9E1EA]'}>
                      {repo.openFindings} VULNERABILITIES
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] text-[#9AA7B8]">
                    <span>LAST AUDIT:</span>
                    <span>{repo.lastScan}</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 flex items-center space-x-2">
                <CyberButton
                  variant={isAlert ? 'threat' : 'secondary'}
                  size="sm"
                  className="w-full"
                  onClick={() => onNavigate(isAlert ? 'findings' : isScanning ? 'scanner' : 'scanner')}
                >
                  {isAlert ? 'REVIEW FINDINGS' : 'RUN AST SCAN'}
                </CyberButton>
              </div>
            </GlassPanel>
          );
        })}
      </div>
    </div>
  );
};
