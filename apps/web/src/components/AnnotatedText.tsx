"use client";

// AnnotatedText renders a string of Chinese text with pinyin ruby above each
// indexed CJK character, and (optionally) makes each CJK char clickable to
// open the character-breakdown popover.
//
// - CJK chars with a pinyin entry render as <ruby>字<rt>pīnyīn</rt></ruby>.
// - CJK chars the index doesn't cover render bare (honest gap: no fake pinyin).
// - Non-CJK runs (punctuation, numbers, latin) render as plain text so the
//   reader sees natural spacing and no broken ruby.
//
// WORD-AWARE RENDERING: when `wordSpans` is supplied (build-time compound
// segmentation — see tools/build_word_gloss.py), chars belonging to the same
// multi-char word are wrapped in a shared <span class="cjk-word"> so the whole
// word highlights on hover/select, and the click handler carries the word
// span up to the caller so the popover can show the token's gloss above the
// per-char breakdown. Falls back to per-char rendering (no word grouping)
// when wordSpans is absent or unaligned.
//
// Pinyin is supplied by the caller as a pre-built map (the chapter page builds
// one server-side for every line — zero per-line requests). The reader lines
// are the only surface annotated; everywhere else Chinese appears (titles,
// translation bodies, comments) shows the bare glyphs.

import { isCJK, toneOf } from "@/lib/cjk";
import type { WordSpan } from "@/lib/api";
import { usePinyin, useToneColors } from "@/lib/settings";

export type PinyinMap = Map<string, { pinyin: string | null; has_entry: boolean }>;

