/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary brand colors
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',  // Main primary
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Trading specific colors (legacy, kept for compatibility)
        profit: {
          light: '#22c55e',
          DEFAULT: '#16a34a',
          dark: '#15803d',
        },
        loss: {
          light: '#ef4444',
          DEFAULT: '#dc2626',
          dark: '#b91c1c',
        },
        // A-Share board colors
        board: {
          main: '#3b82f6',      // Main board - blue
          chinext: '#8b5cf6',   // ChiNext - purple
          star: '#f59e0b',      // STAR - orange
        },
        // Agent status colors
        agent: {
          active: '#10b981',    // Green
          inactive: '#6b7280',  // Gray
          error: '#ef4444',     // Red
          warning: '#f59e0b',   // Orange
        },
        // Risk level colors
        risk: {
          low: '#10b981',
          medium: '#f59e0b',
          high: '#ef4444',
          critical: '#dc2626',
        },
        // UI colors
        background: {
          DEFAULT: '#ffffff',
          secondary: '#f9fafb',
          dark: '#111827',
        },
        surface: {
          DEFAULT: '#ffffff',
          hover: '#f3f4f6',
          active: '#e5e7eb',
        },
        text: {
          primary: '#111827',
          secondary: '#6b7280',
          disabled: '#9ca3af',
          inverse: '#ffffff',
        },
        border: {
          DEFAULT: '#e5e7eb',
          focus: '#3b82f6',
          error: '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      },
    },
  },
  plugins: [],
}
