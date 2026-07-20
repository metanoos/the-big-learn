// API client for the read-only Go content service: books, chapters, character
// breakdowns, and batch pinyin.
//
// All reader state lives in localStorage — see lib/progress.ts and
// lib/reviewChars.ts. The server keeps no database or reader identifiers.
//
// Base URL handling:
//   - In the browser: same-origin "/api/v1" (Next.js rewrites /api/* to the
//     Go backend — see next.config.js).
//   - In server components / route handlers: relative URLs don't work (no
//     host), so we use the absolute API_BASE_URL env var, defaulting to the
//     local dev backend.
const BASE =
  typeof window === "undefined"
    ? `${process.env.API_BASE_URL || "http://localhost:8180"}/api/v1`
    : "/api/v1";

// Per-chapter metadata from a book's catalog `chapters` array — the lightweight
// info the chapter list needs (id, order, title) without loading each chapter
// file. title_en is wired through today but not yet authored in any catalog, so
// it renders nothing until data lands.
export type CatalogChapter = {
  id: string;
  order: number;
  title?: string;
  title_en?: string;
  // Provenance discriminant for title_en, mirroring the CanonicalTranslation
  // source convention: "human" for rule-derived/hand-authored, "llm" for
  // GLM-generated. Recorded for audit honesty; not surfaced as a UI badge.
  title_en_source?: "human" | "llm";
  character_count?: number;
  reading_unit_count?: number;
};

export type Book = {
  slug: string;
  title: string;
  chapter_count: number;
  // Per-chapter entries from the catalog, used by the book page chapter list to
  // render titled rows. Absent on placeholder stubs with no chapter files.
  chapters?: CatalogChapter[];
  source_title?: string;
  pedagogy_note?: string;
  // Short one-line description (used on cards / as background fallback) and
  // the longer "about this book" paragraph for the book page. Both optional;
  // both passed through verbatim from catalog.json by the backend.
  blurb?: string;
  background?: string;
  // Optional catalog-level attribution. Books with mixed sources or no
  // English seed omit this and explain provenance in their background copy.
  seed_translator?: {
    translator: string;
    year?: number;
    license?: string;
  };
  v1: boolean;
  // False on placeholder stubs (catalog exists, content not yet ingested).
  // Defaults to true when absent so older catalogs render as readable.
  available?: boolean;
  // Two-facet taxonomy — see content/TAXONOMY.md. All optional because the
  // library UI treats them as plain data; an older catalog without them
  // still renders (just without grouping/badges).
  display_name?: string;
  // Structured name parts for ruby rendering (see BookTitle component):
  // name_zh = Chinese, name_pinyin = one space-separated syllable per CJK
  // char (aligned by index), name_en = established English name.
  name_zh?: string;
  name_pinyin?: string;
  name_en?: string;
  tradition?: string;
  form?: string;
  year?: number;
  // Editorial era label for card display (e.g. "Tang", "Spring & Autumn").
  // When unset, the UI derives an era from `year`. Set explicitly when `year`
  // reflects publication/translation rather than content era — e.g. Tang 300
  // (anthology compiled 1763, but the poems are Tang) or Shi Jing (the `year`
  // field is Legge's 1879 translation, the odes are pre-Qin).
  era?: string;
  tier?: string;
  difficulty?: string;
  curriculum_order?: number | null;
  // For commentaries: the slug of the parent text this comments on. Currently
  // Zuozhuan → chun-qiu. Renders as "commentary on <parent name>" on the card
  // so a commentary isn't mistaken for a standalone classic.
  commentary_on?: string;
};

export type CanonicalTranslation = {
  translator: string;
  year?: number;
  license: string;
  source_url: string;
  text: string;
  // Provenance discriminant: omitted (or "human") = human-authored canon;
  // "llm" = machine-generated. The reader relies on the byline
  // (translator · year · license) to disclose the latter, rather than a
  // separate badge, so generated text is never mistaken for authoritative
  // canon.
  source?: "human" | "llm";
};

