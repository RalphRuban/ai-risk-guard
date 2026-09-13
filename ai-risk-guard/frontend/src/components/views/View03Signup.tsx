import React, { useState } from 'react';
import { Github, Shield, CheckCircle2 } from 'lucide-react';
import { getMe } from '../../api/client';
import { CyberButton } from '../common/CyberButton';
import { TacticalBracket } from '../common/TacticalBracket';
import { ViewId } from '../../types';

interface View03SignupProps {
  onSignupSuccess: () => void;
  onNavigate: (view: ViewId) => void;
}

export const View03Signup: React.FC<View03SignupProps> = ({ onSignupSuccess, onNavigate }) => {
  const [orgName, setOrgName] = useState('enterprise-secops');
  const [fetchError, setFetchError] = useState<string | null>(null);

  React.useEffect(() => {
    getMe()
      .then((me) => {
        if (me.authenticated) {
          onSignupSuccess();
        }
      })
      .catch(() => {
        setFetchError('Unable to reach the backend service. Please try again shortly.');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleContinue = () => {
    window.location.href = '/auth/login';
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 py-12">
      <div className="relative w-full max-w-lg bg-[#050B16] border border-[#17406E] p-6 sm:p-10 shadow-[0_0_50px_rgba(0,123,255,0.2)]">
        <TacticalBracket color="#00A8FF" size="lg" />

        <div className="text-center space-y-3 mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-[#007BFF]/20 border border-[#00A8FF]/60 rounded-sm mb-2">
            <Shield className="w-7 h-7 text-[#00A8FF]" />
          </div>
          <div className="font-mono text-[10px] text-[#00A8FF] tracking-widest">
            ORGANIZATION ONBOARDING CLEARANCE
          </div>
          <h2 className="font-headline font-black text-2xl sm:text-3xl text-white">
            Register Security Org
          </h2>
          <p className="font-mono text-xs text-[#9AA7B8] max-w-md mx-auto">
            Initialize organization-wide AST scanning, policy gateway gates, and container sandbox isolation.
          </p>
        </div>

        <div className="space-y-4 mb-8">
          <div className="p-3 bg-[#050B16] border border-[#17406E] space-y-1 font-mono text-xs">
            <span className="text-[#9AA7B8] text-[10px] block">ORGANIZATION DOMAIN / SLUG</span>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="bg-transparent border-none outline-none text-[#E4EBF3] w-full font-mono text-sm"
            />
          </div>

          <div className="p-3 bg-[#020B1A] border border-[#17406E] font-mono text-[11px] text-[#9AA7B8] space-y-1.5">
            <div className="text-white font-semibold">INITIALIZATION CHECKLIST:</div>
            <div className="flex items-center space-x-2 text-[10px]">
              <CheckCircle2 className="w-3 h-3 text-[#00E699]" />
              <span>Multi-Agent Mesh Deployment (6 Subsystems)</span>
            </div>
            <div className="flex items-center space-x-2 text-[10px]">
              <CheckCircle2 className="w-3 h-3 text-[#00E699]" />
              <span>Hardened Docker Sandbox Runtime Provisioning</span>
            </div>
            <div className="flex items-center space-x-2 text-[10px]">
              <CheckCircle2 className="w-3 h-3 text-[#00E699]" />
              <span>7-Factor Contextual Risk Calibration</span>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <CyberButton
            variant="primary"
            size="lg"
            className="w-full"
            icon={<Github className="w-4 h-4" />}
            onClick={handleContinue}
          >
            CONTINUE WITH GITHUB
          </CyberButton>

          {fetchError && (
            <div className="p-3 bg-[#7E1120]/20 border border-[#FF1E2D] text-[#FF1E2D] font-mono text-[11px] leading-relaxed">
              {fetchError}
            </div>
          )}

          <button
            onClick={() => onNavigate('login')}
            className="w-full py-2 text-center font-mono text-xs text-[#9AA7B8] hover:text-[#5BC9FF] transition-colors"
          >
            Already have an active clearance? <span className="underline text-[#00A8FF]">Authenticate Now</span>
          </button>
        </div>
      </div>
    </div>
  );
};
