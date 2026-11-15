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
        background: "var(--fb-canvas)",
        surface: {
          DEFAULT: "var(--fb-stage)",
          card: "var(--fb-card-top)",
          container: "var(--fb-card-bottom)",
          low: "var(--fb-well)",
          lowest: "var(--fb-well-deep)",
          high: "var(--fb-obsidian)",
          highest: "var(--fb-obsidian-elevated)",
        },
        primary: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
          active: "#1e40af",
          container: "#1e3a8a",
          foreground: "#ffffff",
          tint: "#adc6ff",
        },
        secondary: {
          DEFAULT: "#059669",
          hover: "#047857",
          container: "rgba(16, 185, 129, 0.14)",
          foreground: "#065f46",
        },
        tertiary: {
          DEFAULT: "#d97706",
          container: "rgba(245, 158, 11, 0.14)",
          foreground: "#92400e",
        },
        danger: {
          DEFAULT: "#dc2626",
          container: "rgba(239, 68, 68, 0.14)",
          foreground: "#991b1b",
        },
        outline: {
          DEFAULT: "#78716c",
          variant: "var(--fb-hairline)",
          subtle: "var(--fb-hairline)",
          active: "rgba(217, 95, 43, 0.35)",
        },
        "on-surface": "var(--fb-ink)",
        "on-surface-variant": "var(--fb-ink-secondary)",
      },
      borderRadius: {
        DEFAULT: "8px",
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "18px",
        "2xl": "22px",
        full: "9999px",
      },
      fontFamily: {
        sans: ["Outfit", "Plus Jakarta Sans", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        heading: ["Plus Jakarta Sans", "Outfit", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
