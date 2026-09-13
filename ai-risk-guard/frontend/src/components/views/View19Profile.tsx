import React, { useEffect, useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { User, Github, Mail, ShieldCheck, Server, ChevronRight } from 'lucide-react';
import { getMe, MeResponse } from '../../api/client';

export const View19Profile: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((res) => {
        if (!cancelled) setMe(res);
      })
      .catch(() => {
        if (!cancelled) setError('Unable to load operator profile.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const user = me?.user ?? null;

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00A8FF] tracking-widest mb-1">
            <span>OPERATOR IDENTITY // USER PROFILE</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Operator Profile
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <CyberButton
            variant="secondary"
            size="sm"
            onClick={() => onNavigate('dashboard')}
          >
            BACK TO DASHBOARD
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
        <div className="p-3 bg-[#7E1120]/20 border border-[#FF1E2D] text-[#FF1E2D] font-mono text-xs">
          {error}
        </div>
      )}

      {loading && (
        <div className="p-6 text-center font-mono text-xs text-[#9AA7B8]">
          VERIFYING OPERATOR CLEARANCE...
        </div>
      )}

      {!loading && user && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Identity Card */}
          <GlassPanel
            headerTitle="IDENTITY CARD"
            headerCode="VIEW-19"
            statusIndicator="ACTIVE"
          >
            <div className="flex flex-col items-center space-y-4 py-2">
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.login}
                  className="w-24 h-24 rounded-full border-2 border-[#00A8FF]/50 shadow-[0_0_25px_rgba(0,168,255,0.25)] object-cover"
                />
              ) : (
                <div className="w-24 h-24 rounded-full bg-[#0B2A5E] border-2 border-[#00A8FF]/50 flex items-center justify-center">
                  <User className="w-12 h-12 text-[#00A8FF]" />
                </div>
              )}
              <div className="text-center space-y-1">
                <div className="font-headline font-bold text-xl text-white">
                  {user.name || user.login}
                </div>
                <div className="font-mono text-xs text-[#00A8FF]">@{user.login}</div>
              </div>
              <div className="font-mono text-[10px] text-[#9AA7B8] flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-[#00E699]" />
                <span>GITHUB-CLEARED OPERATOR</span>
              </div>
            </div>
          </GlassPanel>

          {/* Profile Details */}
          <GlassPanel
            headerTitle="PROFILE DETAILS"
            headerCode="GITHUB_OAUTH"
            statusIndicator="ACTIVE"
          >
            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-start justify-between border-b border-[#17406E]/50 pb-2">
                <div className="flex items-center space-x-2 text-[#9AA7B8]">
                  <Github className="w-3.5 h-3.5" />
                  <span>GITHUB ID:</span>
                </div>
                <span className="text-[#EAF1F8] font-semibold">{user.github_id}</span>
              </div>
              <div className="flex items-start justify-between border-b border-[#17406E]/50 pb-2">
                <div className="flex items-center space-x-2 text-[#9AA7B8]">
                  <User className="w-3.5 h-3.5" />
                  <span>LOGIN:</span>
                </div>
                <span className="text-[#EAF1F8] font-semibold">@{user.login}</span>
              </div>
              <div className="flex items-start justify-between border-b border-[#17406E]/50 pb-2">
                <div className="flex items-center space-x-2 text-[#9AA7B8]">
                  <Mail className="w-3.5 h-3.5" />
                  <span>NAME:</span>
                </div>
                <span className="text-[#EAF1F8] font-semibold">{user.name || 'NOT SET'}</span>
              </div>
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2 text-[#9AA7B8]">
                  <Server className="w-3.5 h-3.5" />
                  <span>AUTH METHOD:</span>
                </div>
                <span className="text-[#EAF1F8] font-semibold">GITHUB OAUTH (SECURE)</span>
              </div>
            </div>
          </GlassPanel>

          {/* Access & Installations */}
          <GlassPanel
            headerTitle="CLEARANCE & INSTALLATIONS"
            headerCode="SCOPE"
            statusIndicator="ACTIVE"
          >
            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-start justify-between border-b border-[#17406E]/50 pb-2">
                <div className="flex items-center space-x-2 text-[#9AA7B8]">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>SESSION:</span>
                </div>
                <span className="text-[#00E699] font-semibold">AUTHENTICATED</span>
              </div>
              <div className="flex items-start justify-between border-b border-[#17406E]/50 pb-2">
                <div className="flex items-center space-x-2 text-[#9AA7B8]">
                  <Server className="w-3.5 h-3.5" />
                  <span>INSTALLATIONS:</span>
                </div>
                <span className="text-[#EAF1F8] font-semibold">{me?.installations ?? 0} ACTIVE</span>
              </div>
              <div className="pt-2">
                <div className="text-[10px] text-[#9AA7B8] mb-2">
                  INSTALLATION SCOPE MANAGED ON GITHUB APPS
                </div>
                <a
                  href={me?.install_url || '#'}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between p-2.5 bg-[#0B2A5E] border border-[#17406E] text-[#D9E1EA] hover:bg-[#1248A8] hover:text-white hover:border-[#D9E1EA]/50 transition-all group"
                >
                  <span className="font-mono text-[11px] tracking-widest">MANAGE GITHUB APP</span>
                  <ChevronRight className="w-4 h-4 text-[#00A8FF] group-hover:text-white" />
                </a>
              </div>
              <CyberButton
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => document.location.href = '/auth/logout'}
              >
                DISCONNECT OPERATOR SESSION
              </CyberButton>
            </div>
          </GlassPanel>
        </div>
      )}

      {!loading && !user && (
        <div className="p-6 text-center font-mono text-xs text-[#FF1E2D] space-y-4">
          <div>NO OPERATOR SESSION — CLEARANCE REQUIRED</div>
          <CyberButton
            variant="primary"
            size="sm"
            onClick={() => onNavigate('login')}
          >
            GITHUB SIGN IN
          </CyberButton>
        </div>
      )}
    </div>
  );
};