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
        background: 'var(--bg-main)',
        panel: 'var(--bg-card)',
        sidebar: 'var(--bg-sidebar)',
        header: 'var(--bg-header)',
        panelHover: 'var(--bg-hover)',
        border: 'var(--border)',
        borderStrong: 'var(--border-strong)',
        accent: 'var(--accent)',
        accentHover: 'var(--accent-hover)',
        success: 'var(--success)',
        warning: 'var(--warning)',
        danger: 'var(--danger)',
        // Text mapping
        white: 'var(--text-primary)',
        primary: 'var(--text-primary)',
        secondary: 'var(--text-secondary)',
        muted: 'var(--text-muted)',
        // Override grays to force them to respect the theme
        gray: {
          100: 'var(--text-primary)',
          200: 'var(--text-primary)',
          300: 'var(--text-secondary)',
          400: 'var(--text-secondary)',
          500: 'var(--text-muted)',
          600: 'var(--text-muted)',
          700: 'var(--border)',
          800: 'var(--bg-card)',
          900: 'var(--bg-main)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: 'var(--card-shadow)',
      }
    },
  },
  plugins: [],
}