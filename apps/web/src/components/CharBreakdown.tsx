"use client";

// CharBreakdown renders the per-char definition rows shared by the reader
// popover and the dashboard's saved-token panel. One row per constituent char,
// each carrying its pinyin (tone-colored when the reader's tone toggle is on)
// and its English defs.
//
// Extracted from CharacterPopover so a token renders identically wherever it's
// expanded: a clicked compound in the reader, a single char in the reader, and
// a saved token re-opened on the dashboard all flow through these same rows.
//
// Defs are fetched lazily per char (progressive fill: each row populates as its
// lookup lands, so a slow char doesn't gate the others). `pinyinOverride` lets
// the caller pass the build-time, context-disambiguated reading carved out of a
// word's pinyin (preferred when present); absent that, the row falls back to
// the index's own reading for the char.

import { useEffect, useState } from "react";
import { getCharacter } from "@/lib/api";
import { toneOf } from "@/lib/cjk";
import { useToneColors } from "@/lib/settings";

// Per-char lookup result. Pinyin is the index's readings for the char (may be
// multiple — polyphones); english is the def list. Both empty when the char is
// unknown to the index (honest gap).
export type CharLookup = { pinyin: string[]; english: string[] };

// Split a word's space-separated pinyin string into one syllable per char.
// Tone-marked and aligned 1:1 with the word's chars (e.g. "bù yuǎn qiān lǐ" for
// 不远千里). Falls back to "" per slot on any mismatch (malformed entry, fewer
// syllables than chars) so per-char alignment never desyncs from the chars.
// Exported for the popover, which carves a word's pinyin into per-char slots.
export function splitWordPinyin(p: string | null | undefined, n: number): string[] {
  if (!p || n <= 0) return [];
  const parts = p.trim().split(/\s+/);
  // If the count doesn't match, give up on per-char pinyin rather than
  // misaligning — the row will show the char with no pinyin annotation.
  if (parts.length !== n) return Array.from({ length: n }, () => "");
  return parts;
}

export function CharBreakdown({
  chars,
  pinyinOverride,
}: {
  // The constituent chars to render rows for. For a compound that's every char
  // in the token; for a single char it's a one-element array.
  chars: string[];
  // Optional per-char pinyin (one syllable per char, aligned to `chars`), taken
  // from a build-time word reading when available. When a slot is empty (or the
  // whole array is absent), the row falls back to the index reading for that
  // char. Null/undefined when there's no word context (standalone char click).
  pinyinOverride?: string[] | null;
}) {
  // charDefs: per-char lookup result, keyed by char. Each char's lookup resolves
  // independently and progressively writes into this map, so rows populate as
  // their data lands rather than waiting on the slowest char.
  const [charDefs, setCharDefs] = useState<Record<string, CharLookup>>({});

  useEffect(() => {
    let cancelled = false;
    const wanted = new Set(chars);
    setCharDefs((prev) => {
      const next: Record<string, CharLookup> = {};
      // Carry over entries we still want; drop the rest (stale chars from a
      // previous token). Retained entries stay so a re-fetch on the same token
      // doesn't flash empty.
      for (const [c, d] of Object.entries(prev)) {
        if (wanted.has(c)) next[c] = d;
      }
      return next;
    });
    Promise.all(
      chars.map((c) =>
        getCharacter(c)
          .then((d) => {
            if (cancelled) return;
            setCharDefs((prev) => ({
              ...prev,
              [c]: { pinyin: d.pinyin ?? [], english: d.english ?? [] },
            }));
          })
          .catch(() => {
            if (cancelled) return;
            // Record the miss; the row renders "no definition".
            setCharDefs((prev) => ({ ...prev, [c]: { pinyin: [], english: [] } }));
          }),
      ),
    );
    return () => {
      cancelled = true;
    };
    // chars identity changes per render; join to keep deps stable for a given
    // token while still refetching when the token actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chars.join("")]);

  const overrides = pinyinOverride ?? [];

  return (
    <div className="cjk-char-section space-y-1.5">
      {chars.map((c, i) => (
        <CharRow
          key={`${c}-${i}`}
          char={c}
          // Prefer the build-time per-char reading (carved from the word's
          // pinyin, context-disambiguated); fall back to the index's reading
          // for this char when there's no word context.
          pinyin={overrides[i] || charDefs[c]?.pinyin?.[0] || ""}
          lookup={charDefs[c]}
        />
      ))}
    </div>
  );
}

// One constituent-char row. This is the single source of truth for "how a char
// looks when expanded" — used by both the reader popover and the dashboard.
// Pinyin is tone-colored when the reader's tone toggle is on (mirrors the
// AnnotatedText <rt> coloring via the same .tone-N classes). Defs populate
// lazily: a missing lookup shows "loading…", an empty english list shows "no
// definition", otherwise the defs joined into one line.
export function CharRow({
  char,
  pinyin,
  lookup,
}: {
  char: string;
  pinyin: string;
  lookup: CharLookup | undefined;
}) {
  const [toneColors] = useToneColors();
  const tone = toneOf(pinyin);
  const toneClass = toneColors && tone && tone >= 1 && tone <= 4 ? `tone-${tone}` : "";
  return (
    <div className="leading-snug">
      {/* text-base lives on the container (not the char span) so the pinyin
          span's 0.48em resolves against the char's size — mirroring how the
          reader's <rt> resolves 0.48em against its ruby base. Pinyin:char is
          the same 0.48:1 ratio as the reading surface, and the stone-400/500
          color matches the reader's ruby > rt. */}
      <div className="flex items-baseline gap-1.5 text-base">
        <span className="font-medium cjk-inline">{char}</span>
        {pinyin && (
          <span className={`text-[0.48em] text-stone-400 dark:text-stone-500 ${toneClass}`}>
            {pinyin}
          </span>
        )}
      </div>
      {lookup === undefined ? (
        <div className="text-xs text-stone-400 dark:text-stone-500 italic">loading…</div>
      ) : lookup.english.length === 0 ? (
        <div className="text-xs text-stone-400 dark:text-stone-500 italic">no definition</div>
      ) : (
        <div className="text-xs text-stone-700 dark:text-stone-300">
          {lookup.english.join("; ")}
        </div>
      )}
    </div>
  );
}
