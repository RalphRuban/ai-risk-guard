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
    primary: "bg-[#E31424] hover:bg-[#C41724] text-white border-[#FF1E2D]/80 hover:border-[#FF1E2D] shadow-[0_0_20px_rgba(255,30,45,0.45)] hover:shadow-[0_0_30px_rgba(255,30,45,0.65)]",
    secondary: "bg-[#0B2A5E] hover:bg-[#1248A8] text-[#DEE7F0] hover:text-white border-[#D9E1EA]/40 hover:border-[#F0F5FA] shadow-[0_0_15px_rgba(217,225,234,0.12)] hover:shadow-[0_0_25px_rgba(217,225,234,0.35)]",
    ice: "bg-[#071A2E] hover:bg-[#0B2A5E] text-[#D9E1EA] border-[#C2CDD9]/60 hover:border-[#F0F5FA] shadow-[0_0_15px_rgba(217,225,234,0.2)] hover:shadow-[0_0_20px_rgba(217,225,234,0.35)]",
    threat: "bg-[#A01D29] hover:bg-[#E31424] text-white border-[#FF1E2D] shadow-[0_0_20px_rgba(255,30,45,0.5)]",
    outline: "bg-transparent hover:bg-[#0B2A5E]/80 text-[#D9E1EA] hover:text-white border-[#17406E] hover:border-[#D9E1EA] hover:shadow-[0_0_18px_rgba(217,225,234,0.25)]"
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
            <span className="ml-1.5 px-1.5 py-0.5 text-[10px] bg-[#D9E1EA]/15 rounded font-mono text-[#EAF1F8] border border-[#D9E1EA]/50 shadow-[0_0_8px_rgba(217,225,234,0.2)]">
              {badge}
            </span>
          )}
          {icon && iconPosition === 'right' && <span className="shrink-0">{icon}</span>}
        </>
      )}
    </button>
  );
};
