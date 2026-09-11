import React, { useState } from 'react';
import { Github, Shield, Lock, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { getMe } from '../../api/client';
import { CyberButton } from '../common/CyberButton';
import { TacticalBracket } from '../common/TacticalBracket';
import { ViewId } from '../../types';

interface View02LoginProps {
  onLoginSuccess: () => void;
  onNavigate: (view: ViewId) => void;
}

export const View02Login: React.FC<View02LoginProps> = ({ onLoginSuccess, onNavigate }) => {
  const [initializing, setInitializing] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Detect OAuth error params (e.g. /?error=login_failed&reason=no_installations)
  // and detect a fresh session after callback redirect.
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const error = params.get('error');
    if (error === 'login_failed') {
      const reason = params.get('reason') || 'unknown';
      setAuthError(`GitHub OAuth failed (${reason}). Please retry.`);
    } else if (error === 'no_installations') {
      const installUrl = params.get('install_url') || '';
      setAuthError(
        installUrl
          ? 'No GitHub App installations found. Install the app and retry.'
          : 'No GitHub App installations found.'
      );
    }
    getMe()
      .then((me) => {
        if (me.authenticated) {
          onLoginSuccess();
        }
      })
      .catch(() => undefined)
      .finally(() => setInitializing(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAuth = () => {
    window.location.href = '/auth/login';
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 py-12">
      <div className="relative w-full max-w-lg bg-[#030914] border border-[#1E3C5C] p-6 sm:p-10 shadow-[0_0_50px_rgba(8,123,255,0.2)]">
        <TacticalBracket color="#00CFFF" size="lg" />

        {/* Top Header */}
        <div className="text-center space-y-3 mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-[#087BFF]/20 border border-[#00CFFF]/60 rounded-sm mb-2">
            <Github className="w-7 h-7 text-[#00CFFF]" />
          </div>
          <div className="font-mono text-[10px] text-[#00CFFF] tracking-widest">
            SECURITY PROTOCOL: ARG-OAUTH-GATE
          </div>
          <h2 className="font-headline font-black text-2xl sm:text-3xl text-white">
            GitHub Operator Gateway
          </h2>
          <p className="font-mono text-xs text-[#8D9AAA] max-w-md mx-auto">
            Authorize enterprise security operator clearance via single-provider GitHub OAuth token clearance.
          </p>
        </div>

        {/* Operator Preset Input */}
        <div className="space-y-4 mb-8">
          <div className="p-3 bg-[#06101F] border border-[#1E3C5C] space-y-1.5 font-mono text-xs">
            <span className="text-[#8D9AAA] text-[10px] block">OPERATOR IDENTITY HANDLE</span>
            <div className="flex items-center space-x-2 text-white font-semibold">
              <span className="text-[#00CFFF]">@</span>
              <span className="bg-transparent text-[#F1F5F9] w-full font-mono">your-github-username</span>
            </div>
          </div>

          {/* Requested Scopes */}
          <div className="p-3 bg-[#02050B] border border-[#1E3C5C] font-mono text-[11px] text-[#8D9AAA] space-y-2">
            <div className="text-white font-semibold flex items-center justify-between">
              <span>REQUESTED PERMISSIONS MANIFEST</span>
              <span className="text-[#00E699] text-[10px]">READ/WRITE</span>
            </div>
            <ul className="space-y-1 text-[10px]">
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="w-3 h-3 text-[#00CFFF]" />
                <span>Pull Request Scanning & AST Comment Ingestion</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="w-3 h-3 text-[#00CFFF]" />
                <span>Automated NodeTransformer Patch Commits</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="w-3 h-3 text-[#00CFFF]" />
                <span>Hardened Docker Sandbox Webhook Dispatch</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="w-3 h-3 text-[#00CFFF]" />
                <span>Enterprise Security Gate Enforcement</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <CyberButton
            variant="primary"
            size="lg"
            className="w-full"
            loading={initializing}
            icon={<Github className="w-4 h-4" />}
            onClick={handleAuth}
          >
            {initializing ? 'VERIFYING SESSION...' : 'AUTHENTICATE WITH GITHUB'}
          </CyberButton>

          {authError && (
            <div className="p-3 bg-[#8F1424]/20 border border-[#FF304F] text-[#FF304F] font-mono text-[11px] leading-relaxed">
              {authError}
            </div>
          )}

          <CyberButton
            variant="outline"
            size="md"
            className="w-full"
            icon={<ArrowLeft className="w-3.5 h-3.5" />}
            onClick={() => onNavigate('landing')}
          >
            RETURN TO PLATFORM
          </CyberButton>
        </div>

        <div className="mt-6 text-center font-mono text-[10px] text-[#8D9AAA]">
          RESTRICTED TO REPOSITORY COLLABORATORS WITH SECOPS PRIVILEGES
        </div>
      </div>
    </div>
  );
};
