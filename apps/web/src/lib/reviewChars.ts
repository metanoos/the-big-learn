// Per-browser "review" list of tokens the reader has expanded. A token is the
// CJK text of whatever the popover opened on — a single char (道) or a whole
// compound (天命). Stored in localStorage (anonymous-friendly — reading needs
// no account, and so does building up a review pile). Entries are MRU-first,
// deduped by `text`, unbounded.
//
// Each entry optionally carries the pinyin the popover had in hand at save time
// (build-time, context-disambiguated for compounds). Single chars don't carry
// pinyin here — they resolve at render via the per-char batch endpoint, as in
// the chapter reader. So `pinyin` is present exactly when the entry is a
// multi-char compound.
//
// STORAGE SHAPE & MIGRATION: the payload is `ReviewEntry[]`. Earlier versions
// stored a flat `string[]` of single chars; `readRaw` migrates that shape
// transparently on first read (each valid char → {text}), so existing lists
// survive without a version bump. The localStorage KEY is unchanged for the
// same reason.
//
// All accessors are SSR-safe: they no-op on the server and survive a corrupt
// JSON blob without throwing. Writes broadcast a custom event so same-tab
// subscribers (e.g. the dashboard section) can re-read live; cross-tab updates
// arrive through the native `storage` event, which listeners opt into.

import { isCJK } from "@/lib/cjk";

const KEY = "tbl:review-chars";
const CHANGE_EVENT = "tbl:review-chars-changed";

export type ReviewEntry = {
  text: string; // 1+ CJK runes; the token's surface form
  // Tone-marked, space-separated pinyin (e.g. "tiān mìng"). Present when the
  // entry was saved from a compound click (the build-time reading); absent for
  // single-char entries, which resolve their reading at render.
  pinyin?: string;
  // Word-level gloss captured at save time (the popover's word-section gloss).
  // Present only for compound clicks that carried a gloss; absent for single
  // chars and entries saved before this field existed. Surfaced at the top of
  // the dashboard expansion so a saved token shows its meaning, not just the
  // per-char breakdown.
  gloss?: string;
  // Provenance of the gloss — mirrors WordSpan["source"], so the dashboard can
  // render the same "classical (curated)" / "CC-CEDICT (modern)" label as the
  // in-reader popover. Absent alongside gloss.
  source?: "classical-override" | "CC-CEDICT" | "char";
};

// A token is valid iff it's a non-empty string of CJK runes only. Punctuation,
// latin, or mixed runs are rejected so the review list never collects junk
// (defensive against a corrupt payload or a future caller mistake).
function isValidToken(s: unknown): s is string {
  if (typeof s !== "string" || s.length === 0) return false;
  const runes = Array.from(s);
  return runes.length > 0 && runes.every(isCJK);
}

// Read + validate + migrate. Returns a clean ReviewEntry[] come what may:
// legacy string[] → migrated; corrupt payload → empty (honest gap).
function readRaw(): ReviewEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    // Legacy shape: string[] of single chars. Migrate each valid entry.
    if (parsed.length === 0 || typeof parsed[0] === "string") {
      return (parsed as unknown[])
        .filter(isValidToken)
        .map((text) => ({ text }));
    }

    // Current shape: ReviewEntry[]. Validate text; carry pinyin only when it's
    // a non-empty string aligned to the token's char count (one syllable per
    // rune, space-separated). gloss/source ride along when present. Malformed
    // fields are dropped, not fatal.
    return (parsed as unknown[])
      .filter((e): e is Record<string, unknown> => {
        if (!e || typeof e !== "object") return false;
        return isValidToken((e as { text?: unknown }).text);
      })
      .map((e) => {
        const text = e.text as string;
        const entry: ReviewEntry = { text };
        const p = e.pinyin;
        if (typeof p === "string" && p.trim()) entry.pinyin = p;
        const g = e.gloss;
        if (typeof g === "string" && g.trim()) {
          entry.gloss = g;
          const s = e.source;
          // Only carry a source we recognize; an unknown value would leave the
          // provenance label blank but the gloss would still render.
          if (s === "classical-override" || s === "CC-CEDICT" || s === "char") {
            entry.source = s;
          }
        }
        return entry;
      });
  } catch {
    return [];
  }
}

function write(entries: ReviewEntry[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(entries));
    // Same-tab notification. The dashboard listens for this so a token saved
    // while reading appears when the reader returns to the dashboard tab.
    window.dispatchEvent(new Event(CHANGE_EVENT));
  } catch {
    /* quota / disabled storage — review list is best-effort, never fatal */
  }
}

export function getReviewEntries(): ReviewEntry[] {
  return readRaw();
}

// Add (or MRU-promote) a token. Pinyin is recorded when supplied (compound
// clicks); omitted for single chars. gloss + source are recorded alongside
// when the token was opened from a compound with a word-level gloss, so the
// dashboard expansion can show the word def above the per-char breakdown.
// Dedup is by `text` — re-opening a token bubbles it to the front and refreshes
// its gloss/source to the latest click's, matching the original MRU behavior.
export function addReviewEntry(
  text: string,
  pinyin?: string,
  gloss?: string,
  source?: ReviewEntry["source"],
) {
  if (!isValidToken(text)) return;
  const entry: ReviewEntry = { text };
  if (pinyin && pinyin.trim()) entry.pinyin = pinyin;
  if (gloss && gloss.trim()) {
    entry.gloss = gloss;
    if (source) entry.source = source;
  }
  const next: ReviewEntry[] = [entry, ...readRaw().filter((e) => e.text !== text)];
  write(next);
}

export function removeReviewEntry(text: string) {
  write(readRaw().filter((e) => e.text !== text));
}

// Unchanged event name — cross-tab listeners keyed on the old name keep
// working without a redeploy of every subscriber.
export const REVIEW_CHARS_CHANGE_EVENT = CHANGE_EVENT;
