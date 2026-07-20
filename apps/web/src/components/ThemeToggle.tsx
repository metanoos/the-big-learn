"use client";

// ThemeToggle: a binary Light ↔ Dark button. One compact icon in the NavBar
// keeps the bar chrome-free while still surfacing the current state via the
// glyph + tooltip. Mirrors the icon-button styling of the chapter header's
// ToneColorToggle so the two controls read as a family. Backed by lib/theme.ts;
// the actual <html class="dark"> side effect lives in useTheme, while this
// component only renders and dispatches the next preference.

import { useTheme } from "@/lib/theme";

export function ThemeToggle() {
  const [pref, setPref] = useTheme();
  const next = pref === "light" ? "dark" : "light";

  const label = `Theme: ${pref === "light" ? "Light" : "Dark"}`;
  const hint = `Click for ${next}`;

  return (
    <button
      type="button"
      onClick={() => setPref(next)}
      aria-label={`${label}. ${hint}`}
      title={`${label} — ${hint}`}
      className="flex min-h-11 min-w-11 items-center justify-center rounded p-1.5 text-stone-400 hover:text-stone-700 hover:bg-stone-100 dark:text-stone-500 dark:hover:text-stone-200 dark:hover:bg-stone-800 transition-colors"
    >
      {/* Show the glyph for the current state: a sun for light and a moon for
          dark. Stroke inherits currentColor so hover/active states recolor the
          glyph automatically. */}
      {pref === "light" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}
