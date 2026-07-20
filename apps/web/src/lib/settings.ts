"use client";

import { useCallback, useSyncExternalStore } from "react";

// Per-browser reader-display settings. Each setting mirrors the localStorage +
// custom-event pattern in lib/progress.ts so every client-only pref shares one
// shape: SSR-safe accessors, defensive parsing, same-tab broadcast + cross-tab
// storage sync.
//
// Settings today:
//  - tone-colored pinyin (default off) — opt-in coloring of <rt> by tone.
//  - pinyin annotations  (default on)  — show/hide the ruby pinyin above chars.
//  - english translation (default on)  — show/hide the canonical English rows.
//
// The toggle(s) live in the chapter header (see ToneColorToggle / PinyinToggle /
// EnglishToggle); the values are read reactively inside the reading-surface
// components (AnnotatedText, LineView) so the display updates the moment a flip
// lands, with no prop drilling through ChapterReader.

// --- generic boolean-setting factory --------------------------------------
// One localStorage-backed boolean pref: read with a default, write + broadcast
// a same-tab event, and rely on the cross-tab `storage` event elsewhere. Every
// reader pref is thus identical in shape — a new pref is one factory call. The
// `defaultValue` is what absent/corrupt storage falls back to AND what SSR +
// first paint render to, so server markup matches the initial client render
// (no hydration flash for the common case); the stored value — which may
// differ — is applied after mount.
function makeBooleanSetting(
  key: string,
  eventName: string,
  defaultValue: boolean,
) {
  function readRaw(): boolean {
    if (typeof window === "undefined") return defaultValue;
    try {
      const v = window.localStorage.getItem(key);
      // Absent key → default (so a fresh browser sees the documented default
      // look). "true"/"false" strings are honored; anything else (corrupt,
      // malformed) also falls back to the default.
      return v === null ? defaultValue : v === "true";
    } catch {
      return defaultValue;
    }
  }

  function writeRaw(on: boolean) {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(key, on ? "true" : "false");
      // Same-tab notification — the reading-surface listeners re-render on this.
      window.dispatchEvent(new CustomEvent(eventName));
    } catch {
      /* private storage disabled (incognito, quota) — fail quietly */
    }
  }

  function subscribe(onStoreChange: () => void) {
    const onStorage = (event: StorageEvent) => {
      if (event.key === key) onStoreChange();
    };
    window.addEventListener(eventName, onStoreChange);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(eventName, onStoreChange);
      window.removeEventListener("storage", onStorage);
    };
  }

  // useSyncExternalStore gives localStorage a single reactive source of truth.
  // The server snapshot remains the documented default, while hydration reads
  // the stored value without a second effect-driven state transition.
  function useSetting(): [boolean, (on: boolean) => void] {
    const on = useSyncExternalStore(subscribe, readRaw, () => defaultValue);
    const toggle = useCallback((next: boolean) => writeRaw(next), []);
    return [on, toggle];
  }

  return { key, eventName, defaultValue, readRaw, writeRaw, useSetting };
}

// --- tone-colored pinyin (default off) ------------------------------------
// The spec's toneColor feature: opt-in coloring of <rt> + the popover's per-char
// rows by tone contour. Off by default so the reader's look is unchanged until
// the reader opts in.
const toneColors = makeBooleanSetting(
  "tbl:tone-colors",
  "tbl:tone-colors-changed",
  false,
);
export const TONE_COLORS_CHANGED_EVENT = toneColors.eventName;
export function useToneColors(): [boolean, (on: boolean) => void] {
  return toneColors.useSetting();
}
// Allow non-React modules (or a one-shot read inside a render without the hook)
// to consult the current value. Rare; the hook is the usual path.
export function toneColorsEnabled(): boolean {
  return toneColors.readRaw();
}

// --- pinyin annotations (default on) --------------------------------------
// Show/hide the ruby pinyin above each CJK char in the reading lines. On by
// default (pinyin is part of the default look); toggling off drops every <rt>
// in AnnotatedText. The popover's per-char breakdown keeps its pinyin — that
// reading IS the point of inspecting a char.
const pinyin = makeBooleanSetting("tbl:pinyin", "tbl:pinyin-changed", true);
export const PINYIN_CHANGED_EVENT = pinyin.eventName;
export function usePinyin(): [boolean, (on: boolean) => void] {
  return pinyin.useSetting();
}
export function pinyinEnabled(): boolean {
  return pinyin.readRaw();
}

// --- english translations (default on) ------------------------------------
// Show/hide the canonical English translation rows beneath each line. On by
// default; toggling off collapses the whole translation block (including the
// "no canonical translation seeded yet" empty state). The chengyu origin link
// stays — it's a classical-Chinese snippet, not a translation.
const english = makeBooleanSetting("tbl:english", "tbl:english-changed", true);
export const ENGLISH_CHANGED_EVENT = english.eventName;
export function useEnglish(): [boolean, (on: boolean) => void] {
  return english.useSetting();
}
export function englishEnabled(): boolean {
  return english.readRaw();
}
