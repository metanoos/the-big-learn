"use client";

// Library — the curriculum. Books grouped into named, narrated sections
// (Four Books → Daoist → Five Classics → …) in priority order. The earlier
// view-toggle is gone; facets survive as per-card tags (see LibraryCard).
//
// Server-side code passes the full book list; this client component layers
// the reader's device-local progress on top (per-card "X / Y ch read" + a
// ✓/○ toggle to mark the whole book read/unread). Progress lives in
// localStorage — see lib/progress.ts.
//
// "Chapter read" == "the reader has opened the chapter". ChapterReader
// auto-marks the chapter read on open, so opening a chapter == reading it.

import { useCallback, useEffect, useState } from "react";
import type { Book } from "@/lib/api";
import { LibraryCard } from "@/components/LibraryCard";
import { AnnotatedName } from "@/components/BookTitle";
import { groupByCurriculum } from "@/lib/libraryViews";
import {
  getReadChapters,
  markBookReadLocal,
  markBookUnreadLocal,
  READ_CHANGED_EVENT,
} from "@/lib/progress";

export function LibraryBooks({ books }: { books: Book[] }) {
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

  const readCount = useCallback(
    (slug: string): number | null => {
      if (!readSet) return null;
      let n = 0;
      readSet.forEach((k) => {
        if (k.startsWith(`${slug}:`)) n++;
      });
      return n;
    },
    [readSet],
  );

  const toggleBook = (slug: string, total: number, wantRead: boolean) => {
    if (!readSet) return;
    const next = new Set(readSet);
    for (let n = 1; n <= total; n++) {
      const key = `${slug}:${n}`;
      if (wantRead) next.add(key);
      else next.delete(key);
    }
    setReadSet(next);
    if (wantRead) markBookReadLocal(slug, total);
    else markBookUnreadLocal(slug);
  };

  const groups = groupByCurriculum(books);

  // slug → Chinese name, for resolving a commentary's parent text. Currently
  // only Zuozhuan (→ chun-qiu) uses this. Falls back to the slug if the parent
  // isn't in the catalog.
  const nameBySlug = new Map(books.map((b) => [b.slug, b.name_zh ?? b.slug]));
  const commentaryName = (b: Book): string | undefined =>
    b.commentary_on ? nameBySlug.get(b.commentary_on) ?? b.commentary_on : undefined;

  return (
    <div className="space-y-10">
      {groups.map((g) => (
        <section key={g.id} id={g.id}>
          <h2 className="font-serif text-lg text-stone-900 dark:text-stone-100">
            <AnnotatedName zh={g.name_zh} pinyin={g.name_pinyin} en={g.name_en} />
          </h2>
          {g.intro && (
            <p className="text-sm text-stone-500 dark:text-stone-400 mt-1 mb-3 max-w-prose leading-relaxed">
              {g.intro}
            </p>
          )}
          <div className={g.intro ? "grid gap-3 mt-1" : "grid gap-3 mt-3"}>
            {g.books.map((b) => (
              <LibraryCard
                key={b.slug}
                book={b}
                readCount={readCount(b.slug)}
                onToggle={toggleBook}
                commentaryOn={commentaryName(b)}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
