"use client";

// ChapterReader owns the single shared "selected character" state across all
// lines of a chapter. It exists because character selection can't be per-line
// if "click anywhere dismisses the def": clicking a char in line 12 must close
// the def opened in line 5, and a click on empty space must close whatever's
// open. That requires one piece of state lifted above the lines.
//
// Selection model: the open char is identified by {char, index} (not just the
// char string) so the highlight lands on the exact rune the reader clicked,
// not on every identical character in the chapter.
//
// Dismissal: a document-level pointerdown listener closes the selection
// unless the click landed on a clickable character (`.cjk-char`) — those
// re-select rather than dismiss, handled by their own onClick + stopPropagation.
// The ChapterReader's own children (the def card included) are inside the
// listener's container ref and are ignored as dismissal triggers.

import { useCallback, useEffect, useRef, useState } from "react";
import { LineView, type PinyinMap } from "./LineView";
import type { ReadingUnit, WordSpan } from "@/lib/api";
import { markChapterReadLocal } from "@/lib/progress";

type Selection = {
  unitID: string;
  char: string;
  index: number;
  anchor: HTMLElement | null;
  // The word span the clicked char belongs to (null when wordSpans isn't in
  // use for this line). Carried up so LineView can pass it to the popover,
  // which renders a word-level gloss section above the per-char breakdown.
  word: WordSpan | null;
} | null;

export function ChapterReader({
  book,
  chapter,
  units,
  pinyin,
}: {
  book: string;
  chapter: number;
  units: ReadingUnit[];
  pinyin: PinyinMap;
}) {
  const [sel, setSel] = useState<Selection>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Mark this chapter read on mount. Reading works without an account, so
  // progress is persisted in localStorage and surfaced on the dashboard.
  // book + chapter are stable for a mounted reader; re-running would only
  // re-mark the same chapter.
  useEffect(() => {
    markChapterReadLocal(book, chapter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Click-anywhere-dismisses. Fires on pointerdown so the def closes before
  // any other click handler (e.g. a link navigation) commits — feels instant.
  // We ignore clicks that:
  //   - start outside this reader (NavBar, ChatBar, etc. handle themselves),
  //   - land on a `.cjk-char` (those select via their own handler).
  const dismiss = useCallback(() => setSel(null), []);

  useEffect(() => {
    if (!sel) return;
    const onDown = (e: PointerEvent) => {
      const target = e.target as Element | null;
      if (!target) return;
      // The popover is portaled to <body>, so it's outside containerRef — but
      // clicks inside it must NOT dismiss (interactions with the def should
      // stay put). It's marked with [data-char-popover].
      if (target.closest("[data-char-popover]")) return;
      // Clicks inside the reader container are dismissed, EXCEPT clicks on a
      // character — those re-select and call stopPropagation in their handler,
      // so they never reach this listener. Defense-in-depth: also check the
      // class so a non-clickable ruby (no onChar) inside the def card still
      // dismisses rather than no-ops.
      if (containerRef.current?.contains(target) && !target.closest(".cjk-char")) {
        // Inside the reader but not on a char → dismiss (covers the line gutter,
        // whitespace between lines).
        setSel(null);
      } else if (!containerRef.current?.contains(target)) {
        // Outside the reader entirely → dismiss.
        setSel(null);
      }
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [sel]);

  const select = useCallback((
    unitID: string,
    char: string,
    index: number,
    anchor: HTMLElement | null,
    word: WordSpan | null,
  ) => setSel({ unitID, char, index, anchor, word }), []);

  return (
    <div ref={containerRef} className="divide-y divide-stone-200 dark:divide-stone-800">
      {units.map((u) => (
        <LineView
          key={u.id}
          book={book}
          chapter={chapter}
          unit={u}
          pinyin={pinyin}
          selectedChar={sel?.unitID === u.id ? sel.char : null}
          selectedIndex={sel?.unitID === u.id ? sel.index : null}
          selectedAnchor={sel?.unitID === u.id ? sel.anchor : null}
          selectedWord={sel?.unitID === u.id ? sel.word : null}
          onSelectChar={(char, index, anchor, word) => select(u.id, char, index, anchor, word)}
          onCloseChar={dismiss}
        />
      ))}
    </div>
  );
}
