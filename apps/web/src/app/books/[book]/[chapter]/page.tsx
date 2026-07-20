import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ApiError, getBooks, getChapter, getCharPinyinBatch, type Book, type ReadingUnit, type WordSpan } from "@/lib/content";
import { ChapterReader } from "@/components/ChapterReader";
import { BookTitle, AnnotatedName } from "@/components/BookTitle";
import { ToneColorToggle } from "@/components/ToneColorToggle";
import { PinyinToggle } from "@/components/PinyinToggle";
import { EnglishToggle } from "@/components/EnglishToggle";
import { isCJK } from "@/lib/cjk";
import { titleSyllables, findChapterTitleEn } from "@/lib/titles";
import type { PinyinMap } from "@/components/AnnotatedText";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ book: string; chapter: string }>;
}): Promise<Metadata> {
  const { book, chapter } = await params;
  const chapterNum = Number(chapter);
  if (!Number.isInteger(chapterNum) || chapterNum < 1) notFound();
  const books = await getBooks();
  const bookMeta = books.find((candidate) => candidate.slug === book);
  const chapterMeta = bookMeta?.chapters?.find((candidate) => candidate.order === chapterNum);
  if (!bookMeta || bookMeta.available === false || !chapterMeta) notFound();
  const bookTitle = bookMeta.name_en || bookMeta.display_name || bookMeta.title;
  const chapterTitle = chapterMeta.title_en || chapterMeta.title || `Chapter ${chapterNum}`;
  const title = `${chapterTitle} — ${bookTitle}`;
  const description = `Read ${chapterTitle} from ${bookTitle} in classical Chinese with pinyin, translation, and character definitions.`;
  return {
    title,
    description,
    alternates: { canonical: `/books/${book}/${chapterNum}` },
    openGraph: { title, description, url: `/books/${book}/${chapterNum}`, type: "article" },
    twitter: { title, description },
  };
}