// A multi-char compound (or single-char fallback) within a reading unit's
// text, with its pinyin + gloss. Built by tools/build_word_gloss.py via
// layered longest-match segmentation (curated classical overrides → CC-CEDICT
// → per-char). start/end are rune indices into the unit's `text`, matching
// the pinyin_per_char alignment contract; non-CJK runes are never covered.
// The reader uses this to surface the *token* a clicked char belongs to, on
// top of the per-char breakdown.
export type WordSpan = {
  start: number;
  end: number; // exclusive
  word: string;
  pinyin: string | null; // tone-marked, space-separated; null for per-char fallback
  gloss: string | null; // null for per-char fallback (char breakdown covers it)
  source: "classical-override" | "CC-CEDICT" | "char";
};

export type ReadingUnit = {
  id: string;
  order: number;
  text: string;
  pinyin?: string;
  pinyin_source?: string;
  // One pinyin syllable per rune in `text`, context-disambiguated at build
  // time (with tone sandhi). Empty string for non-CJK runes or unknown chars.
  // When present and matching the rune count, the reader prefers this over the
  // per-char fallback map so polyphones/sandhi render correctly in context.
  pinyin_per_char?: string[];
  // Word-level segmentation of `text` into compounds with glosses. Optional:
  // chengyu-catalog units and any unit the build hasn't enriched render with
  // the legacy per-char-only click behavior.
  word_spans?: WordSpan[];
  character_count: number;
  canonical_translations: CanonicalTranslation[];
  // Optional origin link for chengyu units whose 4-char source is coined
  // verbatim in a classical book we ship. Built by tools/attach_chengyu_origins.py.
  // Absent on classical-book units and on chengyu with no verbatim origin
  // (honest gap — coverage is partial). When present, the reader shows a
  // link to the source line.
  origin?: {
    book: string;       // slug, e.g. "lunyu"
    chapter: number;    // bare integer, matches /books/<book>/<chapter>#line-<line>
    line: number;       // the origin unit's order
    snippet?: string;   // ~80-char context, so the card needs no round-trip
  };
};

export type Chapter = {
  chapter: {
    id: string;
    order: number;
    title: string;
    summary: string;
    text: string;
    character_count: number;
    reading_unit_count: number;
    reading_units: ReadingUnit[];
  };
  provider: string;
  source_title: string;
  source_url: string;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.error || res.statusText);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// --- content (anonymous) ---------------------------------------------------

export const getBooks = async (): Promise<Book[]> => {
  const response = await req<Book[] | { books: Book[] }>("/books");
  return Array.isArray(response) ? response : response.books;
};
export const getChapter = (book: string, chapter: number | string) =>
  req<Chapter>(`/books/${book}/chapters/${chapter}`);

// --- characters (popover breakdown + batch pinyin) -------------------------

export type ChengyuRef = {
  text: string;
  pinyin: string;
  gloss: string;
};

export type CharacterDetails = {
  character: string; // simplified form (the index headword)
  traditional?: string; // traditional form, shown as the popover headline
  pinyin: string[];
  english: string[];
  decomposition?: { expression: string; parts: string[] };
  phrases?: { classical: string[]; chengyu: ChengyuRef[] };
};

// Pinyin for a single char: null when the char isn't in the index (honest gap,
// no fake annotation). has_entry mirrors the backend so callers can distinguish
// "no pinyin recorded" from "char unknown to the index".
export type CharPinyinEntry = { pinyin: string | null; has_entry: boolean };

export const getCharacter = (char: string) =>
  req<CharacterDetails>(`/characters/${encodeURIComponent(char)}`);

export const getCharPinyinBatch = async (
  chars: string[],
): Promise<Map<string, CharPinyinEntry>> => {
  const res = await req<Record<string, CharPinyinEntry>>(
    "/characters/batch",
    { method: "POST", body: JSON.stringify({ chars }) },
  );
  return new Map(Object.entries(res));
};
