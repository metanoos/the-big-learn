"use client";

// One book card in the library. Two variants share this file:
//
//   - readable (available !== false): clickable link to the book, with the
//     reader's device-local progress overlay + a ✓/○ toggle to mark the
//     whole book read/unread;
//   - placeholder (available === false): dimmed, dashed border, but still a
//     link — clicking opens the book page, which shows the description above
//     an empty chapter list. The dimming signals "not yet readable"; the
//     hover-to-full-opacity signals "you can still open it".
//
// Every card shows the four facet tags (tradition · tier · year · form)
// in a uniform row — that's what makes the curriculum comprehensible without
// a view-toggle. Tag labels come from libraryViews.cardTagLabels.
//
// Tradition is also encoded as a colored spine + a leading dot in the tag row
// (gold/jade/pink/slate), and Tier-S books carry a small ribbon in the
// top-right — the curriculum's "backbone of the language" tier. Color carries
// information, not decoration: only tradition and the top tier earn a mark.

import Link from "next/link";
import { type Book } from "@/lib/api";
import { BookTitle } from "@/components/BookTitle";
import { cardTagLabels } from "@/lib/libraryViews";
import { traditionColor } from "@/lib/traditionColor";

export function LibraryCard({
  book,
  readCount,
  onToggle,
  commentaryOn,
}: {
  book: Book;
  readCount: number | null;
  onToggle: (slug: string, total: number, wantRead: boolean) => void;
  // Resolved display name of the parent text when this book is a commentary
  // (e.g. "春秋" for Zuozhuan). Passed in pre-resolved so the card doesn't
  // need a slug→name lookup; undefined for non-commentary books.
  commentaryOn?: string;
}) {
  const tags = cardTagLabels(book);

  // Placeholder: catalog stub, content not yet ingested. Still a link to the
  // book page (where the description renders above an empty chapter list), but
  // visually set apart — dashed border + dimmed until hover, so it reads as a
  // roadmap slot, not a ready-to-read book. Keeps the tradition spine so the
  // shelf stays color-consistent.
  if (book.available === false) {
    return (
      <Link
        href={`/books/${book.slug}`}
        title="On the roadmap — text not yet ingested. Click for the description."
        className="relative block px-4 py-3 bg-stone-50 dark:bg-stone-900/40 border border-dashed border-stone-200 dark:border-stone-800 rounded opacity-60 hover:opacity-100 hover:border-stone-400 dark:hover:border-stone-600 transition"
        style={{
          borderLeftColor: traditionColor(book.tradition),
          borderLeftWidth: "3px",
          borderLeftStyle: "solid",
        }}
      >
        <TierRibbon tier={book.tier} dimmed />
        <div className="font-serif text-stone-700 dark:text-stone-300">
          <BookTitle book={book} size="card" />
        </div>
        {commentaryOn && (
          <span className="block text-[11px] italic text-stone-400 dark:text-stone-500">
            commentary on {commentaryOn}
          </span>
        )}
        {tags.length > 0 && (
          <TagRow tags={tags} className="mt-1" dotColor={traditionColor(book.tradition)} />
        )}
        <span className="block text-[11px] italic text-stone-400 dark:text-stone-500 mt-1">
          Not yet available · read the description
        </span>
      </Link>
    );
  }

  const total = book.chapter_count;
  const done = readCount ?? 0;
  const hasData = readCount !== null;
  const allRead = hasData && total > 0 && done >= total;
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;

  return (
    <div className="relative">
      <Link
        href={`/books/${book.slug}`}
        className="block px-4 py-3 bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 border-l-[3px] rounded hover:border-stone-400 dark:hover:border-stone-600 transition-colors"
        style={{ borderLeftColor: traditionColor(book.tradition) }}
      >
        {/* Tier-S ribbon: a small mark in the top-right corner, the only tier
            that earns one. Sits above the title so it reads as a flag, not a
            button. A/B stay unbadged — the shelf shouldn't rank every book. */}
        <TierRibbon tier={book.tier} />
        <div className="flex items-baseline justify-between gap-2">
          <span className="font-serif text-stone-900 dark:text-stone-100">
            <BookTitle book={book} size="card" />
          </span>
          {/* Chapter count + the read-toggle as a single right-aligned unit.
              The toggle moved here (was absolute top-right) to free the corner
              for the Tier-S ribbon; it still stops propagation so it doesn't
              navigate. */}
          <span className="flex items-center gap-2 shrink-0">
            {hasData && total > 0 && (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onToggle(book.slug, total, !allRead);
                }}
                title={allRead ? "Mark book unread" : "Mark book read"}
                aria-label={allRead ? "Mark book unread" : "Mark book read"}
                aria-pressed={allRead}
                className="w-5 h-5 -mr-0.5 flex items-center justify-center rounded-full text-xs
                           text-stone-400 hover:text-stone-700 dark:text-stone-500 dark:hover:text-stone-200
                           hover:bg-stone-100 dark:hover:bg-stone-800"
              >
                {allRead ? "✓" : "○"}
              </button>
            )}
            <span className="text-xs text-stone-400 dark:text-stone-500 tabular-nums">
              {hasData
                ? `${done} / ${total} chapters`
                : `${total} chapters`}
            </span>
          </span>
        </div>
        {commentaryOn && (
          <span className="block text-[11px] italic text-stone-400 dark:text-stone-500">
            commentary on {commentaryOn}
          </span>
        )}
        {tags.length > 0 && (
          <TagRow tags={tags} className="mt-1" dotColor={traditionColor(book.tradition)} />
        )}
        {hasData && total > 0 && (
          <div className="h-1 bg-stone-100 dark:bg-stone-800 rounded-full overflow-hidden mt-2">
            <div
              className="h-full bg-emerald-500 dark:bg-emerald-400 rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        )}
      </Link>
    </div>
  );
}

// Tier-S ribbon: a tiny amber flag in the top-right of a card. Only Tier-S
// (the "backbone of the language" tier per TAXONOMY.md) is marked — the
// curriculum's top rank, visible at a glance without ranking every book.
// `dimmed` lowers opacity for placeholder/roadmap cards so the mark stays
// consistent but quiet.
function TierRibbon({ tier, dimmed = false }: { tier: string | undefined; dimmed?: boolean }) {
  if (tier !== "S") return null;
  return (
    <span
      title="Tier S — backbone of the language"
      aria-label="Tier S"
      className={`absolute top-0 right-0 px-1.5 py-0.5 text-[10px] font-sans font-medium tracking-wide rounded-bl text-amber-800 dark:text-amber-300 bg-amber-100 dark:bg-amber-950/70 border-l border-b border-amber-200 dark:border-amber-900 ${dimmed ? "opacity-70" : ""}`}
    >
      S
    </span>
  );
}

// The four facet tags in a uniform row, with a leading dot in the book's
// tradition color. The dot reinforces the spine at card level — a quick scan
// down the shelf shows tradition by color before the eye reads any label.
function TagRow({
  tags,
  className = "",
  dotColor,
}: {
  tags: string[];
  className?: string;
  dotColor?: string;
}) {
  return (
    <div className={`text-[11px] text-stone-500 dark:text-stone-400 ${className}`}>
      {dotColor && (
        <span
          aria-hidden="true"
          className="inline-block w-1.5 h-1.5 rounded-full mr-1 align-middle"
          style={{ backgroundColor: dotColor }}
        />
      )}
      {tags.join(" · ")}
    </div>
  );
}
