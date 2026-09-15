import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { ViewId, PolicyData } from '../../types';
import { getPolicy } from '../../api/client';

type Sanitizer = { type: string; sanitizer: string };

export const View10Policy: React.FC<{ onNavigate: (view: ViewId) => void }> = () => {
  const [policy, setPolicy] = useState<PolicyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    getPolicy()
      .then(setPolicy)
      .catch(() => {
        setFetchError('Unable to load policy from the backend service. Please try again shortly.');
      })
      .finally(() => setLoading(false));
  }, []);

  const blockedModules: { name: string; reason: string }[] =
    Array.isArray(policy?.forbidden_modules)
      ? policy.forbidden_modules.map((m: string) => ({ name: m, reason: 'Forbidden by policy engine' }))
      : [];

  const forbiddenFuncs: { name: string; replacement: string }[] =
    Array.isArray(policy?.forbidden_functions)
      ? policy.forbidden_functions.map((f: string) => ({
          name: `${f}()`,
          replacement: 'Rejected by policy (fail-closed)',
        }))
      : [];

  const sanitizers: Sanitizer[] = policy?.mandatory_sanitizers
    ? Object.entries(policy.mandatory_sanitizers).map(([target, opts]) => ({
        type: target,
        sanitizer: (Array.isArray(opts) ? opts : []).join(', ') || 'enforced',
      }))
    : [];

  const sensitivePaths: string[] = Array.isArray(policy?.sensitive_paths)
    ? policy.sensitive_paths
    : [];

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>ORGANIZATIONAL GOVERNANCE // RULE ENFORCEMENT</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Governance & Security Policy Gateway
          </h1>
        </div>

        <div className="px-3 py-1.5 bg-[#050B16] border border-[#17406E] font-mono text-[10px] text-[#9AA7B8]">
          {loading ? 'LOADING POLICY...' : `POLICY ${policy?.version || '1.0'} // ${policy?.policy_name || 'Standard Enterprise Security Policy'}`}
        </div>
      </div>

      {fetchError && (
        <div className="p-4 bg-[#7E1120]/20 border border-[#FF1E2D] text-[#FF1E2D] font-mono text-xs">
          {fetchError}
        </div>
      )}

      {/* 4 Policy Panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Panel 1: Blocked Modules */}
        <GlassPanel
          headerTitle="POLICY RULE: BANNED MODULE IMPORTS"
          headerCode="ARG-POL-01"
          statusIndicator={blockedModules.length ? 'ALERT' : 'ACTIVE'}
          accentColor={blockedModules.length ? '#FF1E2D' : '#00E699'}
        >
          <div className="space-y-3 font-mono text-xs">
            <p className="text-[#9AA7B8] text-[11px]">
              AST scanner prohibits import statements targeting insecure, unmaintained, or legacy modules.
            </p>
            <div className="space-y-2">
              {blockedModules.length === 0 && (
                <div className="p-2.5 bg-[#020B1A] border border-[#17406E] text-[#9AA7B8] text-[10px]">
                  No banned modules configured.
                </div>
              )}
              {blockedModules.map((m) => (
                <div key={m.name} className="p-2.5 bg-[#020B1A] border border-[#17406E] flex items-center justify-between">
                  <div>
                    <span className="text-white font-bold">{m.name}</span>
                    <span className="text-[10px] text-[#9AA7B8] block">{m.reason}</span>
                  </div>
                  <span className="px-2 py-0.5 bg-[#7E1120]/40 text-[#FF1E2D] border border-[#FF1E2D] text-[10px] font-bold">
                    BLOCKED
                  </span>
                </div>
              ))}
            </div>
          </div>
        </GlassPanel>

        {/* Panel 2: Prohibited Functions */}
        <GlassPanel
          headerTitle="POLICY RULE: FORBIDDEN SINK FUNCTIONS"
          headerCode="ARG-POL-02"
          statusIndicator={forbiddenFuncs.length ? 'ALERT' : 'ACTIVE'}
          accentColor={forbiddenFuncs.length ? '#FF1E2D' : '#00E699'}
        >
          <div className="space-y-3 font-mono text-xs">
            <p className="text-[#9AA7B8] text-[11px]">
              Direct calls to these function identifiers trigger immediate AST validation rejections.
            </p>
            <div className="space-y-2">
              {forbiddenFuncs.length === 0 && (
                <div className="p-2.5 bg-[#020B1A] border border-[#17406E] text-[#9AA7B8] text-[10px]">
                  No forbidden functions configured.
                </div>
              )}
              {forbiddenFuncs.map((f) => (
                <div key={f.name} className="p-2.5 bg-[#020B1A] border border-[#17406E] flex items-center justify-between">
                  <div>
                    <span className="text-white font-bold">{f.name}</span>
                    <span className="text-[10px] text-[#5BC9FF] block">{f.replacement}</span>
                  </div>
                  <span className="px-2 py-0.5 bg-[#7E1120]/40 text-[#FF1E2D] border border-[#FF1E2D] text-[10px] font-bold">
                    BANNED
                  </span>
                </div>
              ))}
            </div>
          </div>
        </GlassPanel>

        {/* Panel 3: Mandatory Sanitizers */}
        <GlassPanel
          headerTitle="POLICY RULE: MANDATORY SANITIZERS"
          headerCode="ARG-POL-03"
          statusIndicator="ACTIVE"
          accentColor="#00E699"
        >
          <div className="space-y-3 font-mono text-xs">
            <p className="text-[#9AA7B8] text-[11px]">
              Inbound external inputs must pass through verified sanitization nodes before reaching database or network sinks.
            </p>
            <div className="space-y-2">
              {sanitizers.length === 0 && (
                <div className="p-2.5 bg-[#020B1A] border border-[#17406E] text-[#9AA7B8] text-[10px]">
                  No mandatory sanitizers configured.
                </div>
              )}
              {sanitizers.map((s) => (
                <div key={s.type} className="p-2.5 bg-[#020B1A] border border-[#17406E] flex items-center justify-between">
                  <div>
                    <span className="text-white font-bold">{s.type}</span>
                    <span className="text-[10px] text-[#00E699] block">{s.sanitizer}</span>
                  </div>
                  <span className="px-2 py-0.5 bg-[#00E699]/20 text-[#00E699] border border-[#00E699] text-[10px] font-bold">
                    REQUIRED
                  </span>
                </div>
              ))}
            </div>
          </div>
        </GlassPanel>

        {/* Panel 4: Sensitive Paths */}
        <GlassPanel
          headerTitle="POLICY RULE: SENSITIVE PATH SURVEILLANCE"
          headerCode="ARG-POL-04"
          statusIndicator="ACTIVE"
        >
          <div className="space-y-4 font-mono text-xs">
            <p className="text-[#9AA7B8] text-[11px]">
              File paths matching these patterns receive elevated risk scoring and mandatory review on every pull request.
            </p>

            <div className="p-3 bg-[#020B1A] border border-[#17406E] space-y-2">
              {sensitivePaths.length === 0 && (
                <div className="text-[#9AA7B8] text-[10px]">No sensitive paths configured.</div>
              )}
              {sensitivePaths.map((p) => (
                <div key={p} className="flex items-center justify-between">
                  <span className="text-[#00A8FF] font-mono">{p}/</span>
                  <span className="px-2 py-0.5 bg-[#007BFF]/20 text-[#00A8FF] border border-[#00A8FF] text-[10px] font-bold">
                    ELEVATED
                  </span>
                </div>
              ))}
            </div>
          </div>
        </GlassPanel>
      </div>
    </div>
  );
};
