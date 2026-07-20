"use client";

// Review — a real, device-local view of what this reader has set aside.
//
// Reading works without an account, so this view is what makes that visible:
// the saved lines (bookmarks) and the saved words (characters expanded via the
// popover while reading). Everything here is localStorage-backed and never
// leaves this browser.
//
// Per-book progress is intentionally NOT shown here — that lives on the Library
// page, where each card carries its own "X / Y ch read" overlay. This page is
// only the things the reader has personally pulled out of the text.

import Link from "next/link";
import { useEffect, useState } from "react";
import { getBooks, getChapter, type Book } from "@/lib/api";
import { BookTitle, type BookName } from "@/components/BookTitle";
import { ReviewCharsSection } from "@/components/ReviewChars";
import { ReaderDataControls } from "@/components/ReaderDataControls";
import {
  BOOKMARKS_CHANGED_EVENT,
  getBookmarkPreviews,
  getBookmarks,
  removeBookmark,
  saveBookmarkPreviews,
  type BookmarkPreview,
} from "@/lib/progress";

export default function DashboardPage() {
  return <LocalDashboard />;
}

function LocalDashboard() {
  // Books catalog is anonymous-readable; needed to title the saved-lines rows.
  const [books, setBooks] = useState<Book[] | null>(null);
  const [bookmarks, setBookmarks] = useState<string[]>([]);
  const [previews, setPreviews] = useState<Record<string, BookmarkPreview>>({});

  useEffect(() => {
    let cancelled = false;
    getBooks()
      .then((b) => {
        if (!cancelled) setBooks(b);
      })
      .catch(() => {
        if (!cancelled) setBooks([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Sync bookmarks now and on change. Browser-only, so this view reflects
  // lines saved in any tab live.
  useEffect(() => {
    const sync = () => {
      setBookmarks(getBookmarks());
      setPreviews(getBookmarkPreviews());
    };
    sync();
    window.addEventListener(BOOKMARKS_CHANGED_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(BOOKMARKS_CHANGED_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  // Bookmarks created before previews were introduced only contain a location.
  // Backfill their Chinese and first English line from the bundled chapter
  // content once, then keep that snapshot locally with the bookmark.
  useEffect(() => {
    const missing = bookmarks
      .map(parseBookmarkKey)
      .filter((entry): entry is ParsedBookmark => !!entry && !previews[entry.key]);
    if (missing.length === 0) return;

    let cancelled = false;
    const chapters = new Map<string, ParsedBookmark[]>();
    for (const entry of missing) {
      const chapterKey = `${entry.book}:${entry.chapter}`;
      chapters.set(chapterKey, [...(chapters.get(chapterKey) ?? []), entry]);
    }
    Promise.all(
      Array.from(chapters.values()).map(async (entries) => ({
        entries,
        chapter: await getChapter(entries[0].book, entries[0].chapter),
      })),
    )
      .then((results) => {
        if (cancelled) return;
        const next = { ...previews };
        for (const { entries, chapter } of results) {
          for (const entry of entries) {
            const unit = chapter.chapter.reading_units.find((candidate) => candidate.order === entry.line);
            if (!unit) continue;
            next[entry.key] = {
              text: unit.text,
              translation: unit.canonical_translations?.[0]?.text,
            };
          }
        }
        saveBookmarkPreviews(next);
        setPreviews(next);
      })
      .catch(() => {
        // The saved location remains usable if content is temporarily offline.
      });
    return () => {
      cancelled = true;
    };
  }, [bookmarks, previews]);

  const names: Record<string, BookName> = {};
  for (const b of books ?? []) {
    names[b.slug] = {
      slug: b.slug,
      name_zh: b.name_zh,
      name_pinyin: b.name_pinyin,
      name_en: b.name_en,
      display_name: b.display_name,
      title: b.title,
    };
  }

  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <h1 className="font-serif text-2xl text-stone-900 dark:text-stone-100">Review</h1>
        <p className="text-stone-600 dark:text-stone-300 text-sm">
          Saved only on this device. The lines and words you've pulled out of
          the text live in this browser — no account, no sync.
        </p>
      </div>

      <ReviewCharsSection />

      <section>
        <h2 className="text-xs uppercase tracking-wider text-stone-400 dark:text-stone-500 mb-3">
          Saved lines · on this device
        </h2>
        {bookmarks.length === 0 ? (
          <p className="text-sm text-stone-500 dark:text-stone-400 italic">
            None yet. Tap the heart on a line in the reader to save it here.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {bookmarks.map((key, i) => {
              const m = key.split(":");
              const book = m[0];
              const ch = Number(m[1]);
              const ln = Number(m[2]);
              if (!book || !ch || !ln) return null;
              return (
                <SavedLineRow
                  key={`${book}:${ch}:${ln}`}
                  book={book}
                  chapter={ch}
                  line={ln}
                  name={names[book] ?? { slug: book }}
                  preview={previews[key]}
                />
              );
            })}
          </ul>
        )}
      </section>

      <ReaderDataControls />
    </div>
  );
}

// One saved-line row. The body is a link into the reader (chapter + line
// anchor); the heart removes the device-local bookmark in place so a reader can
// prune their saved list without leaving Review. A bookmark-changed event then
// re-syncs the list.
function SavedLineRow({
  book,
  chapter,
  line,
  name,
  preview,
}: {
  book: string;
  chapter: number;
  line: number;
  name: BookName;
  preview?: BookmarkPreview;
}) {
  function remove() {
    removeBookmark(book, chapter, line);
  }

  return (
    <li className="flex items-start gap-2 text-sm">
      <button
        type="button"
        onClick={remove}
        aria-label="Remove this saved line"
        title="Remove from saved"
        className="flex min-h-11 min-w-11 shrink-0 items-center justify-center text-rose-500 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 transition-colors"
      >
        ♥
      </button>
      <Link
        href={`/books/${book}/${chapter}#line-${line}`}
        className="min-w-0 flex-1 rounded px-2 py-2 text-stone-600 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-900 dark:hover:text-stone-100"
      >
        <span className="flex items-center gap-2 text-xs text-stone-400 dark:text-stone-500">
          <span className="whitespace-nowrap tabular-nums">{chapter}-{line}</span>
          <BookTitle book={name} size="card" />
        </span>
        {preview?.text && (
          <span className="mt-1 block">
            <span className="cjk-inline block text-lg text-stone-800 dark:text-stone-200">
              {preview.text}
            </span>
            {preview.translation && (
              <span className="mt-0.5 block text-sm text-stone-500 dark:text-stone-400">
                {preview.translation}
              </span>
            )}
          </span>
        )}
      </Link>
    </li>
  );
}

type ParsedBookmark = {
  key: string;
  book: string;
  chapter: number;
  line: number;
};

function parseBookmarkKey(key: string): ParsedBookmark | null {
  const [book, chapterRaw, lineRaw] = key.split(":");
  const chapter = Number(chapterRaw);
  const line = Number(lineRaw);
  if (!book || !Number.isInteger(chapter) || chapter < 1 || !Number.isInteger(line) || line < 1) {
    return null;
  }
  return { key, book, chapter, line };
}
