import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { Settings, Save, Sliders, Shield, Terminal, CheckCircle2 } from 'lucide-react';
import { getSettings, updateSettings } from '../../api/client';

export const View17Settings: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const [scanMode, setScanMode] = useState('docker_only');
  const [sandboxNetwork, setSandboxNetwork] = useState('none');
  const [codeqlEnabled, setCodeqlEnabled] = useState(false);
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
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError('Failed to persist settings.');
    }
  };

  return (
    <div className="py-8 px-4 sm:px-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1E3C5C]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00CFFF] tracking-widest mb-1">
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

          <CyberButton
            variant="secondary"
            size="sm"
            onClick={() => onNavigate('status')}
          >
            SYSTEM HEALTH (VIEW 18)
          </CyberButton>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-[#8F1424]/20 border border-[#FF304F] text-[#FF304F] font-mono text-xs">
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
              <div className="flex justify-between text-[#8D9AAA]">
                <span>ACTIVE SCAN MODE:</span>
                <span className="text-[#00CFFF] font-bold">{scanMode.toUpperCase()}</span>
              </div>
              <select
                value={scanMode}
                onChange={(e) => setScanMode(e.target.value)}
                className="w-full bg-[#06101F] border border-[#1E3C5C] text-[#D7DEE7] px-3 py-2 cursor-pointer"
              >
                <option value="docker_only">docker_only</option>
                <option value="sandbox_with_local_fallback">sandbox_with_local_fallback</option>
              </select>
              <div className="flex justify-between text-[10px] text-[#8D9AAA]">
                <span>DOCKER-ONLY / SANDBOX + LOCAL FALLBACK</span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-[#1E3C5C]/50">
              <span className="text-white">CodeQL Provisioning:</span>
              <button
                onClick={() => setCodeqlEnabled(!codeqlEnabled)}
                className={`px-3 py-1 text-[10px] font-bold border transition-colors ${
                  codeqlEnabled
                    ? 'bg-[#00E699]/20 border-[#00E699] text-[#00E699]'
                    : 'bg-[#030914] border-[#1E3C5C] text-[#8D9AAA]'
                }`}
              >
                {codeqlEnabled ? 'ENABLED' : 'DISABLED'}
              </button>
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
              <div className="flex justify-between text-[#8D9AAA]">
                <span>NETWORK MODE:</span>
                <span className="text-[#00E699] font-bold">{sandboxNetwork.toUpperCase()}</span>
              </div>
              <select
                value={sandboxNetwork}
                onChange={(e) => setSandboxNetwork(e.target.value)}
                className="w-full bg-[#06101F] border border-[#1E3C5C] text-[#D7DEE7] px-3 py-2 cursor-pointer"
              >
                <option value="none">none (airgap)</option>
                <option value="bridge">bridge</option>
              </select>
              <div className="flex justify-between text-[10px] text-[#8D9AAA]">
                <span>DOCKER: {dockerAvailable ? 'AVAILABLE' : 'UNAVAILABLE'}</span>
              </div>
            </div>

            <div className="p-2.5 bg-[#02050B] border border-[#1E3C5C] space-y-1 text-[10px] text-[#8D9AAA]">
              <div className="text-[#00CFFF]">ISOLATION POLICY:</div>
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
