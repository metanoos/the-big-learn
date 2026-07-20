// Plain-string display names — the fallback path. The catalog `title` field
// holds the source document title (provenance), not a human-facing book name.
// The human-facing name lives in the catalog as `display_name`.
//
// For VISIBLE rendering, prefer <BookTitle> (apps/web/src/components/BookTitle),
// which renders the structured name_zh with pinyin ruby above + name_en. This
// helper is for contexts that need a plain string: the browser <title> tag,
// alt text, oEmbed-style single strings.
//
// Two call shapes:
//   displayName(book)            — pass a Book to read its display_name
//   displayName(slug, names?)    — slug with an optional slug→name map for
//                                  call sites that only have a slug in hand;
//                                  falls back to the slug itself.
export function displayName(
  book: { display_name?: string; slug: string } | string,
  names?: Record<string, string>,
): string {
  if (typeof book === "string") {
    return names?.[book] ?? book;
  }
  return book.display_name ?? book.slug;
}

import type { PinyinMap } from "@/components/AnnotatedText";
import type { Book } from "./api";

// titleSyllables bridges the two pinyin conventions in the codebase:
// getCharPinyinBatch returns a per-char Map (PinyinMap), but AnnotatedName
// takes one space-separated syllable per CJK char. Walk the title's CJK chars
// in order, look each up in the Map, and join the syllables. Returns undefined
// when there's no map or any CJK char is missing a reading — AnnotatedName's
// `aligned` check then degrades to bare zh (no ruby), the same honest fallback
// book titles use when name_pinyin is mis-curated.
//
// Shared by the book page chapter list and the chapter reading page, so both
// render chapter titles the same way. Pure function, no deps on React.
export function titleSyllables(zh: string, map?: PinyinMap): string | undefined {
  if (!map || map.size === 0) return undefined;
  const syllables: string[] = [];
  for (const r of Array.from(zh)) {
    const code = r.codePointAt(0)!;
    const cjk = code >= 0x4e00 && code <= 0x9fff;
    if (!cjk) continue; // non-CJK runes don't consume a syllable
    const entry = map.get(r);
    if (!entry?.pinyin) return undefined; // gap → let AnnotatedName render bare
    syllables.push(entry.pinyin);
  }
  return syllables.length > 0 ? syllables.join(" ") : undefined;
}

// findChapterTitleEn looks up a chapter's English title by its order number,
// from the catalog chapters[] carried on the Book (served by /books). The
// single-chapter endpoint doesn't return title_en — but the chapter reading
// page already fetches getBooks() for chapter_count, so this reuses that
// payload. Returns undefined when the book has no chapter data or this chapter
// has no title_en authored (the honest gap most catalogs carry today).
export function findChapterTitleEn(
  book: Pick<Book, "chapters"> | undefined,
  chapterNum: number,
): string | undefined {
  const c = book?.chapters?.find((c) => c.order === chapterNum);
  const en = c?.title_en?.trim();
  return en ? en : undefined;
}
