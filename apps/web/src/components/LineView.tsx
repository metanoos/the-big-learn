"use client";

import { useCallback, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { type ReadingUnit, type WordSpan } from "@/lib/api";
import { AnnotatedText, type PinyinMap } from "./AnnotatedText";
import { CharacterPopover } from "./CharacterPopover";
import {
  addBookmark,
  bookmarkKey,
  isBookmarked,
  BOOKMARKS_CHANGED_EVENT,
  removeBookmark,
} from "@/lib/progress";
import { useEnglish } from "@/lib/settings";

// PinyinMap is re-exported from AnnotatedText (its canonical home — that's the
// component that consumes it). Kept on the LineView export so the chapter page
// and other callers don't need to know where it lives.
export type { PinyinMap };

// Display labels for the books whose origins we link chengyu to. Matches the
// ORIGIN_BOOKS set in tools/attach_chengyu_origins.py; the chengyu reader
// doesn't have the books list in hand, so the small map keeps the card
// self-contained. A new origin-source book needs an entry here.
const ORIGIN_BOOK_LABEL: Record<string, string> = {
  lunyu: "Lunyu 论语",
  mengzi: "Mengzi 孟子",
  daodejing: "Daodejing 道德经",
  "zhong-yong": "Zhong Yong 中庸",
  "da-xue": "Da Xue 大学",
  "sunzi-bingfa": "Sunzi Bingfa 孙子兵法",
};

export function LineView({
  book,
  chapter,
  unit,
  pinyin,
  selectedChar,
  selectedIndex,
  selectedAnchor,
  selectedWord,
  onSelectChar,
  onCloseChar,
}: {
  book: string;
  chapter: number;
  unit: ReadingUnit;
  pinyin: PinyinMap;
  // Currently-open character selection, owned by ChapterReader (one shared
  // selection across the whole chapter). When the open char lives in THIS
  // line, we render its popover from here.
  selectedChar?: string | null;
  selectedIndex?: number | null;
  // The clicked <ruby> element — the popover anchors to it. Passed through
  // from ChapterReader; null until a char is clicked.
  selectedAnchor?: HTMLElement | null;
  // The word span the open char belongs to (null if the char isn't part of a
  // multi-char compound, or word spans aren't in use). Passed to the popover
  // so it can render a word-level gloss section above the per-char breakdown.
  selectedWord?: WordSpan | null;
  onSelectChar?: (char: string, index: number, el: HTMLElement, word: WordSpan | null) => void;
  onCloseChar?: () => void;
}) {
  const line = unit.order;
  const canon = unit.canonical_translations ?? [];
  // English translations: per-browser setting (default on). Read here so the
  // whole translation block collapses the moment the toggle flips — no prop
  // drilling through ChapterReader. When off, the rows (and the "no canonical
  // translation seeded yet" empty state) drop out entirely; the chengyu origin
  // link below stays, since that's a classical-Chinese snippet, not a
  // translation.
  const [showEnglish] = useEnglish();
  // Copy-to-clipboard state: tracks whether the copy button has just fired,
  // so we can swap the icon for a checkmark briefly as confirmation.
  const [copied, setCopied] = useState(false);

  const subscribeToBookmark = useCallback((onStoreChange: () => void) => {
    const myKey = bookmarkKey(book, chapter, line);
    const onBookmarkChange = (event: Event) => {
      const changed = (event as CustomEvent<string>).detail;
      if (changed !== undefined && changed !== myKey) return;
      onStoreChange();
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key === "tbl:bookmarks") onStoreChange();
    };
    window.addEventListener(BOOKMARKS_CHANGED_EVENT, onBookmarkChange);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(BOOKMARKS_CHANGED_EVENT, onBookmarkChange);
      window.removeEventListener("storage", onStorage);
    };
  }, [book, chapter, line]);
  const getBookmarkSnapshot = useCallback(
    () => isBookmarked(book, chapter, line),
    [book, chapter, line],
  );
  const liked = useSyncExternalStore(
    subscribeToBookmark,
    getBookmarkSnapshot,
    () => false,
  );

  // Does the open selection belong to this line? The def card is rendered
  // inline beneath the line that owns the clicked char, so we check that the
  // selected char is actually present in this line's text at that index.
  const openInThisLine =
    !!selectedChar && !!onSelectChar && typeof selectedIndex === "number"
    && Array.from(unit.text)[selectedIndex] === selectedChar;

  // Copies the raw Chinese line to the clipboard and flashes a checkmark for
  // a moment so the reader sees it worked. The ChapterReader's dismiss-on-
  // pointerdown listener ignores clicks on this button because it's inside
  // the reader container (and stopPropagation isn't needed — dismissal
  // happening on a press here would only close a def card, not interrupt
  // the click).
  async function copyLine() {
    try {
      await navigator.clipboard.writeText(unit.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard API unavailable (e.g. insecure context) — fail quietly;
      // the icon just won't flash. Could surface a fallback later.
    }
  }

  // Toggle the private bookmark. The bookmark event synchronizes other
  // consumers in this tab; the storage event handles other tabs.
  function toggleBookmark() {
    const next = !liked;
    if (next) {
      addBookmark(book, chapter, line, {
        text: unit.text,
        translation: canon[0]?.text,
      });
    }
    else removeBookmark(book, chapter, line);
  }

  // No alternating row tint: the chapter surface stays a single uniform color
  // (the body bg-stone-950), with line separation carried by the parent's
  // `divide-y` dividers alone. Keeps the reading background flat.
  return (
    <article
      id={`line-${line}`}
      className="reading-line group/line py-4 scroll-mt-20 px-3 sm:px-4 -mx-3 sm:-mx-4"
    >
      {/*
        Header row above the line: the index sits at the left edge, the icon
        cluster (copy / like) hugs the right. Always visible — the affordances
        are part of the line, not surprises on hover.
      */}
      <div className="flex items-center justify-between font-sans tabular-nums select-none mb-3">
        {/* Index reads as "chapter-line" so a copied reference is unambiguous
            across the whole book, not just within this chapter. */}
        <span className="text-xs whitespace-nowrap text-stone-300 dark:text-stone-600">
          {chapter}-{line}
        </span>
        <div className="flex items-center gap-0.5">
          {/* Copy this line to the clipboard; flashes a checkmark briefly. */}
          <button
            type="button"
            onClick={copyLine}
            aria-label={copied ? "Copied" : "Copy this line"}
            className={`flex min-h-11 min-w-11 items-center justify-center rounded text-stone-400 hover:text-stone-700 hover:bg-stone-100 dark:text-stone-500 dark:hover:text-stone-200 dark:hover:bg-stone-800 ${
              copied ? "text-emerald-600 dark:text-emerald-400" : ""
            }`}
          >
            {copied ? <CheckIcon /> : <CopyIcon />}
          </button>
          {/* Save this line privately on this device. */}
          <button
            type="button"
            onClick={toggleBookmark}
            aria-pressed={liked}
            title={liked ? "Saved on this device" : "Save this line"}
            aria-label={liked ? "Remove this saved line" : "Save this line"}
            className={`flex min-h-11 min-w-11 items-center justify-center gap-1 rounded ${
              liked
                ? "text-rose-500 dark:text-rose-400"
                : "text-stone-400 hover:text-stone-700 hover:bg-stone-100 dark:text-stone-500 dark:hover:text-stone-200 dark:hover:bg-stone-800"
            }`}
          >
            {liked ? <HeartFilledIcon /> : <HeartIcon />}
          </button>
        </div>
      </div>

      {/*
        Line body: Chinese + canonical translation stacked, full width — no
        gutter column anymore, so the text owns the whole row.
      */}
      <div className="min-w-0">
        {/* Row 1: the Chinese line, with pinyin above each char + per-char
            click. */}
        <p className="cjk text-stone-900 dark:text-stone-100">
          <AnnotatedText
            text={unit.text}
            pinyin={pinyin}
            perCharPinyin={unit.pinyin_per_char}
            wordSpans={unit.word_spans}
            onChar={onSelectChar}
            selectedIndex={openInThisLine ? selectedIndex : null}
            selectedWordStart={openInThisLine ? selectedWord?.start ?? null : null}
            selectedWordEnd={openInThisLine ? selectedWord?.end ?? null : null}
          />
        </p>

        {/* Character definition popover. Rendered as a portal to <body> from
            CharacterPopover, so it floats above the page anchored to the
            clicked char rather than pushing content down. Only the line that
            owns the open selection mounts it (one shared selection). The
            `word` prop, when the clicked char belongs to a multi-char
            compound, renders a word-level gloss section above the per-char
            breakdown. */}
        {openInThisLine && selectedChar && (
          <CharacterPopover
            char={selectedChar}
            anchor={selectedAnchor ?? null}
            word={selectedWord ?? null}
            onClose={() => onCloseChar?.()}
          />
        )}

        {/* Row 2: canonical translation, aligned flush under the Chinese.
            Each entry carries a provenance byline (translator · year ·
            license) so the reader can see *who* rendered the line. Entries
            with source:"llm" are machine-generated (e.g. GLM poem
            translations where no PD human rendering exists); their byline
            already names the generator + license (e.g. "GLM · 2026 ·
            machine-generated"), so no separate badge is rendered — the byline
            itself keeps a generated line from passing silently as authoritative
            canon, which is the honest-framing rule the project holds to. */}
        {showEnglish && (
          <div className="mt-1.5 space-y-1.5">
          {canon.length > 0 ? (
            canon.map((c, i) => (
              <div key={i}>
                <p className="font-serif text-stone-800 dark:text-stone-200 leading-relaxed text-xl whitespace-pre-line">
                  {c.text}
                </p>
                <p className="mt-0.5 text-[11px] text-stone-400 dark:text-stone-500">
                  {c.source_url ? (
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline-offset-2 hover:underline"
                    >
                      {c.translator}
                      {c.year ? ` · ${c.year}` : ""} · {c.license}
                    </a>
                  ) : (
                    <>
                      {c.translator}
                      {c.year ? ` · ${c.year}` : ""} · {c.license}
                    </>
                  )}
                </p>
              </div>
            ))
          ) : (
            <p className="text-xs text-stone-400 dark:text-stone-500 italic">
              No canonical translation seeded yet.
            </p>
          )}
          </div>
        )}

        {/* Origin link: only chengyu units whose 4-char text is coined
            verbatim in a classical book we ship carry `unit.origin`. Built
            by tools/attach_chengyu_origins.py; absent everywhere else,
            including on chengyu with no verbatim origin (honest gap). */}
        {unit.origin && (
          <div className="mt-3 pt-3 border-t border-stone-200/60 dark:border-stone-800">
            <Link
              href={`/books/${unit.origin.book}/${unit.origin.chapter}#line-${unit.origin.line}`}
              className="group inline-block"
            >
              <span className="block text-[11px] uppercase tracking-wider text-stone-400 dark:text-stone-500">
                Origin · {ORIGIN_BOOK_LABEL[unit.origin.book] ?? unit.origin.book}
              </span>
              {unit.origin.snippet && (
                <span className="block text-xs italic text-stone-500 dark:text-stone-400 mt-1 group-hover:text-stone-700 dark:group-hover:text-stone-200 transition-colors">
                  {unit.origin.snippet}
                </span>
              )}
            </Link>
          </div>
        )}
      </div>
    </article>
  );
}

// --- copy icon (inline SVG; no icon dep to add for one glyph) --------------

function CopyIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

// Outline heart — the unsaved state. Same 16px stroke style as the copy/check
// icons so the cluster reads as one set.
function HeartIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}

// Filled heart — the saved state. The currentColor fill picks up the rose
// tint from the button's text color, so dark mode tracks automatically.
function HeartFilledIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="currentColor"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}
