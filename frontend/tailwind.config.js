/** @type {import('tailwind-css').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Strict Red, Black, White palette ONLY
        brandRed: '#dc2626', // Primary Red
        brandRedHover: '#b91c1c',
        brandRedBright: '#ef4444',
        brandRedLight: '#fee2e2',
        
        // Dark theme tokens
        darkBg: '#050505',
        darkSurface: '#0f0f0f',
        darkSurface2: '#181818',
        darkBorder: '#262626',
        darkBorderBold: '#dc2626',
        
        // Light theme tokens
        lightBg: '#fafafa',
        lightSurface: '#ffffff',
        lightSurface2: '#f4f4f5',
        lightBorder: '#18181b',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Courier New', 'monospace'],
      },
      boxShadow: {
        'brutal-sm': '3px 3px 0px 0px #000000',
        'brutal': '5px 5px 0px 0px #000000',
        'brutal-lg': '7px 7px 0px 0px #000000',
        'brutal-red': '5px 5px 0px 0px #dc2626',
        'brutal-white': '5px 5px 0px 0px #ffffff',
        'brutal-red-lg': '7px 7px 0px 0px #dc2626',
      }
    },
  },
  plugins: [],
}
