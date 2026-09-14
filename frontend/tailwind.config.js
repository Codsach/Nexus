/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",

        // Nexus specific light theme palette (Emerald/Teal & Zinc/Slate, NO blue/purple)
        nexus: {
          bg: '#f8fafc',
          surface: '#ffffff',
          card: '#ffffff',
          border: '#e2e8f0',
          accent: '#059669', // Emerald 600
          'accent-glow': '#10b981', // Emerald 500
          'accent-subtle': '#ecfdf5', // Emerald 50
          muted: '#94a3b8',
          text: '#0f172a',
          'text-muted': '#475569',
        },
        // Status colors
        status: {
          resolved: '#059669',
          escalated: '#d97706',
          investigating: '#0d9488',
          open: '#64748b',
        },
        // Urgency
        urgency: {
          critical: '#e11d48',
          high: '#ea580c',
          medium: '#d97706',
          low: '#059669',
        },
        // Sentiment
        sentiment: {
          'very-negative': '#e11d48',
          negative: '#ea580c',
          neutral: '#64748b',
          positive: '#059669',
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'trace-appear': 'traceAppear 0.4s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0px rgba(16, 185, 129, 0)' },
          '50%': { boxShadow: '0 0 12px rgba(16, 185, 129, 0.3)' },
        },
        traceAppear: {
          '0%': { transform: 'translateX(-10px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
      backgroundImage: {
        'gradient-nexus': 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
        'gradient-card': 'linear-gradient(145deg, #ffffff 0%, #f8fafc 100%)',
        'gradient-accent': 'linear-gradient(135deg, #059669 0%, #0d9488 100%)',
      },
    },
  },
  plugins: [],
}
