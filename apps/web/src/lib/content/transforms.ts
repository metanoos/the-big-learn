// Pure transforms used by the content layer — projection + simplification.
// Ported from services/api/internal/content/content.go and server.go so the
// TS reader returns the same JSON shapes the Go service did.
//
// Kept side-effect-free so it's safe to call from server components and route
// handlers alike.

// --- types (kept here so @/lib/content/index.ts can re-export them) --------

export type CatalogChapter = {
  id: string;
  order: number;
  title?: string;
  title_en?: string;
  title_en_source?: "human" | "llm";
  character_count?: number;
  reading_unit_count?: number;
};

export type Book = {
  slug: string;
  title: string;
  chapter_count: number;
  chapters?: CatalogChapter[];
  source_title?: string;
  pedagogy_note?: string;
  blurb?: string;
  background?: string;
  seed_translator?: { translator: string; year?: number; license?: string };
  v1: boolean;
  available?: boolean;
  display_name?: string;
  name_zh?: string;
  name_pinyin?: string;
  name_en?: string;
  tradition?: string;
  form?: string;
  year?: number;
  era?: string;
  tier?: string;
  difficulty?: string;
  curriculum_order?: number | null;
  commentary_on?: string;
};

export type CanonicalTranslation = {
  translator: string;
  year?: number;
  license: string;
  source_url: string;
  text: string;
  source?: "human" | "llm";
};

export type WordSpan = {
  start: number;
  end: number;
  word: string;
  pinyin?: string | null;
  gloss?: string | null;
  source?: "classical-override" | "CC-CEDICT" | "char";
};

export type ReadingUnit = {
  id: string;
  order: number;
  text: string;
  pinyin?: string;
  pinyin_source?: string;
  pinyin_per_char?: string[];
  word_spans?: WordSpan[];
  character_count: number;
  canonical_translations: CanonicalTranslation[];
  origin?: {
    book: string;
    chapter: number;
    line: number;
    snippet?: string;
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
  schema_version?: number;
};

export type CharacterDetails = {
  character: string;
  traditional?: string;
  pinyin: string[];
  english: string[];
  decomposition?: { expression: string; parts: string[] };
  phrases?: {
    classical: string[];
    chengyu: { text: string; pinyin: string; gloss: string }[];
  };
};

export type CharPinyinEntry = { pinyin: string | null; has_entry: boolean };

// --- simplification --------------------------------------------------------
//
// Each rune mapped through trad2simpl; unmapped runes pass through. Identity
// returns the input string (avoid an alloc), matching content.go Simplify().

export function simplify(
  str: string,
  trad2simpl: Map<string, string>
): string {
  if (!trad2simpl || trad2simpl.size === 0) return str;
  const runes = Array.from(str);
  let changed = false;
  for (let i = 0; i < runes.length; i++) {
    const s = trad2simpl.get(runes[i]);
    if (s !== undefined) {
      runes[i] = s;
      changed = true;
    }
  }
  return changed ? runes.join("") : str;
}

// --- chapter ID normalization (port of normalizeChapterID in server.go) ----
//
// "1" → "chapter-001", "chapter-001" → unchanged, "" → "chapter-001".

export function normalizeChapterID(input: string): string {
  const s = input.trim();
  if (s === "") return "chapter-001";
  if (s.startsWith("chapter-")) return s;
  const n = parseIntSafe(s);
  if (n > 0) return `chapter-${pad3(n)}`;
  return s;
}

function parseIntSafe(s: string): number {
  let n = 0;
  let any = false;
  for (const c of s) {
    if (c < "0" || c > "9") return 0;
    n = n * 10 + (c.charCodeAt(0) - "0".charCodeAt(0));
    any = true;
  }
  return any ? n : 0;
}

function pad3(n: number): string {
  if (n < 10) return "00" + n;
  if (n < 100) return "0" + n;
  return String(n);
}

// --- chapter projection (parity with Go struct field set + omitempty) ------
//
// The on-disk chapter JSON carries extra fields the Go service's structs don't
// model (source_block_chunk, supplemental_*, etc.) and would otherwise leak
// through a naive passthrough. These projectors keep only the public contract
// and apply Go-style omitempty: empty strings and 0-length arrays drop.

type RawCanonicalTranslation = {
  translator: string;
  year?: number;
  license: string;
  source_url: string;
  text: string;
  source?: "human" | "llm";
};

type RawWordSpan = {
  start: number;
  end: number;
  word: string;
  pinyin?: string | null;
  gloss?: string | null;
  source?: string;
};

type RawUnitOrigin = {
  book: string;
  chapter: number;
  line: number;
  snippet?: string;
};

type RawReadingUnit = {
  id: string;
  order: number;
  text: string;
  pinyin?: string;
  pinyin_source?: string;
  pinyin_per_char?: string[];
  character_count: number;
  canonical_translations?: RawCanonicalTranslation[];
  word_spans?: RawWordSpan[];
  origin?: RawUnitOrigin;
};

function projectCanonicalTranslation(
  raw: RawCanonicalTranslation
): CanonicalTranslation {
  const out: CanonicalTranslation = {
    translator: raw.translator,
    license: raw.license,
    source_url: raw.source_url,
    text: raw.text,
  };
  if (raw.year) out.year = raw.year;
  if (raw.source) out.source = raw.source;
  return out;
}

function projectWordSpan(raw: RawWordSpan): WordSpan {
  const out: WordSpan = { start: raw.start, end: raw.end, word: raw.word };
  // Go omitempty: pinyin/gloss drop when empty string. The disk stores null
  // for the per-char fallback; treat null and "" the same (omit).
  if (raw.pinyin) out.pinyin = raw.pinyin;
  if (raw.gloss) out.gloss = raw.gloss;
  if (raw.source) out.source = raw.source as WordSpan["source"];
  return out;
}

export function projectReadingUnit(raw: RawReadingUnit): ReadingUnit {
  const out: ReadingUnit = {
    id: raw.id,
    order: raw.order,
    text: raw.text,
    character_count: raw.character_count,
    canonical_translations:
      raw.canonical_translations?.map(projectCanonicalTranslation) ?? [],
  };
  if (raw.pinyin) out.pinyin = raw.pinyin;
  if (raw.pinyin_source) out.pinyin_source = raw.pinyin_source;
  if (raw.pinyin_per_char && raw.pinyin_per_char.length > 0) {
    out.pinyin_per_char = raw.pinyin_per_char;
  }
  if (raw.word_spans && raw.word_spans.length > 0) {
    out.word_spans = raw.word_spans.map(projectWordSpan);
  }
  if (raw.origin) {
    const o: ReadingUnit["origin"] = {
      book: raw.origin.book,
      chapter: raw.origin.chapter,
      line: raw.origin.line,
    };
    if (raw.origin.snippet) o.snippet = raw.origin.snippet;
    out.origin = o;
  }
  return out;
}
