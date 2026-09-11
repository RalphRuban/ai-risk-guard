import React from 'react';

interface CyberButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'threat' | 'ice' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  badge?: string;
  loading?: boolean;
}

export const CyberButton: React.FC<CyberButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  badge,
  loading = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = "relative inline-flex items-center justify-center font-mono font-medium uppercase tracking-wider select-none transition-all duration-150 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none group overflow-hidden border";
  
  const sizeStyles = {
    sm: "text-xs px-3 py-1.5 gap-1.5",
    md: "text-xs px-5 py-2.5 gap-2",
    lg: "text-sm px-7 py-3 gap-2.5"
  };

  const variantStyles = {
    primary: "bg-[#DC2626] hover:bg-[#B91C1C] text-white border-[#FF2A4B]/80 hover:border-[#FF2A4B] shadow-[0_0_20px_rgba(255,42,75,0.45)] hover:shadow-[0_0_30px_rgba(255,42,75,0.65)]",
    secondary: "bg-[#0B2556] hover:bg-[#12356B] text-[#E2E8F0] hover:text-white border-[#CBD5E1]/40 hover:border-[#CBD5E1] shadow-[0_0_15px_rgba(203,213,225,0.12)] hover:shadow-[0_0_25px_rgba(203,213,225,0.25)]",
    ice: "bg-[#061533] hover:bg-[#0B2556] text-[#CBD5E1] border-[#CBD5E1]/50 hover:border-white shadow-[0_0_15px_rgba(203,213,225,0.2)]",
    threat: "bg-[#991B1B] hover:bg-[#DC2626] text-white border-[#FF2A4B] shadow-[0_0_20px_rgba(255,42,75,0.5)]",
    outline: "bg-transparent hover:bg-[#0B2556]/80 text-[#CBD5E1] hover:text-white border-[#184384] hover:border-[#CBD5E1]"
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {/* Corner notch accent */}
      <span className="absolute top-0 right-0 w-1.5 h-1.5 border-t border-r border-white/40 group-hover:border-white transition-colors" />
      <span className="absolute bottom-0 left-0 w-1.5 h-1.5 border-b border-l border-white/40 group-hover:border-white transition-colors" />

      {loading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        <>
          {icon && iconPosition === 'left' && <span className="shrink-0">{icon}</span>}
          <span>{children}</span>
          {badge && (
            <span className="ml-1.5 px-1.5 py-0.5 text-[10px] bg-white/10 rounded font-mono text-[#65E7FF] border border-[#00CFFF]/30">
              {badge}
            </span>
          )}
          {icon && iconPosition === 'right' && <span className="shrink-0">{icon}</span>}
        </>
      )}
    </button>
  );
};
