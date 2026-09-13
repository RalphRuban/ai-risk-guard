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
          navyVoid: '#020B1A',
          navyDark: '#050B16',
          navyPanel: '#071A2E',
          navyDeep: '#0B2A5E',
          navyStructure: '#0B2A5E',
          navyBorder: '#17406E',
          navyLight: '#0B5ED7',
          navyElectric: '#007BFF',
          
          // 10% Red (Tactical Cyber Threat, Alarms, Energy Lasers)
          threatRed: '#FF1E2D',
          rubyCore: '#E31424',
          darkRed: '#A01D29',
          crimsonAlert: '#E11D48',
          dimRed: '#5A0E16',

          // 10% Silver (Aerospace Titanium, Chrome Highlights, Metallic Typography)
          metalWhite: '#EAF1F8',
          metalSheen: '#F0F5FA',
          metalLight: '#DEE7F0',
          metalSilver: '#D9E1EA',
          metalSteel: '#C2CDD9',
          metalMuted: '#A7B4C4',
          metalDark: '#76879D',

          // Compatibility keys
          bgVoid: '#020B1A',
          bgDark: '#050B16',
          bgPanel: '#071A2E',
          structureDark: '#0B2A5E',
          structureBase: '#0B2A5E',
          gunmetal: '#1248A8',
          steel: '#17406E',
          electricBlue: '#007BFF',
          cyberBlue: '#1248A8',
          energyCyan: '#FF1E2D', // routed to Threat Red
          iceBlue: '#D9E1EA',    // routed to Silver
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
        'red-glow': '0 0 25px rgba(255, 30, 45, 0.35)',
        'threat-glow': '0 0 30px rgba(255, 30, 45, 0.45)',
        'silver-glow': '0 0 20px rgba(217, 225, 234, 0.25)',
        'silver-glow-strong': '0 0 25px rgba(217, 225, 234, 0.4)',
        'silver-rim': 'inset 0 1px 0 rgba(217, 225, 234, 0.3)',
        'navy-glow': '0 0 30px rgba(0, 123, 255, 0.25)',
        'tactical-inset': 'inset 0 1px 0 rgba(222, 231, 240, 0.15), inset 0 0 20px rgba(2, 11, 26, 0.7)',
        'glass-card': '0 16px 40px -10px rgba(2, 11, 26, 0.8), 0 0 1px 1px rgba(217, 225, 234, 0.2)',
        'glass-floating': '0 20px 50px -10px rgba(2, 11, 26, 0.85), 0 0 30px 1px rgba(255, 30, 45, 0.18)'
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
