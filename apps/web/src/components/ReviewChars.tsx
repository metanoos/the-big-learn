"use client";

// ReviewCharsSection: the page's "Saved words" panel. Surfaces every token the
// reader has expanded (via the popover) while reading — single chars and whole
// compounds alike. Backed by localStorage, so it works for anonymous readers
// too — no account required, matches the repo's "reading is anonymous" ethos.
//
// Reuses CharBreakdown (the same per-char row component the reader popover
// uses) for the expansion view, so a token renders identically whether it's
// opened here or in the reader.
//
// Tile layout is flex-wrap (not a fixed-col grid) so a tile can grow wider
// than its neighbours when its content needs the room: a 4-char chengyu's
// space-separated pinyin would otherwise wrap inside a fixed track. min-w on
// each tile preserves the old per-row density; whitespace-nowrap on the ruby
// makes the pinyin drive the tile's intrinsic width, so only tiles that
// actually need more room expand. h-full on the button keeps each row's tiles
// aligned to a uniform height.

import { useEffect, useState } from "react";
import {
  getReviewEntries,
  removeReviewEntry,
  REVIEW_CHARS_CHANGE_EVENT,
  type ReviewEntry,
} from "@/lib/reviewChars";
import { getCharPinyinBatch, type CharPinyinEntry } from "@/lib/api";
import { CharBreakdown } from "./CharBreakdown";

export function ReviewCharsSection() {
  const [entries, setEntries] = useState<ReviewEntry[]>([]);
  // Pinyin readings for the review tiles, keyed by entry text. Two sources
  // merged here: a multi-char entry's saved pinyin (captured at save time from
  // the popover), and the per-char batch endpoint for single-char entries (no
  // saved pinyin). One map so the tile render is uniform.
  const [pinyin, setPinyin] = useState<Map<string, string>>(new Map());
  const [openText, setOpenText] = useState<string | null>(null);

  // Read on mount, and re-read whenever the list changes. We listen to three
  // signals so the dashboard stays current without polling:
  //   - our custom same-tab event (fired on every add/remove in this tab)
  //   - the native `storage` event (fired when another tab writes)
  //   - window focus (cheap refresh when the reader returns to this tab,
  //     covering the rare case an event was missed)
  useEffect(() => {
    const refresh = () => setEntries(getReviewEntries());
    refresh();
    window.addEventListener(REVIEW_CHARS_CHANGE_EVENT, refresh);
    window.addEventListener("storage", refresh);
    window.addEventListener("focus", refresh);
    return () => {
      window.removeEventListener(REVIEW_CHARS_CHANGE_EVENT, refresh);
      window.removeEventListener("storage", refresh);
      window.removeEventListener("focus", refresh);
    };
  }, []);

  // Resolve pinyin for the tiles. Seed the map from entries that already carry
  // a saved reading (compound clicks), then fetch the remaining single-char
  // entries via the batch endpoint (one round-trip). Multi-char entries without
  // saved pinyin render bare — honest gap; in practice words always save pinyin.
  useEffect(() => {
    const saved = new Map<string, string>();
    const needFetch: string[] = [];
    for (const e of entries) {
      if (e.pinyin) saved.set(e.text, e.pinyin);
      // Batch endpoint is per-char; only single-char entries are fetchable.
      else if (Array.from(e.text).length === 1) needFetch.push(e.text);
    }
    if (needFetch.length === 0) {
      setPinyin(saved);
      return;
    }
    let cancelled = false;
    getCharPinyinBatch(needFetch)
      .then((m: Map<string, CharPinyinEntry>) => {
        if (cancelled) return;
        for (const [c, entry] of m) {
          if (entry.pinyin) saved.set(c, entry.pinyin);
        }
        setPinyin(saved);
      })
      .catch(() => setPinyin(saved)); // non-fatal: tiles fall back to bare glyphs
    return () => {
      cancelled = true;
    };
  }, [entries]);

  function remove(text: string) {
    // Optimistic: the change event will refresh anyway, but this keeps the UI
    // snappy and avoids a flash if the event is delayed.
    setEntries((es) => es.filter((e) => e.text !== text));
    removeReviewEntry(text);
  }

  return (
    <section>
      <h2 className="text-xs uppercase tracking-wider text-stone-400 dark:text-stone-500 mb-3">
        Saved words
      </h2>
      {entries.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-stone-400 italic">
          Click any character while reading to save it here for review.
        </p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {entries.map((e) => {
            const runes = Array.from(e.text);
            const py = pinyin.get(e.text);
            return (
              <li key={e.text} className="relative group min-w-[14%] sm:min-w-[11%] md:min-w-[9%]">
                <button
                  onClick={() => setOpenText(e.text)}
                  className="cjk min-h-16 w-full h-full flex items-center justify-center text-center px-1 bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 rounded hover:border-stone-400 dark:hover:border-stone-600"
                  aria-label={`Open ${e.text}`}
                >
                  <ruby className="flex flex-col items-center leading-tight whitespace-nowrap">
                    {py && <rt className="text-[0.5em] text-stone-500 dark:text-stone-400">{py}</rt>}
                    <span
                      className={
                        runes.length >= 4 ? "text-base" : runes.length === 3 ? "text-xl" : "text-2xl"
                      }
                    >
                      {e.text}
                    </span>
                  </ruby>
                </button>
                <button
                  onClick={() => remove(e.text)}
                  className="absolute -right-3 -top-3 flex h-11 w-11 items-center justify-center text-xs leading-none opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100 text-stone-600 dark:text-stone-300 hover:text-rose-700 dark:hover:text-rose-300"
                  aria-label={`Remove ${e.text} from review`}
                >
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-stone-200 hover:bg-rose-200 dark:bg-stone-700 dark:hover:bg-rose-900">×</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {openText && (() => {
        const entry = entries.find((e) => e.text === openText);
        return (
          <div className="mt-3 px-3 py-2 border-l-2 border-stone-300 dark:border-stone-700 bg-stone-50 dark:bg-stone-900 rounded-r text-sm">
            {/* Word-level gloss — mirrors the reader popover's word section so a
                saved token shows its meaning on top of the per-char breakdown,
                not just the breakdown. Rendered only when the entry carries a
                gloss (compound clicks saved after this field was added); older
                entries and single chars fall straight through to CharBreakdown. */}
            {entry?.gloss && (
              <div className="cjk-word-section">
                <div className="flex items-baseline gap-2 flex-wrap text-lg">
                  <span className="cjk-inline">{openText}</span>
                  {entry.pinyin && (
                    <span className="text-[0.48em] text-stone-400 dark:text-stone-500">
                      {entry.pinyin}
                    </span>
                  )}
                </div>
                <div className="mt-0.5">{entry.gloss}</div>
                <div className="mt-1 text-[10px] uppercase tracking-wide text-stone-400 dark:text-stone-500">
                  {entry.source === "classical-override"
                    ? "classical (curated)"
                    : entry.source === "CC-CEDICT"
                      ? "CC-CEDICT (modern)"
                      : ""}
                </div>
              </div>
            )}
            {/* Same CharBreakdown the reader popover uses — a token reads
                identically whether expanded here or in the reader. Per-char
                pinyin comes from the entry's saved reading when present. */}
            <CharBreakdown
              chars={Array.from(openText)}
              pinyinOverride={entry?.pinyin?.split(/\s+/) ?? null}
            />
          </div>
        );
      })()}
    </section>
  );
}