export function AnnotatedText({
  text,
  pinyin,
  perCharPinyin,
  wordSpans,
  onChar,
  selectedIndex,
  selectedWordStart,
  selectedWordEnd,
}: {
  text: string;
  // Map from single-character string -> {pinyin, has_entry}. Built once per
  // chapter by the chapter page and passed down; null pinyin = "no reading".
  // Used as a fallback when perCharPinyin is absent or out of sync.
  pinyin: PinyinMap;
  // Build-time, context-disambiguated pinyin (one syllable per rune, with
  // tone sandhi). Preferred over the per-char map when its length matches the
  // rune count of `text`, so polyphones read correctly in context. Non-CJK
  // runes occupy an array slot (empty string) so rune-index alignment holds.
  perCharPinyin?: string[];
  // Build-time compound segmentation of `text` (see tools/build_word_gloss.py).
  // When present and aligned (every CJK rune covered, indices within range),
  // chars in the same multi-char word group under a shared <span class="cjk-word">.
  // Optional; chengyu-catalog units and un-enriched content render legacy-style.
  wordSpans?: WordSpan[];
  // Called when a CJK character is clicked, with the rune, its index in
  // `text`, the clicked `<ruby>` element, and the word span the char belongs
  // to (or null when wordSpans isn't in use). ChapterReader stores the index
  // + word span so the popover can anchor to the clicked position and show
  // the token's gloss.
  onChar?: (char: string, index: number, el: HTMLElement, word: WordSpan | null) => void;
  // Rune index of the currently-selected char within this text, or null. The
  // ruby at this position gets .cjk-char-selected for as long as its def is open.
  selectedIndex?: number | null;
  // Rune range [start, end) of the currently-selected WORD within this text,
  // or null. Every ruby in this range gets .cjk-word-selected so the whole
  // compound highlights while its gloss is open. Parallel to selectedIndex
  // but ranges over the word; null/absent falls back to per-char highlight.
  selectedWordStart?: number | null;
  selectedWordEnd?: number | null;
}) {
  // Tone-colored pinyin: opt-in reader setting (per-browser, default off).
  // Read here so the class lands on every <rt> the moment the toggle flips,
  // without threading the value through LineView/ChapterReader props. Returns
  // false during SSR/first paint, so the server-rendered markup matches the
  // initial client render (no hydration flash).
  const [toneColors] = useToneColors();
  // Pinyin annotations: per-browser setting (default on). Read here so each
  // <rt> drops the moment the toggle flips — no prop drilling. When off, the
  // ruby renders bare (no <rt>), so the reading surface shows just the glyphs.
  const [showPinyin] = usePinyin();
  const runes = Array.from(text);
  const firstCjkIndex = runes.findIndex(isCJK);
  const out: React.ReactNode[] = [];
  // Use the build-time per-char array only when it aligns 1:1 with the runes.
  // Mismatch (e.g. content edited after build, or non-CJK handling drift)
  // silently falls back to the per-char map rather than misaligning ruby.
  const usePerChar = perCharPinyin && perCharPinyin.length === runes.length;

  // Validate wordSpans alignment before using it. The build guarantees every
  // CJK rune is covered exactly once with indices inside [0, runes.length),
  // but content can drift between builds; a stale/unaligned wordSpans would
  // mis-group chars, so we fall back to per-char rendering instead.
  const useWordSpans = !!wordSpans && wordSpansCoversCjk(runes, wordSpans);
  // rune index -> the word span covering it. Looked up per-char during render.
  const wordByStart = useWordSpans
    ? new Map(wordSpans!.map((w) => [w.start, w] as const))
    : null;
  const hasWordSelection =
    typeof selectedWordStart === "number" && typeof selectedWordEnd === "number";

  // Walk rune-by-rune, grouping consecutive non-CJK runes into a single text
  // node so the DOM stays light (punctuation between chars isn't split).
  let buf = "";
  let i = 0;
  const flushBuf = (key: number) => {
    if (!buf) return;
    out.push(<span key={`t-${key}`}>{buf}</span>);
    buf = "";
  };

  while (i < runes.length) {
    const r = runes[i];
    if (!isCJK(r)) {
      buf += r;
      i++;
      continue;
    }
    flushBuf(i);

    // If word spans are in use and this rune starts a word, render the whole
    // word as a group; otherwise render a single char (the legacy path, which
    // is also what the per-char fallback inside wordSpans produces).
    const wordStart = wordByStart?.get(i);
    if (wordStart) {
      const end = Math.min(wordStart.end, runes.length);
      out.push(renderWord(wordStart, end));
      i = end;
      continue;
    }

    out.push(renderChar(i, null, false));
    i++;
  }
  flushBuf(i);

  // Render one CJK rune as a <ruby>. `word` is the span this char belongs to
  // (null when wordSpans isn't in use or the char is rendered standalone);
  // it's passed up to the click handler so the popover can show the token's
  // gloss. `inSelectedWord` swaps the highlight class from per-char
  // (.cjk-char-selected) to whole-word (.cjk-word-selected) when the char's
  // word is the open one — so the compound lights up together.
  function renderChar(runeIdx: number, word: WordSpan | null, inSelectedWord: boolean) {
    const r = runes[runeIdx];
    // Prefer the build-time per-char reading (context-disambiguated, with
    // sandhi); fall back to the per-char map (first reading of that rune)
    // when no array or the array doesn't align. Either way, an empty/null
    // reading renders the char bare (honest gap — no fake pinyin).
    let reading: string | null = null;
    if (usePerChar) {
      const pc = perCharPinyin![runeIdx];
      reading = pc ? pc : null;
    } else {
      const entry = pinyin.get(r);
      reading = entry?.pinyin ?? null;
    }
    const clickable = !!onChar;
    const selected = selectedIndex != null && runeIdx === selectedIndex;
    // Bind the index into the click closure. Without this snapshot the
    // handler would capture the mutated loop counter.
    const idx = runeIdx;
    const activate = (el: HTMLElement) => onChar!(r, idx, el, word);
    return (
      <ruby
        key={`c-${runeIdx}`}
        className={[
          clickable ? "cjk-char" : "",
          inSelectedWord ? "cjk-word-selected" : "",
          // Per-char highlight only applies when NOT in a word selection
          // (otherwise the whole-word highlight takes over and per-char
          // would double up).
          !inSelectedWord && selected ? "cjk-char-selected" : "",
        ].join(" ").trim() || undefined}
        data-cjk-interactive={clickable ? "" : undefined}
        role={clickable ? "button" : undefined}
        tabIndex={clickable ? (runeIdx === firstCjkIndex ? 0 : -1) : undefined}
        aria-label={clickable ? `Open definition for ${r}${reading ? ` (${reading})` : ""}` : undefined}
        aria-expanded={clickable ? selected : undefined}
        onClick={
          clickable
            ? (e) => {
                e.stopPropagation();
                activate(e.currentTarget);
              }
            : undefined
        }
        onKeyDown={
          clickable
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  e.stopPropagation();
                  activate(e.currentTarget);
                  return;
                }
                if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
                const root = e.currentTarget.closest("[data-annotated-text]") as HTMLElement | null;
                const targets = root
                  ? Array.from(root.querySelectorAll<HTMLElement>("[data-cjk-interactive]"))
                  : [];
                const current = targets.indexOf(e.currentTarget);
                if (current < 0 || targets.length === 0) return;
                e.preventDefault();
                const next = e.key === "Home"
                  ? 0
                  : e.key === "End"
                    ? targets.length - 1
                    : Math.max(0, Math.min(targets.length - 1, current + (e.key === "ArrowRight" ? 1 : -1)));
                targets[current].tabIndex = -1;
                if (targets[next]) targets[next].tabIndex = 0;
                targets[next]?.focus();
              }
            : undefined
        }
      >
        {r}
        {reading && showPinyin && (
          <rt className={toneRtClass(reading, toneColors) || undefined}>
            {reading}
          </rt>
        )}
      </ruby>
    );
  }

  // Render a whole word (a run of CJK runes that share a word span) as a
  // grouped <span class="cjk-word"> containing one <ruby> per char. Pinyin
  // alignment is unchanged from the per-char path. The group gets
  // .cjk-word-selected when it's the open word, lighting up the compound.
  function renderWord(word: WordSpan, end: number) {
    const inSelectedWord =
      hasWordSelection &&
      selectedWordStart === word.start &&
      selectedWordEnd === end;
    return (
      <span
        key={`w-${word.start}`}
        className={[
          "cjk-word",
          inSelectedWord ? "cjk-word-selected" : "",
        ].join(" ").trim()}
      >
        {Array.from(
          { length: end - word.start },
          (_, k) => renderChar(word.start + k, word, inSelectedWord),
        )}
      </span>
    );
  }

  return <span data-annotated-text>{out}</span>;
}

