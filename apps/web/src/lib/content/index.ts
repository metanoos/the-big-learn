// Content layer: replaces the Go content service with direct on-disk reads.
//
// This module is a drop-in replacement for the old fetch-based @/lib/api —
// same exported names, same types, same behavior. It reads prebuilt artifacts
// from .content-cache/ (produced by scripts/build-content.ts at prebuild) for
// the book list and character indexes, and reads raw chapter JSON from
// content/ at request time. Server components and route handlers call these
// functions directly; client components go through the route handlers under
// /api/v1/ which call the same functions.
//
// Shape parity target: services/api/internal/httpapi/server.go.

import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { existsSync } from "node:fs";

import {
  simplify,
  normalizeChapterID,
  projectReadingUnit,
  type Book,
  type Chapter,
  type ReadingUnit,
  type WordSpan,
  type CatalogChapter,
  type CharacterDetails,
  type CharPinyinEntry,
} from "./transforms";

// Re-export every type the old @/lib/api exposed so call sites that import
// types from "@/lib/api" keep compiling unchanged.
export type {
  Book,
  Chapter,
  ReadingUnit,
  WordSpan,
  CatalogChapter,
  CharacterDetails,
  CharPinyinEntry,
};

// ApiError mirrors the old client: a thrown Error carrying an HTTP status.
// Route handlers use it to produce the right status code; server components
// can `instanceof ApiError` to branch on 404 (see the chapter page).
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// --- content root + cache paths --------------------------------------------
//
// All runtime reads come from the build cache under apps/web/.content-cache/
// (written by scripts/build-content.ts at prebuild). The cache lives inside
// the app so it ships with the deploy; the raw content/ tree (132 MB, outside
// apps/web) is never touched at runtime — it's a build-time input only.
//
// CONTENT_CACHE_DIR override exists for tests / unusual layouts. CONTENT_ROOT
// is no longer read at runtime but kept exported for diagnostics.

const WEB_ROOT = process.cwd(); // apps/web when Next runs from there
const CACHE_DIR =
  process.env.CONTENT_CACHE_DIR || join(WEB_ROOT, ".content-cache");
const CONTENT_ROOT =
  process.env.CONTENT_ROOT || join(WEB_ROOT, "..", "..", "content");

// --- lazy-loaded indexes (module-level singletons) -------------------------

type CharEntry = {
  character: string;
  simplified: string;
  traditional: string;
  aliases?: string[];
  pinyin?: string[];
  english?: string[];
  explosion?: {
    analysis?: { expression?: string; parts?: string[] };
    synthesis?: { phraseUse?: string[] };
  };
};

type ChengyuRef = { text: string; pinyin: string; gloss: string };

type CharIndexData = {
  entries: Map<string, CharEntry>;
  trad2simpl: Map<string, string>;
};

type Cache = {
  books?: Book[];
  charIndex?: CharIndexData | null;
  chengyu?: Map<string, ChengyuRef[]>;
  chapterLRU?: Map<string, Chapter>;
};

const globalForCache = globalThis as typeof globalThis & {
  __contentCache?: Cache;
};
const cache: Cache = globalForCache.__contentCache ?? (globalForCache.__contentCache = {});

async function readJSON<T>(path: string): Promise<T> {
  return JSON.parse(await readFile(path, "utf8")) as T;
}

// --- books -----------------------------------------------------------------

async function loadBooks(): Promise<Book[]> {
  if (cache.books) return cache.books;
  try {
    const { books } = await readJSON<{ books: Book[] }>(
      join(CACHE_DIR, "books.json")
    );
    cache.books = books;
    return books;
  } catch (err) {
    throw new ApiError(
      500,
      `content cache missing: run \`pnpm build:content\` (${(err as Error).message})`
    );
  }
}

// --- character + chengyu indexes ------------------------------------------

async function loadCharIndex(): Promise<CharIndexData | null> {
  if (cache.charIndex !== undefined) return cache.charIndex;
  try {
    const raw = await readJSON<{
      entries: [string, CharEntry][];
      trad2simpl: [string, string][];
    }>(join(CACHE_DIR, "char-index.json"));
    cache.charIndex = {
      entries: new Map(raw.entries),
      trad2simpl: new Map(raw.trad2simpl),
    };
  } catch {
    // No cache → no pinyin. Chapter pages still render; the popover 404s.
    cache.charIndex = null;
  }
  return cache.charIndex;
}

async function loadChengyuIndex(): Promise<Map<string, ChengyuRef[]>> {
  if (cache.chengyu !== undefined) return cache.chengyu;
  try {
    const raw = await readJSON<[string, ChengyuRef[]][]>(
      join(CACHE_DIR, "chengyu-index.json")
    );
    cache.chengyu = new Map(raw);
  } catch {
    cache.chengyu = new Map();
  }
  return cache.chengyu;
}

// --- chapter loading (cache reads) -----------------------------------------
//
// Chapters are prebuilt into .content-cache/chapters/<book>/<id>.json by
// scripts/build-content.ts. The on-disk payload carries extra fields the Go
// service dropped (supplemental_text, source_block_*, etc.); we accept the
// loose shape and project to the public Chapter contract, then simplify on
// response — same two-step the Go server did (Chapter() then chapterSimplified()).

type RawChapter = {
  chapter?: {
    id?: string;
    order?: number;
    title?: string;
    summary?: string;
    text?: string;
    character_count?: number;
    reading_unit_count?: number;
    reading_units?: ReadingUnit[];
  };
  provider?: string;
  source_title?: string;
  source_url?: string;
  schema_version?: number;
};

const chapterLRU = (): Map<string, Chapter> =>
  (cache.chapterLRU ??= new Map());

