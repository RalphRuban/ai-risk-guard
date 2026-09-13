import React from 'react';
import { HeroScene } from '../landing/HeroScene';
import { CommandCenterConsole } from '../landing/CommandCenterConsole';
import { WorkstationMatrixStrip } from '../landing/WorkstationMatrixStrip';
import { FinalCTA } from '../landing/FinalCTA';
import FadeContent from '../bits/Animations/FadeContent/FadeContent';
import { ShieldCADState, ViewId } from '../../types';

interface View01LandingProps {
  onNavigate: (view: ViewId) => void;
  scrollProgress: number;
  cadState: ShieldCADState;
  onCADChange: (updates: Partial<ShieldCADState>) => void;
  onOpenDocs: () => void;
}

export const View01Landing: React.FC<View01LandingProps> = ({
  onNavigate,
  scrollProgress,
  cadState,
  onCADChange,
  onOpenDocs
}) => {
  return (
    <div className="relative w-full overflow-hidden space-y-4">
      {/* 01: Hero Scene (Prominent 3D Tactical Shield + CAD Controls + Live Telemetry) */}
      <HeroScene
        onNavigate={onNavigate}
        scrollProgress={scrollProgress}
        cadState={cadState}
        onCADChange={onCADChange}
      />

      {/* 02: Interactive Real Engineering Console Component (Scanner, Diff, Sandbox, Policy) */}
      <FadeContent blur threshold={0.12}>
        <CommandCenterConsole onNavigate={onNavigate} />
      </FadeContent>

      {/* 03: Direct Workstation Matrix Launch Strip */}
      <FadeContent blur delay={200} threshold={0.1}>
        <WorkstationMatrixStrip onNavigate={onNavigate} />
      </FadeContent>

      {/* 04: Minimal Authoritative CTA */}
      <FadeContent blur delay={300} threshold={0.12}>
        <FinalCTA onNavigate={onNavigate} onOpenDocs={onOpenDocs} />
      </FadeContent>
    </div>
  );
};
