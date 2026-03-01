/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'media',
  theme: {
    extend: {
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
        'wave': 'wave 1.2s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'flash': 'flash 0.7s ease-out',
        'gradient': 'gradient 10s ease infinite',
      },
      keyframes: {
        wave: {
          '0%, 100%': { transform: 'scaleY(0.5)' },
          '50%': { transform: 'scaleY(1)' },
        },
        'glow-pulse': {
          '0%, 100%': { 
            opacity: '0.7',
            transform: 'scale(1)'
          },
          '50%': { 
            opacity: '1',
            transform: 'scale(1.05)'
          },
        },
        flash: {
          '0%': { opacity: '0' },
          '25%': { opacity: '0.8' },
          '50%': { opacity: '0.3' },
          '100%': { opacity: '0' },
        },
        gradient: {
          '0%': { backgroundPosition: '0% 50%' },
          '25%': { backgroundPosition: '50% 100%' },
          '50%': { backgroundPosition: '100% 50%' },
          '75%': { backgroundPosition: '50% 0%' },
          '100%': { backgroundPosition: '0% 50%' },
        }
      },
      backgroundColor: {
        'blue-600/10': 'rgba(37, 99, 235, 0.1)',
        'blue-600/20': 'rgba(37, 99, 235, 0.2)',
        'indigo-600/10': 'rgba(79, 70, 229, 0.1)',
        'gray-800/40': 'rgba(31, 41, 55, 0.4)',
        'gray-800/50': 'rgba(31, 41, 55, 0.5)',
        'blue-900/20': 'rgba(30, 58, 138, 0.2)',
        'white/20': 'rgba(255, 255, 255, 0.2)',
        'white/30': 'rgba(255, 255, 255, 0.3)',
      },
      backdropBlur: {
        xs: '2px',
      },
      borderColor: {
        'gray-700/50': 'rgba(55, 65, 81, 0.5)',
        'blue-800/50': 'rgba(30, 64, 175, 0.5)',
        'blue-500/50': 'rgba(59, 130, 246, 0.5)',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(59, 130, 246, 0.5)',
      },
    },
  },
  plugins: [],
} 