async function loadChapter(
  book: string,
  chapterID: string
): Promise<Chapter> {
  const fileID = normalizeChapterID(chapterID);
  const key = `${book}/${fileID}`;
  const lru = chapterLRU();
  const hit = lru.get(key);
  if (hit) return hit;

  let raw: RawChapter;
  try {
    raw = await readJSON<RawChapter>(
      join(CACHE_DIR, "chapters", book, `${fileID}.json`)
    );
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") {
      throw new ApiError(404, "chapter not found");
    }
    throw new ApiError(500, `failed to load chapter: ${(err as Error).message}`);
  }
  const ch = raw.chapter ?? {
    id: fileID,
    order: 0,
    title: "",
    summary: "",
    text: "",
    character_count: 0,
    reading_unit_count: 0,
    reading_units: [],
  };
  // Simplify the response. Same scope as server.go chapterSimplified:
  // title, summary, and each reading unit's text. The trad2simpl map is a
  // no-op when the cache isn't loaded (canon on disk is already simplified).
  // Each unit is projected to the public field set (drops source_block_*, the
  // disk-only supplemental_*, and applies Go omitempty) — same filtering the
  // Go struct does by not modeling those fields.
  const idx = await loadCharIndex();
  const t2s = idx?.trad2simpl ?? new Map<string, string>();
  const simplifiedUnits =
    ch.reading_units?.map((u) => {
      const projected = projectReadingUnit(u);
      projected.text = simplify(projected.text, t2s);
      return projected;
    }) ?? [];
  const out: Chapter = {
    chapter: {
      id: ch.id ?? fileID,
      order: ch.order ?? 0,
      title: simplify(ch.title ?? "", t2s),
      summary: simplify(ch.summary ?? "", t2s),
      text: ch.text ?? "",
      character_count: ch.character_count ?? 0,
      reading_unit_count: ch.reading_unit_count ?? 0,
      reading_units: simplifiedUnits,
    },
    provider: raw.provider ?? "",
    source_title: raw.source_title ?? "",
    source_url: raw.source_url ?? "",
    ...(raw.schema_version !== undefined
      ? { schema_version: raw.schema_version }
      : {}),
  };
  // Bound the LRU so a long-lived serverless instance doesn't grow unbounded.
  if (lru.size > 64) lru.clear();
  lru.set(key, out);
  return out;
}

// --- public API (drop-in for the old @/lib/api) ----------------------------

export const getBooks = async (): Promise<Book[]> => loadBooks();

export const getChapter = async (
  book: string,
  chapter: number | string
): Promise<Chapter> => loadChapter(book, String(chapter));

// getCharacter mirrors server.go handleCharacter: project the index entry
// into the flat popover contract, attach up to 5 chengyu refs, and omit
// decomposition/phrases when empty (omitempty parity).
export async function getCharacter(char: string): Promise<CharacterDetails> {
  const runes = Array.from(char);
  if (runes.length === 0) throw new ApiError(400, "empty character");
  const r = runes[0];
  const idx = await loadCharIndex();
  if (!idx) throw new ApiError(404, "character not in index");
  const entry = idx.entries.get(r);
  if (!entry) throw new ApiError(404, "character not in index");

  const resp: CharacterDetails = {
    character: entry.character,
    pinyin: entry.pinyin ?? [],
    english: entry.english ?? [],
  };
  if (entry.traditional) resp.traditional = entry.traditional;

  if (entry.explosion) {
    const a = entry.explosion.analysis;
    if (a && (a.expression || (a.parts && a.parts.length > 0))) {
      resp.decomposition = {
        expression: a.expression ?? "",
        parts: a.parts ?? [],
      };
    }
    const classicalRaw = entry.explosion.synthesis?.phraseUse ?? [];
    const classical = classicalRaw.map((p) => simplify(p, idx.trad2simpl));
    const chengyuIdx = await loadChengyuIndex();
    const refs = (chengyuIdx.get(r) ?? []).slice(0, 5).map((ref) => ({
      text: ref.text,
      pinyin: ref.pinyin,
      gloss: ref.gloss,
    }));
    if (classical.length > 0 || refs.length > 0) {
      resp.phrases = { classical, chengyu: refs };
    }
  }
  return resp;
}

// getCharPinyinBatch mirrors server.go handleCharacterBatch: dedup runes,
// cap at 2000, return first pinyin or null per char.
export async function getCharPinyinBatch(
  chars: string[]
): Promise<Map<string, CharPinyinEntry>> {
  const out = new Map<string, CharPinyinEntry>();
  if (chars.length > 2000) {
    throw new ApiError(400, "too many chars (max 2000)");
  }
  const idx = await loadCharIndex();
  if (!idx) return out; // no cache → no pinyin; caller renders bare text
  const seen = new Set<string>();
  for (const c of chars) {
    for (const r of Array.from(c)) {
      if (seen.has(r)) continue;
      seen.add(r);
      const entry = idx.entries.get(r);
      if (entry && entry.pinyin && entry.pinyin.length > 0) {
        out.set(r, { pinyin: entry.pinyin[0], has_entry: true });
      } else {
        out.set(r, { pinyin: null, has_entry: false });
      }
    }
  }
  return out;
}

// Health-check helper, exposed for any future /api/v1/health route. Not used
// by the reader today but keeps parity with the Go service's contract.
export async function isHealthy(): Promise<boolean> {
  return existsSync(join(CACHE_DIR, "books.json"));
}

// Exported for tests and for route handlers that need the raw trad2simpl map.
export const __internal = { CACHE_DIR, CONTENT_ROOT, loadCharIndex };
