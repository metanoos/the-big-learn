"use client";

// ToneColorToggle: the chapter-header control for tone-colored pinyin. The
// button swaps between an outlined (off) and filled (on) look so the state is
// readable at a glance. Backed by the per-browser setting in lib/settings.ts
// (default off — the reader's look is unchanged until the reader opts in).
//
// Lives in the chapter header rather than per-line: it's a chapter-wide display
// preference, not a per-line affordance, and one control keeps the reading
// surface free of repeated chrome.

import { usePinyin, useToneColors } from "@/lib/settings";
import { SettingToggle } from "./SettingToggle";

export function ToneColorToggle() {
  const [on, setOn] = useToneColors();
  const [pinyinOn] = usePinyin();
  return (
    <SettingToggle
      on={on}
      onToggle={setOn}
      label="Tones"
      title={
        !pinyinOn
          ? "Turn on Pinyin to use tone colors"
          : on
            ? "Turn off tone-colored pinyin"
            : "Color pinyin by tone (1·2·3·4)"
      }
      disabled={!pinyinOn}
    />
  );
}