export default async function ChapterPage({
  params,
}: {
  params: Promise<{ book: string; chapter: string }>;
}) {
  const { book, chapter } = await params;
  const chapterNum = Number(chapter);
  if (!Number.isInteger(chapterNum) || chapterNum < 1) notFound();

  // Books list carries the authoritative chapter_count. Fetch in parallel with
  // the chapter payload; fall back to null on error so the chapter still renders.
  const [chResult, booksResult] = await Promise.allSettled([
    getChapter(book, chapterNum),
    getBooks(),
  ]);
  // Resolve the book's presentational name up front so the error path can use
  // it too — the raw `book` param is the slug (e.g. "lunyu"), not a name to
  // show a reader.
  if (booksResult.status === "rejected") throw booksResult.reason;
  const books: Book[] = booksResult.value;
  const bookMeta = books.find((b) => b.slug === book);
  if (!bookMeta || bookMeta.available === false) notFound();
  if (chResult.status === "rejected") {
    if (chResult.reason instanceof ApiError && chResult.reason.status === 404) notFound();
    throw chResult.reason;
  }
  const ch = chResult.value;
  const totalChapters = bookMeta?.chapter_count ?? 0;

  // Batch-fetch pinyin for every CJK char in the chapter in one round-trip.
  // Runs server-side (this is a Server Component) so the browser pays nothing.
  // Chars not in the index map to null — rendered as bare text, no fake pinyin.
  // Includes the title's chars so the heading can render pinyin ruby too.
  const chars = new Set<string>();
  for (const r of Array.from(ch.chapter.title)) {
    if (isCJK(r)) chars.add(r);
  }
  for (const u of ch.chapter.reading_units) {
    for (const r of Array.from(u.text)) {
      if (isCJK(r)) chars.add(r);
    }
  }
  let pinyin: PinyinMap = new Map();
  if (chars.size > 0) {
    try {
      pinyin = await getCharPinyinBatch(Array.from(chars));
    } catch {
      // Non-fatal: lines render without pinyin. The popover still works on click.
    }
  }

  const prev = chapterNum > 1 ? chapterNum - 1 : null;
  // Bound "next" by the book's actual chapter_count (known from the catalog),
  // never by reading_unit_count (that's lines-per-chapter, unrelated — see the
  // da-xue ch7 → phantom ch8 bug).
  const hasNext = totalChapters > 0 && chapterNum < totalChapters;
  const next = hasNext ? chapterNum + 1 : null;

  return (
    <div className="space-y-8">
      <div>
        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link href={`/books/${book}`} className="group text-sm text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-200">
            ← <BookTitle book={bookMeta ?? { slug: book }} />
          </Link>
          {/* Chapter-wide display settings, kept out of the reading surface so
              the lines stay clean. All per-browser, read reactively by the
              reading-surface components (no prop drilling):
                English  — canonical translation rows on/off (default on)
                Pinyin   — ruby annotations on/off (default on)
                Tones    — opt-in coloring of pinyin by tone (default off) */}
          <div className="flex items-center gap-1 self-end sm:self-auto">
            <EnglishToggle />
            <PinyinToggle />
            <ToneColorToggle />
          </div>
        </div>
        {/* Chapter title: Chinese with pinyin ruby + English, the same
            three-part treatment the chapter list uses (AnnotatedName). Pinyin
            rides the same batch fetch as the reading-unit chars above; the
            English label comes from the catalog chapters[] on bookMeta (the
            single-chapter endpoint doesn't carry title_en, but getBooks()
            above does). Falls back to "第N章 · Chapter N" when this catalog
            ships no title (e.g. zhong-yong) — mirrors the chapter list. */}
        {(() => {
          const zh = ch.chapter.title?.trim();
          if (!zh) {
            return (
              <h1 className="font-serif text-xl text-stone-900 dark:text-stone-100 mt-5">
                {/* 第N章 rendered through AnnotatedName so 第 and 章 get pinyin
                    ruby, matching every other Chinese title in the app. The
                    digit sits between them as bare text. Pinyin hardcoded:
                    第 (dì) and 章 (zhāng) have one stable reading in this
                    fixed template. */}
                <span className="text-stone-500 dark:text-stone-400 mr-3">
                  <AnnotatedName zh={`第${chapterNum}章`} pinyin="dì zhāng" />
                </span>
                Chapter {chapterNum}
              </h1>
            );
          }
          return (
            <h1 className="font-serif text-xl text-stone-900 dark:text-stone-100 mt-5 cjk">
              <AnnotatedName
                zh={zh}
                pinyin={titleSyllables(zh, pinyin)}
                en={findChapterTitleEn(bookMeta, chapterNum)}
              />
            </h1>
          );
        })()}
      </div>

      <ChapterReader
        book={book}
        chapter={chapterNum}
        units={ch.chapter.reading_units.map(synthesizeUnitWordSpan)}
        pinyin={pinyin}
      />

      <nav className="flex justify-between text-sm pt-4">
        {prev ? (
          <Link href={`/books/${book}/${prev}`} className="text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100">
            ← Chapter {prev}
          </Link>
        ) : (
          <span />
        )}
        {next && (
          <Link href={`/books/${book}/${next}`} className="text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100">
            Chapter {next} →
          </Link>
        )}
      </nav>
    </div>
  );
}

// Synthesize a whole-text word span for reading units the build pipeline
// didn't segment. Today that's the chengyu catalog: each unit's `text` is a
// single 4-char idiom that IS one word, but the units ship without
// `word_spans`, so without this a chengyu click would render only the single
// char's def — never the idiom's meaning (which sits in
// canonical_translations[0].text). Classical books already carry word_spans
// and are returned untouched.
//
// Guards: only when the text is non-empty + all-CJK (so a single [0, n) span
// is valid — no punctuation gaps), a gloss is present, and a top-level pinyin
// string exists. Units with no gloss fall back to per-char only (honest: we
// have nothing to show at the word level), matching the prior behavior. The
// synthesized span flows through the existing popover machinery unchanged,
// including the CC-CEDICT provenance label.
function synthesizeUnitWordSpan(unit: ReadingUnit): ReadingUnit {
  if (unit.word_spans && unit.word_spans.length > 0) return unit;
  const runes = Array.from(unit.text);
  if (runes.length === 0 || !runes.every(isCJK)) return unit;
  const gloss = unit.canonical_translations?.[0]?.text;
  const pinyin = unit.pinyin;
  if (!gloss || !pinyin) return unit;
  const span: WordSpan = {
    start: 0,
    end: runes.length,
    word: unit.text,
    pinyin,
    gloss,
    source: "CC-CEDICT",
  };
  return { ...unit, word_spans: [span] };
}
