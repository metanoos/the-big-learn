import type { Config } from "tailwindcss";
export default {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class", // the .dark class is set by lib/theme.ts (and a pre-paint head script in layout.tsx)
  theme: {
    extend: {
      // Tradition accent palette — one muted color per tradition so the shelf
      // is scannable at a glance (gold/jade/pink/slate). Chosen from the
      // -700/-600 ramp so they read on both stone-50 and stone-950. The
      // canonical hex values live in src/lib/traditionColor.ts (used at runtime
      // via inline styles); this theme entry mirrors them as design tokens for
      // any future class-based usage (bg-tradition-confucian, etc.).
      colors: {
        tradition: {
          confucian: "#b45309", // amber-700 — gold
          daoist:    "#047857", // emerald-700 — jade
          buddhist:  "#be185d", // pink-700 — pink
          secular:   "#475569", // slate-600 — neutral
        },
      },
      fontFamily: {
        // Fraunces (var set on <html> by next/font in layout.tsx) leads the
        // Latin stack; CJK faces stay ahead of it so Chinese glyphs still pick
        // up Source Han / Noto Serif SC. Browser picks the first font that
        // has a given glyph, so this resolves correctly per-character.
        serif: [
          '"Source Han Serif"',
          '"Noto Serif SC"',
          '"Songti SC"',
          "var(--font-fraunces)",
          "Georgia",
          "serif",
        ],
        sans: ["system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
