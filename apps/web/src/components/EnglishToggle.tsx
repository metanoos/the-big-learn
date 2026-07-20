"use client";

// EnglishToggle: the chapter-header control for showing/hiding the canonical
// English translation rows beneath each line. A simple on/off pill (via the
// shared SettingToggle). Backed by the per-browser setting in lib/settings.ts
// (default on — translations are part of the reader's default look).
//
// Lives in the chapter header alongside the tone-color and pinyin toggles:
// chapter-wide display preference, one control, reading surface stays clean.
// The value is read inside LineView so the whole translation block collapses
// the moment the flip lands. Toggling off does NOT touch the chengyu origin
// link — that's a classical-Chinese snippet, not a translation.

import { useEnglish } from "@/lib/settings";
import { SettingToggle } from "./SettingToggle";

export function EnglishToggle() {
  const [on, setOn] = useEnglish();
  return (
    <SettingToggle
      on={on}
      onToggle={setOn}
      label="English"
      title={on ? "Hide English translations" : "Show English translations"}
    />
  );
}
