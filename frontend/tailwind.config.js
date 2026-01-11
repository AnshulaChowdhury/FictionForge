/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ['Gotham', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'sans-serif'],
        serif: ['Georgia', 'Times New Roman', 'serif'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      boxShadow: {
        'subtle': '0 1px 2px hsla(var(--shadow-color, 0 0% 50%), 0.04)',
        'soft': '0 2px 8px hsla(var(--shadow-color, 0 0% 50%), 0.06)',
        'medium': '0 4px 12px hsla(var(--shadow-color, 0 0% 50%), 0.08)',
        'elevated': '0 8px 24px hsla(var(--shadow-color, 0 0% 50%), 0.12)',
      },
      transitionDuration: {
        'fast': '150ms',
        'normal': '200ms',
        'slow': '300ms',
        'slower': '500ms',
      },
      transitionTimingFunction: {
        'smooth': 'cubic-bezier(0.22, 1, 0.36, 1)',
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'fade-up': 'fadeUp 0.3s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'fade-down': 'fadeDown 0.3s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'scale-in': 'scaleIn 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
        'pop': 'pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
        'celebrate': 'celebrate 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s infinite',
        'pulse-glow': 'pulse-glow 2s infinite',
        'breathe': 'breathe 3s ease-in-out infinite',
        'spin': 'spin 1s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        pop: {
          '0%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
          '100%': { transform: 'scale(1)' },
        },
        celebrate: {
          '0%': { transform: 'scale(1)' },
          '25%': { transform: 'scale(1.02) rotate(-1deg)' },
          '50%': { transform: 'scale(1.04)' },
          '75%': { transform: 'scale(1.02) rotate(1deg)' },
          '100%': { transform: 'scale(1)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 hsla(var(--accent), 0.4)' },
          '50%': { boxShadow: '0 0 0 8px hsla(var(--accent), 0)' },
        },
        breathe: {
          '0%, 100%': { boxShadow: '0 0 0 2px hsla(var(--accent), 0.1)' },
          '50%': { boxShadow: '0 0 0 4px hsla(var(--accent), 0.2)' },
        },
      },
    },
  },
  plugins: [],
}
