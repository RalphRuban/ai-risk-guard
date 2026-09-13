import React from 'react';

interface TacticalBracketProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  color?: string;
}

export const TacticalBracket: React.FC<TacticalBracketProps> = ({
  className = '',
  size = 'md',
  color = '#D9E1EA'
}) => {
  const sizeMap = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4'
  };

  return (
    <div className={`pointer-events-none absolute inset-0 ${className}`}>
      {/* Top Left */}
      <span 
        className={`absolute top-0 left-0 ${sizeMap[size]} border-t border-l`} 
        style={{ borderColor: color }} 
      />
      {/* Top Right */}
      <span 
        className={`absolute top-0 right-0 ${sizeMap[size]} border-t border-r`} 
        style={{ borderColor: color }} 
      />
      {/* Bottom Left */}
      <span 
        className={`absolute bottom-0 left-0 ${sizeMap[size]} border-b border-l`} 
        style={{ borderColor: color }} 
      />
      {/* Bottom Right */}
      <span 
        className={`absolute bottom-0 right-0 ${sizeMap[size]} border-b border-r`} 
        style={{ borderColor: color }} 
      />
    </div>
  );
};
