import React from 'react';
import { HeroScene } from '../landing/HeroScene';
import { CommandCenterConsole } from '../landing/CommandCenterConsole';
import { WorkstationMatrixStrip } from '../landing/WorkstationMatrixStrip';
import { FinalCTA } from '../landing/FinalCTA';
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
        onOpenDocs={onOpenDocs}
      />

      {/* 02: Interactive Real Engineering Console Component (Scanner, Diff, Sandbox, Policy) */}
      <CommandCenterConsole onNavigate={onNavigate} />

      {/* 03: Direct Workstation Matrix Launch Strip */}
      <WorkstationMatrixStrip onNavigate={onNavigate} />

      {/* 04: Minimal Authoritative CTA */}
      <FinalCTA onNavigate={onNavigate} onOpenDocs={onOpenDocs} />
    </div>
  );
};
