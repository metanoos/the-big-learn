import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getBooks, getCharPinyinBatch, type Book } from "@/lib/content";
import { CjkText } from "@/components/CjkText";
import { BookTitle } from "@/components/BookTitle";
import { BookBackground } from "@/components/BookBackground";
import { BookPairing } from "@/components/BookPairing";
import { ChapterList } from "@/components/ChapterList";
import { facetLabel, formatYear } from "@/lib/libraryViews";
import { isCJK } from "@/lib/cjk";
import type { PinyinMap } from "@/components/AnnotatedText";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ book: string }>;
}): Promise<Metadata> {
  const { book } = await params;
  const books = await getBooks();
  const meta = books.find((candidate) => candidate.slug === book);
  if (!meta) notFound();
  const title = meta.name_en || meta.display_name || meta.title;
  const description = meta.blurb || meta.background || `Read ${title} in classical Chinese.`;
  return {
    title,
    description,
    alternates: { canonical: `/books/${book}` },
    openGraph: { title, description, url: `/books/${book}`, type: "book" },
    twitter: { title, description },
  };
}

export default async function BookPage({
  params,
}: {
  params: Promise<{ book: string }>;
}) {
  const { book } = await params;
  const books = await getBooks();
  const meta = books.find((b) => b.slug === book);
  if (!meta) notFound();

  // Pairing: derive the commentary relationship both ways from the books list,
  // no extra catalog field needed. If this book has `commentary_on`, it expands
  // a parent text (Zuozhuan → Chun Qiu); if another book points here, this book
  // is the parent and has at least one commentary (Chun Qiu ← Zuozhuan).
  const parent = meta.commentary_on
    ? books.find((b) => b.slug === meta.commentary_on) ?? null
    : null;
  const commentaries = books.filter((b) => b.commentary_on === meta.slug);

  // Placeholder: catalog exists but the text isn't ingested yet. Mirror the
  // real book page — title → pairing → description → chapter list — but the
  // list is empty: a "No chapters yet" note where the rows would go. The URL
  // is reserved so it stays stable when content lands.
  if (meta.available === false) {
    return (
        <div className="space-y-6">
        <div>
          <Link href="/" className="text-sm text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-200">
            ← Library
          </Link>
          <h1 className="font-serif text-2xl text-stone-900 dark:text-stone-100 mt-5">
            <BookTitle book={meta} size="page" />
          </h1>
          <p className="text-xs text-stone-400 dark:text-stone-500 mt-1">
            {bookMetaLine(meta)}
          </p>
          <p className="text-xs text-stone-400 dark:text-stone-500">
            0 chapters · not yet available
          </p>
        </div>

        <BookPairing book={meta} parent={parent} commentaries={commentaries} />
        <BookBackground book={meta} />

        {/* Empty chapter list — same slot as on a real book, so the page
            shape is stable when the text lands. The description sits above
            it; the "no chapters yet" note sits where the rows would. */}
        <div className="border border-dashed border-stone-300 dark:border-stone-700 rounded p-6 bg-stone-50 dark:bg-stone-900/40">
          <p className="text-sm font-medium text-stone-700 dark:text-stone-200">
            No chapters yet
          </p>
          <p className="text-sm text-stone-500 dark:text-stone-400 mt-2">
            This text is on the roadmap but not yet ingested. Chapters will
            appear here when its source is prepared and aligned.
          </p>
          {meta.source_title && meta.source_title !== "Placeholder — text not yet ingested." && (
            <p className="text-xs text-stone-400 dark:text-stone-500 mt-3 italic">
              <CjkText>{meta.source_title}</CjkText>
            </p>
          )}
        </div>
      </div>
    );
  }

  const count = meta.chapter_count;

  // Batch-fetch pinyin for every CJK char across all chapter titles in one
  // round-trip, so the chapter list can render titles with pinyin ruby (same
  // pattern as the chapter page's per-line pinyin fetch). Non-fatal: on
  // failure the list falls back to bare titles without ruby.
  let titlePinyin: PinyinMap = new Map();
  const chars = new Set<string>();
  for (const c of meta.chapters ?? []) {
    for (const r of Array.from(c.title ?? "")) {
      if (isCJK(r)) chars.add(r);
    }
  }
  if (chars.size > 0) {
    try {
      titlePinyin = await getCharPinyinBatch(Array.from(chars));
    } catch {
      // Non-fatal: titles render without pinyin ruby.
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/" className="text-sm text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-200">
          ← Library
        </Link>
        <h1 className="font-serif text-2xl text-stone-900 dark:text-stone-100 mt-5">
          <BookTitle book={meta} size="page" />
        </h1>
        <p className="text-xs text-stone-400 dark:text-stone-500 mt-1">
          {bookMetaLine(meta)}
        </p>
        <p className="text-xs text-stone-400 dark:text-stone-500">
          {count} chapter{count === 1 ? "" : "s"}
          {seedTranslationLabel(meta)}
        </p>
      </div>

      <BookPairing book={meta} parent={parent} commentaries={commentaries} />
      <BookBackground book={meta} />

      <ChapterList
        book={book}
        totalChapters={count}
        chapters={meta.chapters}
        titlePinyin={titlePinyin}
      />
    </div>
  );
}

function seedTranslationLabel(book: Book): string {
  const seed = book.seed_translator;
  if (!seed) return "";
  const details = [seed.translator, seed.year, seed.license].filter(Boolean).join(" · ");
  return details ? ` · seed translation: ${details}` : "";
}

// One-line facet summary for a book — tradition · form · year · tier.
// Mirrors the cross-cutting labels on library cards so the vocabulary is
// consistent everywhere a book is shown.
function bookMetaLine(b: Book): string {
  const parts: string[] = [];
  if (b.tradition) parts.push(facetLabel("tradition", b.tradition));
  if (b.form)      parts.push(facetLabel("form", b.form));
  if (b.year || b.era) parts.push(formatYear(b.year, b.era));
  if (b.tier)      parts.push(`Tier ${b.tier}`);
  return parts.join(" · ");
}
