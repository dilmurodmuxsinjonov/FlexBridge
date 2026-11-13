import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#09090b",
        surface: {
          DEFAULT: "#121214",
          card: "#121214",
          container: "#18181b",
          low: "#141416",
          lowest: "#09090b",
          high: "#202024",
          highest: "#27272a",
        },
        primary: {
          DEFAULT: "#3b82f6",
          hover: "#2563eb",
          active: "#1d4ed8",
          container: "#1e3a8a",
          foreground: "#ffffff",
          tint: "#adc6ff",
        },
        secondary: {
          DEFAULT: "#10b981",
          hover: "#059669",
          container: "rgba(16, 185, 129, 0.15)",
          foreground: "#6ffbbe",
        },
        tertiary: {
          DEFAULT: "#f59e0b",
          container: "rgba(245, 158, 11, 0.15)",
          foreground: "#ffdcc6",
        },
        danger: {
          DEFAULT: "#ef4444",
          container: "rgba(239, 68, 68, 0.15)",
          foreground: "#ffdad6",
        },
        outline: {
          DEFAULT: "#71717a",
          variant: "rgba(255, 255, 255, 0.08)",
          subtle: "rgba(255, 255, 255, 0.05)",
          active: "rgba(255, 255, 255, 0.22)",
        },
        "on-surface": "#f4f4f5",
        "on-surface-variant": "#a1a1aa",
      },
      borderRadius: {
        DEFAULT: "4px",
        sm: "2px",
        md: "6px",
        lg: "8px",
        xl: "12px",
        full: "9999px",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        heading: ["Plus Jakarta Sans", "Inter", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "monospace"],
      },
      spacing: {
        "space-xs": "0.25rem",
        "space-sm": "0.5rem",
        "space-md": "0.75rem",
        "space-lg": "1.25rem",
        "space-xl": "2rem",
        "margin-md": "1.5rem",
        "margin-lg": "2.5rem",
      },
    },
  },
  plugins: [],
};

export default config;
