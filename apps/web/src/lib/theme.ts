"use client";

import { useCallback, useEffect, useSyncExternalStore } from "react";

// Per-browser theme preference. Same shape as lib/settings.ts (localStorage +
// same-tab custom event + cross-tab `storage` sync) so all client-only prefs
// read the same way. The preference is either light or dark and is applied to
// <html>'s classList. Two code paths keep <html> in sync:
//   1. A blocking inline script in layout.tsx <head> runs before first paint,
//      so there's no flash of the wrong theme on load.
//   2. This hook's effect (below) re-applies on preference change, on same-tab
//      event, and on cross-tab storage sync. Idempotent, so overlapping with
//      the head script is harmless.

export type ThemePreference = "light" | "dark";

const KEY = "tbl:theme";
export const THEME_CHANGED_EVENT = "tbl:theme-changed";

// Read the stored preference. Anything missing/corrupt/malformed (including the
// former "system" value) falls back to light. SSR does the same so server markup
// matches the initial client render.
function readRaw(): ThemePreference {
  if (typeof window === "undefined") return "light";
  try {
    const v = window.localStorage.getItem(KEY);
    if (v === "light" || v === "dark") return v;
    return "light";
  } catch {
    return "light";
  }
}

function writeRaw(next: ThemePreference) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, next);
    // Same-tab notification — our listener below re-applies on this.
    window.dispatchEvent(new CustomEvent(THEME_CHANGED_EVENT));
  } catch {
    /* private storage disabled (incognito, quota) — fail quietly */
  }
}

// Apply the theme to <html>. Idempotent — safe to call repeatedly.
function applyTheme(theme: ThemePreference) {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("dark", theme === "dark");
}

function subscribe(onStoreChange: () => void) {
  const onStorage = (event: StorageEvent) => {
    if (event.key === KEY) onStoreChange();
  };
  window.addEventListener(THEME_CHANGED_EVENT, onStoreChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(THEME_CHANGED_EVENT, onStoreChange);
    window.removeEventListener("storage", onStorage);
  };
}

// useTheme: reactive read of the preference. Returns [pref, setPref].
// Also owns the <html> .dark class as a side effect, keeping it in sync with
// preference changes. SSR and first paint return "light" (the useState default)
// so markup matches between server and client; the saved value is applied after
// mount and, before paint, by the head script.
export function useTheme(): [ThemePreference, (next: ThemePreference) => void] {
  const pref = useSyncExternalStore(subscribe, readRaw, () => "light" as const);
  useEffect(() => applyTheme(pref), [pref]);

  const set = useCallback((next: ThemePreference) => writeRaw(next), []);
  return [pref, set];
}
