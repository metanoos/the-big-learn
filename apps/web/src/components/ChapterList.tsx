"use client";

// Chapter list for a single book, with per-chapter read indicators + a
// read/unread toggle on each row, and a "mark whole book" control in the
// header. The book page is server-rendered for the title/source; this overlays
// the reader's device-local progress.
//
// "Chapter read" == "the reader opened the chapter" (ChapterReader auto-marks
// it read on open). Toggling a chapter read/unread flips the whole chapter.
// Progress lives in localStorage — see lib/progress.ts.
//
// When the catalog supplies chapter titles (chapters[] prop), each row shows
// the Chinese title with pinyin ruby + optional English (via AnnotatedName,
// the same component book titles use). Rows with no title data fall back to
// the generic "第N章 · Chapter N" label — e.g. zhong-yong's empty titles, or
// any future catalog gap.

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getReadChapters,
  markBookReadLocal,
  markBookUnreadLocal,
  markChapterReadLocal,
  markChapterUnreadLocal,
  READ_CHANGED_EVENT,
} from "@/lib/progress";
import type { CatalogChapter } from "@/lib/api";
import { titleSyllables } from "@/lib/titles";
import { AnnotatedName } from "@/components/BookTitle";
import type { PinyinMap } from "@/components/AnnotatedText";

export function ChapterList({
  book,
  totalChapters,
  chapters,
  titlePinyin,
}: {
  book: string;
  totalChapters: number;
  chapters?: CatalogChapter[];
  titlePinyin?: PinyinMap;
}) {
  // readSet holds `"book:chapter"` keys for every chapter the reader has opened.
  // null = not yet loaded → no overlay.
  const [readSet, setReadSet] = useState<Set<string> | null>(null);

  // Load device-local progress, and re-read on our custom change event +
  // cross-tab storage so progress saved while reading appears live here.
  useEffect(() => {
    const sync = () => setReadSet(getReadChapters());
    sync();
    window.addEventListener(READ_CHANGED_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(READ_CHANGED_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const isRead = useCallback(
    (n: number) => (readSet ? readSet.has(`${book}:${n}`) : false),
    [readSet, book],
  );

  const setChapter = (n: number, wantRead: boolean) => {
    if (!readSet) return;
    const key = `${book}:${n}`;
    const next = new Set(readSet);
    if (wantRead) next.add(key);
    else next.delete(key);
    setReadSet(next);
    if (wantRead) markChapterReadLocal(book, n);
    else markChapterUnreadLocal(book, n);
  };

  const setAll = (wantRead: boolean) => {
    if (!readSet) return;
    const next = new Set(readSet);
    for (let n = 1; n <= totalChapters; n++) {
      const key = `${book}:${n}`;
      if (wantRead) next.add(key);
      else next.delete(key);
    }
    setReadSet(next);
    if (wantRead) markBookReadLocal(book, totalChapters);
    else markBookUnreadLocal(book);
  };

  const hasData = readSet !== null;
  const readCount = readSet
    ? Array.from({ length: totalChapters }, (_, i) => i + 1).filter((n) =>
        readSet.has(`${book}:${n}`),
      ).length
    : 0;

  // Index chapter entries by order once per render so each row's lookup is
  // O(1). Absent when the catalog ships no chapter data (the rows then fall
  // back to the generic 第N章 · Chapter N label).
  const byOrder = useMemo(() => {
    const m = new Map<number, CatalogChapter>();
    for (const c of chapters ?? []) m.set(c.order, c);
    return m;
  }, [chapters]);

  return (
    <div className="space-y-3">
      {hasData && totalChapters > 0 && (
        <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
          <span>
            {readCount} / {totalChapters} read
          </span>
          {/* Reading is automatic on open, so the only manual action needed is
              to undo it. Hide the control until at least one chapter is read. */}
          {readCount > 0 && (
            <button
              type="button"
              onClick={() => setAll(false)}
              className="px-2 py-1 rounded border border-stone-200 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-600 dark:text-stone-300"
            >
              Mark all unread
            </button>
          )}
        </div>
      )}
      <ol className="space-y-1">
        {Array.from({ length: totalChapters }, (_, i) => i + 1).map((n) => {
          const read = isRead(n);
          return (
            <li key={n} className="flex items-center gap-2">
              {hasData && (
                <button
                  type="button"
                  onClick={() => setChapter(n, !read)}
                  title={read ? "Mark chapter unread" : "Mark chapter read"}
                  aria-label={read ? "Mark chapter unread" : "Mark chapter read"}
                  aria-pressed={read}
                  className={[
                    "w-5 h-5 flex-shrink-0 flex items-center justify-center rounded-full text-xs",
                    read
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-stone-300 dark:text-stone-600 hover:text-stone-500 dark:hover:text-stone-400",
                  ].join(" ")}
                >
                  {read ? "✓" : "○"}
                </button>
              )}
              <Link
                href={`/books/${book}/${n}`}
                className={[
                  "block flex-1 px-3 py-2 hover:bg-stone-100 dark:hover:bg-stone-800 rounded text-sm",
                  read
                    ? "text-stone-500 dark:text-stone-400"
                    : "text-stone-700 dark:text-stone-300",
                ].join(" ")}
              >
                {(() => {
                  // When the catalog has a non-empty title for this chapter,
                  // render it as zh+pinyin ruby+en (AnnotatedName — the same
                  // component book titles use). Otherwise fall back to the
                  // generic "第N章 · Chapter N" label so an untitled catalog
                  // (e.g. zhong-yong) still has a readable row.
                  const c = byOrder.get(n);
                  const zh = c?.title?.trim();
                  if (zh) {
                    return (
                      <AnnotatedName
                        zh={zh}
                        pinyin={titleSyllables(zh, titlePinyin)}
                        en={c?.title_en}
                      />
                    );
                  }
                  return (
                    <>
                      {/* 第N章 rendered through AnnotatedName so 第 and 章 get
                          pinyin ruby above them, matching every other Chinese
                          title in the app. The digit N sits between them as
                          bare text (non-CJK runes don't consume a syllable).
                          Pinyin is hardcoded: 第 (dì) and 章 (zhāng) have one
                          stable reading in this fixed template — no lookup
                          needed. */}
                      <span className="text-stone-400 dark:text-stone-500 mr-3">
                        <AnnotatedName zh={`第${n}章`} pinyin="dì zhāng" />
                      </span>
                      Chapter {n}
                    </>
                  );
                })()}
              </Link>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