// Validate that wordSpans covers every CJK rune exactly once with in-range
// indices. Drift between build and content (e.g. text edited after the spans
// were generated) would otherwise mis-group chars; we fall back to per-char
// rendering instead of rendering wrong groupings.
function wordSpansCoversCjk(runes: string[], spans: WordSpan[]): boolean {
  if (!spans.length) return false;
  const covered = new Array(runes.length).fill(false);
  for (const s of spans) {
    if (s.start < 0 || s.end > runes.length || s.start >= s.end) return false;
    for (let k = s.start; k < s.end; k++) {
      if (!isCJK(runes[k])) return false; // span covers a non-CJK rune — stale
      if (covered[k]) return false; // double-covered — stale
      covered[k] = true;
    }
  }
  // Every CJK rune must be covered (a per-char fallback span exists for each).
  for (let k = 0; k < runes.length; k++) {
    if (isCJK(runes[k]) && !covered[k]) return false;
  }
  return true;
}

// Resolve the tone class for a pinyin <rt>, or "" when tone coloring is off or
// the syllable's tone isn't 1–4 (neutral tone and unknown readings stay on the
// muted default — only the four contour tones carry a color). toneOf accepts
// both forms the reader sees (tone-marked from build-time, numeric from the
// per-char server map), so coloring is consistent regardless of source.
function toneRtClass(syllable: string, toneColors: boolean): string {
  if (!toneColors) return "";
  const t = toneOf(syllable);
  return t && t >= 1 && t <= 4 ? `tone-${t}` : "";
}
