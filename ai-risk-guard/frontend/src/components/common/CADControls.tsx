import React from 'react';
import { ShieldCADState, CADViewAngle } from '../../types';
import { Layers, RotateCw, RefreshCw, Compass, Settings2 } from 'lucide-react';

interface CADControlsProps {
  state: ShieldCADState;
  onChange: (updates: Partial<ShieldCADState>) => void;
  className?: string;
}

export const CADControls: React.FC<CADControlsProps> = ({
  state,
  onChange,
  className = ''
}) => {
  const [expanded, setExpanded] = React.useState(false);
  const [showAnglesMenu, setShowAnglesMenu] = React.useState(false);

  const angles: CADViewAngle[] = ['ISOMETRIC', 'FRONT', 'TOP', 'RIGHT', 'SECTION', 'EXPLODED'];

  return (
    <div className={`relative flex items-center space-x-1 p-1 bg-[#050B16]/90 backdrop-blur-md border border-[#17406E] shadow-lg rounded-sm ${className}`}>
      {/* Collapsed: Small Chip Toggle */}
      {!expanded ? (
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center space-x-1.5 px-2 py-1.5 text-[10px] font-mono tracking-widest border border-[#17406E] text-[#C2CDD9] hover:text-white hover:border-[#00A8FF]/60 hover:bg-[#0B2A5E] transition-all"
          title="Open CAD Controls"
        >
          <Settings2 className="w-3.5 h-3.5 text-[#00A8FF]" />
          <span>CAD</span>
        </button>
      ) : (
        <>
      {/* 6-VIEWS Dropdown */}
      <div className="relative">
        <button
          onClick={() => setShowAnglesMenu(!showAnglesMenu)}
          className={`flex items-center space-x-1.5 px-2.5 py-1 text-[11px] font-mono tracking-wider transition-all border ${
            showAnglesMenu
              ? 'bg-[#007BFF]/20 border-[#00A8FF] text-[#5BC9FF]'
              : 'border-transparent text-[#C2CDD9] hover:text-white hover:bg-[#0B2A5E]'
          }`}
          title="Select CAD Projection Angle"
        >
          <Compass className="w-3.5 h-3.5 text-[#00A8FF]" />
          <span>{state.viewAngle}</span>
        </button>

        {showAnglesMenu && (
          <div className="absolute top-full left-0 mt-1 w-32 py-1 bg-[#050B16] border border-[#17406E] shadow-2xl z-50 font-mono text-[10px]">
            {angles.map((angle) => (
              <button
                key={angle}
                onClick={() => {
                  onChange({ viewAngle: angle });
                  setShowAnglesMenu(false);
                }}
                className={`w-full text-left px-3 py-1.5 transition-colors ${
                  state.viewAngle === angle
                    ? 'bg-[#007BFF]/30 text-[#00A8FF] font-semibold border-l-2 border-[#00A8FF]'
                    : 'text-[#9AA7B8] hover:text-white hover:bg-[#050B16]'
                }`}
              >
                {angle}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="w-[1px] h-4 bg-[#17406E]" />

      {/* Wireframe Toggle */}
      <button
        onClick={() => onChange({ wireframe: !state.wireframe })}
        className={`flex items-center space-x-1 px-2.5 py-1 text-[11px] font-mono tracking-wider transition-all border ${
          state.wireframe
            ? 'bg-[#007BFF]/20 border-[#00A8FF] text-[#00A8FF]'
            : 'border-transparent text-[#9AA7B8] hover:text-white hover:bg-[#0B2A5E]'
        }`}
        title="Toggle Wireframe CAD Mode"
      >
        <Layers className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">WIREFRAME</span>
      </button>

      {/* Auto-Rotate Toggle */}
      <button
        onClick={() => onChange({ autoRotate: !state.autoRotate })}
        className={`flex items-center space-x-1 px-2.5 py-1 text-[11px] font-mono tracking-wider transition-all border ${
          state.autoRotate
            ? 'bg-[#007BFF]/20 border-[#00A8FF] text-[#00A8FF]'
            : 'border-transparent text-[#9AA7B8] hover:text-white hover:bg-[#0B2A5E]'
        }`}
        title="Toggle Continuous Inspection Rotation"
      >
        <RotateCw className={`w-3.5 h-3.5 ${state.autoRotate ? 'animate-spin' : ''}`} />
        <span className="hidden sm:inline">ROTATE</span>
      </button>

      <div className="w-[1px] h-4 bg-[#17406E]" />

      {/* Reset View */}
      <button
        onClick={() => onChange({ viewAngle: 'ISOMETRIC', wireframe: false, autoRotate: true })}
        className="p-1 text-[#9AA7B8] hover:text-[#00A8FF] hover:bg-[#0B2A5E] transition-colors border border-transparent"
        title="Reset CAD View"
      >
        <RefreshCw className="w-3.5 h-3.5" />
      </button>

      {/* Collapse Toggle */}
      <button
        onClick={() => setExpanded(false)}
        className="hidden sm:block p-1 text-[#9AA7B8] hover:text-[#FF1E2D] hover:bg-[#0B2A5E] transition-colors border border-transparent"
        title="Collapse CAD Controls"
      >
        <Settings2 className="w-3.5 h-3.5" />
      </button>
        </>
      )}
    </div>
  );
};
