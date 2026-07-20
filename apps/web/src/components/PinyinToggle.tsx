"use client";

// PinyinToggle: the chapter-header control for showing/hiding the ruby pinyin
// above each CJK char. A simple on/off pill (via the shared SettingToggle),
// backed by the per-browser setting in lib/settings.ts (default on — pinyin is
// part of the reader's default look).
//
// Lives in the chapter header alongside ToneColorToggle: it's a chapter-wide
// display preference, not a per-line affordance, and one control keeps the
// reading surface free of repeated chrome. The value is read inside AnnotatedText
// so every <rt> disappears the moment the flip lands, with no prop drilling.

import { usePinyin } from "@/lib/settings";
import { SettingToggle } from "./SettingToggle";

export function PinyinToggle() {
  const [on, setOn] = usePinyin();
  return (
    <SettingToggle
      on={on}
      onToggle={setOn}
      label="Pinyin"
      title={on ? "Hide pinyin annotations" : "Show pinyin annotations"}
    />
  );
}
