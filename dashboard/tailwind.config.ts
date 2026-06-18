import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "var(--ink)",
          soft: "var(--ink-soft)",
          2: "var(--ink-2)",
        },
        cream: "var(--white)",
        paper: {
          DEFAULT: "var(--paper)",
          ink: "var(--paper-ink)",
        },
        mute: "var(--mute)",
        faint: "var(--faint)",
        ghost: "var(--ghost)",
        hair: "var(--hair)",
        pos: "var(--pos)",
        neg: "var(--neg)",
        accent: "var(--accent)",
      },
      fontFamily: {
        serif: ["var(--serif)"],
        sans: ["var(--sans)"],
        mono: ["var(--mono)"],
        display: ["var(--display)"],
      },
      borderRadius: {
        card: "12px",
      },
      boxShadow: {
        card: "0 40px 90px -40px rgba(0,0,0,0.8)",
      },
    },
  },
  plugins: [],
};

export default config;
