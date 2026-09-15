import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { Save } from 'lucide-react';
import { getSettings, updateSettings } from '../../api/client';

export const View17Settings: React.FC<{ onNavigate: (view: ViewId) => void }> = () => {
  const [scanMode, setScanMode] = useState('docker_only');
  const [sandboxNetwork, setSandboxNetwork] = useState('none');
  const [codeqlEnabled, setCodeqlEnabled] = useState(false);
  const [patchMode, setPatchMode] = useState('both');
  const [dockerAvailable, setDockerAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSettings();
      setScanMode(res.settings.scan_mode || 'docker_only');
      setSandboxNetwork(res.settings.sandbox_network || 'none');
      setCodeqlEnabled(Boolean(res.settings.codeql_enabled));
      setPatchMode(res.settings.patch_mode || 'both');
      setDockerAvailable(Boolean(res.options.docker_available));
    } catch (e) {
      setError('Unable to load settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async () => {
    setSaved(false);
    setError(null);
    try {
      await updateSettings({
        scan_mode: scanMode,
        sandbox_network: sandboxNetwork,
        codeql_enabled: codeqlEnabled,
        patch_mode: patchMode,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError('Failed to persist settings.');
    }
  };

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>PLATFORM CONFIGURATION // OPERATOR TUNING</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Enterprise Operator Settings
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <CyberButton
            variant="primary"
            size="sm"
            icon={<Save className="w-3.5 h-3.5" />}
            onClick={handleSave}
            loading={loading}
          >
            {saved ? 'SETTINGS PERSISTED' : 'SAVE CONFIGURATION'}
          </CyberButton>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-[#7E1120]/20 border border-[#FF1E2D] text-[#FF1E2D] font-mono text-xs">
          {error}
        </div>
      )}

      {/* Settings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Scan Mode */}
        <GlassPanel
          headerTitle="PR SCAN MODE"
          headerCode="SCANMODE"
          statusIndicator="ACTIVE"
        >
          <div className="space-y-4 font-mono text-xs">
            <div className="space-y-2">
              <div className="flex justify-between text-[#9AA7B8]">
                <span>ACTIVE SCAN MODE:</span>
                <span className="text-[#00A8FF] font-bold">{scanMode.toUpperCase()}</span>
              </div>
              <select
                value={scanMode}
                onChange={(e) => setScanMode(e.target.value)}
                className="w-full bg-[#050B16] border border-[#17406E] text-[#D9E1EA] px-3 py-2 cursor-pointer"
              >
                <option value="docker_only">docker_only</option>
                <option value="ci_fallback">ci_fallback</option>
              </select>
              <div className="flex justify-between text-[10px] text-[#9AA7B8]">
                <span>DOCKER-ONLY / CI-RUNNER FALLBACK</span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-[#17406E]/50">
              <span className="text-white">CodeQL Provisioning:</span>
              <button
                onClick={() => setCodeqlEnabled(!codeqlEnabled)}
                className={`px-3 py-1 text-[10px] font-bold border transition-colors ${
                  codeqlEnabled
                    ? 'bg-[#00E699]/20 border-[#00E699] text-[#00E699]'
                    : 'bg-[#050B16] border-[#17406E] text-[#9AA7B8]'
                }`}
              >
                {codeqlEnabled ? 'ENABLED' : 'DISABLED'}
              </button>
            </div>
          </div>
        </GlassPanel>

        {/* Patch Generation Strategy */}
        <GlassPanel
          headerTitle="PATCH GENERATION STRATEGY"
          headerCode="PATCHSTRAT"
          statusIndicator="ACTIVE"
        >
          <div className="space-y-4 font-mono text-xs">
            <div className="space-y-2">
              <div className="flex justify-between text-[#9AA7B8]">
                <span>ACTIVE STRATEGY:</span>
                <span className="text-[#00A8FF] font-bold">
                  {patchMode === 'deterministic_only' ? 'AST ONLY' : 'AST + LLM'}
                </span>
              </div>
              <select
                value={patchMode}
                onChange={(e) => setPatchMode(e.target.value)}
                className="w-full bg-[#050B16] border border-[#17406E] text-[#D9E1EA] px-3 py-2 cursor-pointer"
              >
                <option value="both">both</option>
                <option value="deterministic_only">deterministic_only</option>
              </select>
              <div className="flex justify-between text-[10px] text-[#9AA7B8]">
                <span>AST + LLM / AST ONLY</span>
              </div>
            </div>

            <div className="p-2.5 bg-[#020B1A] border border-[#17406E] space-y-1 text-[10px] text-[#9AA7B8]">
              <div className="text-[#00A8FF]">TRADE-OFF MATRIX:</div>
              <div>AST ONLY — deterministic &amp; faster, lower scan cost</div>
              <div>AST + LLM — context-aware patches, more validation time</div>
            </div>
          </div>
        </GlassPanel>

        {/* Sandbox Runtime Parameters */}
        <GlassPanel
          headerTitle="SANDBOX EXECUTION PARAMETERS"
          headerCode="DOCKER_CGROUPS"
          statusIndicator="ACTIVE"
        >
          <div className="space-y-4 font-mono text-xs">
            <div className="space-y-2">
              <div className="flex justify-between text-[#9AA7B8]">
                <span>NETWORK MODE:</span>
                <span className="text-[#00E699] font-bold">{sandboxNetwork.toUpperCase()}</span>
              </div>
              <select
                value={sandboxNetwork}
                onChange={(e) => setSandboxNetwork(e.target.value)}
                className="w-full bg-[#050B16] border border-[#17406E] text-[#D9E1EA] px-3 py-2 cursor-pointer"
              >
                <option value="none">none (airgap)</option>
                <option value="bridge">bridge</option>
              </select>
              <div className="flex justify-between text-[10px] text-[#9AA7B8]">
                <span>DOCKER: {dockerAvailable ? 'AVAILABLE' : 'UNAVAILABLE'}</span>
              </div>
            </div>

            <div className="p-2.5 bg-[#020B1A] border border-[#17406E] space-y-1 text-[10px] text-[#9AA7B8]">
              <div className="text-[#00A8FF]">ISOLATION POLICY:</div>
              <div>Network: {sandboxNetwork.toUpperCase()}</div>
              <div>Rootfs read-only (--read-only)</div>
              <div>Max process table PID limit: 32</div>
            </div>
          </div>
        </GlassPanel>
      </div>
    </div>
  );
};
