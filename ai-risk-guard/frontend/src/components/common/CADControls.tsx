import React from 'react';
import { ShieldCADState, CADViewAngle } from '../../types';
import { Eye, Layers, RotateCw, RefreshCw, Compass } from 'lucide-react';

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
  const [showAnglesMenu, setShowAnglesMenu] = React.useState(false);

  const angles: CADViewAngle[] = ['ISOMETRIC', 'FRONT', 'TOP', 'RIGHT', 'SECTION', 'EXPLODED'];

  return (
    <div className={`relative flex items-center space-x-1 p-1 bg-[#06101F]/90 backdrop-blur-md border border-[#1E3C5C] shadow-lg rounded-sm ${className}`}>
      {/* 6-VIEWS Dropdown */}
      <div className="relative">
        <button
          onClick={() => setShowAnglesMenu(!showAnglesMenu)}
          className={`flex items-center space-x-1.5 px-2.5 py-1 text-[11px] font-mono tracking-wider transition-all border ${
            showAnglesMenu
              ? 'bg-[#087BFF]/20 border-[#00CFFF] text-[#65E7FF]'
              : 'border-transparent text-[#B8C2CE] hover:text-white hover:bg-[#0F253E]'
          }`}
          title="Select CAD Projection Angle"
        >
          <Compass className="w-3.5 h-3.5 text-[#00CFFF]" />
          <span>{state.viewAngle}</span>
        </button>

        {showAnglesMenu && (
          <div className="absolute top-full left-0 mt-1 w-32 py-1 bg-[#030914] border border-[#1E3C5C] shadow-2xl z-50 font-mono text-[10px]">
            {angles.map((angle) => (
              <button
                key={angle}
                onClick={() => {
                  onChange({ viewAngle: angle });
                  setShowAnglesMenu(false);
                }}
                className={`w-full text-left px-3 py-1.5 transition-colors ${
                  state.viewAngle === angle
                    ? 'bg-[#087BFF]/30 text-[#00CFFF] font-semibold border-l-2 border-[#00CFFF]'
                    : 'text-[#8D9AAA] hover:text-white hover:bg-[#06101F]'
                }`}
              >
                {angle}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="w-[1px] h-4 bg-[#1E3C5C]" />

      {/* Wireframe Toggle */}
      <button
        onClick={() => onChange({ wireframe: !state.wireframe })}
        className={`flex items-center space-x-1 px-2.5 py-1 text-[11px] font-mono tracking-wider transition-all border ${
          state.wireframe
            ? 'bg-[#087BFF]/20 border-[#00CFFF] text-[#00CFFF]'
            : 'border-transparent text-[#8D9AAA] hover:text-white hover:bg-[#0F253E]'
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
            ? 'bg-[#087BFF]/20 border-[#00CFFF] text-[#00CFFF]'
            : 'border-transparent text-[#8D9AAA] hover:text-white hover:bg-[#0F253E]'
        }`}
        title="Toggle Continuous Inspection Rotation"
      >
        <RotateCw className={`w-3.5 h-3.5 ${state.autoRotate ? 'animate-spin' : ''}`} />
        <span className="hidden sm:inline">ROTATE</span>
      </button>

      <div className="w-[1px] h-4 bg-[#1E3C5C]" />

      {/* Reset View */}
      <button
        onClick={() => onChange({ viewAngle: 'ISOMETRIC', wireframe: false, autoRotate: true })}
        className="p-1 text-[#8D9AAA] hover:text-[#00CFFF] hover:bg-[#0F253E] transition-colors border border-transparent"
        title="Reset CAD View"
      >
        <RefreshCw className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
