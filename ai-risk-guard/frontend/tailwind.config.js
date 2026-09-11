/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        cyber: {
          // 80% Navy Blue Hierarchy (Void, Structure, Panels, Accents)
          navyVoid: '#020716',
          navyDark: '#030C22',
          navyPanel: '#061533',
          navyDeep: '#081D45',
          navyStructure: '#0B2556',
          navyBorder: '#184384',
          navyLight: '#245FB0',
          navyElectric: '#1E64D4',
          
          // 10% Red (Tactical Cyber Threat, Alarms, Energy Lasers)
          threatRed: '#FF2A4B',
          rubyCore: '#DC2626',
          darkRed: '#991B1B',
          crimsonAlert: '#E11D48',
          dimRed: '#540D17',

          // 10% Silver (Aerospace Titanium, Chrome Highlights, Metallic Typography)
          metalWhite: '#F8FAFC',
          metalLight: '#E2E8F0',
          metalSilver: '#CBD5E1',
          metalMuted: '#94A3B8',
          metalDark: '#64748B',

          // Compatibility keys
          bgVoid: '#020716',
          bgDark: '#030C22',
          bgPanel: '#061533',
          structureDark: '#081D45',
          structureBase: '#0B2556',
          gunmetal: '#0E2F6B',
          steel: '#184384',
          electricBlue: '#1E64D4',
          cyberBlue: '#1248A8',
          energyCyan: '#FF2A4B', // routed to Threat Red
          iceBlue: '#CBD5E1',    // routed to Silver
          successGreen: '#00E699'
        }
      },
      fontFamily: {
        headline: ['Orbitron', 'Syne', 'sans-serif'],
        display: ['Orbitron', 'sans-serif'],
        syne: ['Syne', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['"Plus Jakarta Sans"', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif']
      },
      boxShadow: {
        'red-glow': '0 0 25px rgba(255, 42, 75, 0.35)',
        'threat-glow': '0 0 30px rgba(255, 42, 75, 0.45)',
        'silver-glow': '0 0 20px rgba(203, 213, 225, 0.25)',
        'navy-glow': '0 0 30px rgba(30, 100, 212, 0.25)',
        'tactical-inset': 'inset 0 1px 0 rgba(226, 232, 240, 0.15), inset 0 0 20px rgba(2, 7, 22, 0.7)',
        'glass-card': '0 16px 40px -10px rgba(2, 7, 22, 0.8), 0 0 1px 1px rgba(203, 213, 225, 0.2)',
        'glass-floating': '0 20px 50px -10px rgba(2, 7, 22, 0.85), 0 0 30px 1px rgba(255, 42, 75, 0.18)'
      },
      keyframes: {
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' }
        },
        'scanline-sweep': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(1000%)' }
        },
        'float-gentle': {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '50%': { transform: 'translateY(-8px) rotate(0.4deg)' }
        },
        'float-delayed': {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '50%': { transform: 'translateY(-10px) rotate(-0.4deg)' }
        },
        'hang-swing': {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '50%': { transform: 'rotate(0.6deg)' }
        },
        'shimmer-pass': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(200%)' }
        }
      },
      animation: {
        'pulse-subtle': 'pulse-subtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scanline': 'scanline-sweep 8s linear infinite',
        'float': 'float-gentle 5s ease-in-out infinite',
        'float-delayed': 'float-delayed 6s ease-in-out 1.5s infinite',
        'hang': 'hang-swing 7s ease-in-out infinite',
        'shimmer': 'shimmer-pass 2.5s ease-in-out infinite'
      }
    },
  },
  plugins: [],
}
