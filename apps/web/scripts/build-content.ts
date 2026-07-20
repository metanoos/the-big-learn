// Precompute content artifacts from the canonical content/ tree.
//
// This script ports the Go content service's startup work — book list sort +
// projection, character index loading (dual-keyed), trad→simplified map, and
// the chengyu reverse index — so the Next.js app can read prebuilt JSON at
// runtime instead of paying that cost on every serverless cold start. Chapter
// payloads are also copied into the cache so the runtime never touches the
// (132 MB) content/ tree — that tree lives outside apps/web and wouldn't ship
// with the Vercel deploy otherwise.
//
// Output (written to apps/web/.content-cache/, gitignored):
//   - books.json          → { books: Book[] }                (sorted, projected)
//   - char-index.json     → { entries: [[<rune>, CharEntry], ...],
//                              trad2simpl: [[<rune>, <rune>], ...] }
//   - chengyu-index.json  → [[<rune>, ChengyuRef[]], ...]    (capped 8/rune)
//   - chapters/<book>/<id>.json  → one per chapter, raw payload
//
// Shape parity target: services/api/internal/content/content.go +
// services/api/internal/httpapi/server.go. When in doubt, the Go behavior wins.
//
// Run via `pnpm run build:content` (also wired as a prebuild step).

import { readFile, readdir, writeFile, mkdir, copyFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Resolve the content root. Strategy:
//   1. CONTENT_ROOT env var (explicit override — recommended for Vercel).
//   2. Walk up from this script's location looking for a `content/` dir.
//      Handles monorepo layouts where the build root may differ from the
//      repo root (e.g. Vercel "Root Directory" = apps/web).
const findContentRoot = (): string => {
  let dir = __dirname;
  for (let i = 0; i < 8; i++) {
    const candidate = join(dir, "content");
    try {
      // Synchronous existence check via import.meta would be cleaner, but
      // existsSync is fine here — runs once at build start.
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { existsSync } = require("node:fs") as {
        existsSync: (p: string) => boolean;
      };
      if (existsSync(candidate)) return candidate;
    } catch {
      // ignore and keep walking
    }
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error(
    "content/ not found. Set CONTENT_ROOT to the absolute path of the content/ directory."
  );
};
const CONTENT_ROOT = process.env.CONTENT_ROOT || findContentRoot();
const OUT_DIR = join(__dirname, "..", ".content-cache");

// --- index entry shape (mirrors CharEntry in content.go) -------------------

type Analysis = { expression?: string; parts?: string[] };
type Synthesis = {
  containingCharacters?: string[];
  phraseUse?: string[];
  homophones?: { sameTone?: string[]; differentTone?: string[] };
};
type Explosion = {
  analysis?: Analysis;
  synthesis?: Synthesis;
  meaningMap?: { synonyms?: string[]; antonyms?: string[] };
};

type CharEntry = {
  character: string;
  simplified: string;
  traditional: string;
  aliases?: string[];
  pinyin?: string[];
  zhuyin?: string[];
  english?: string[];
  explosion?: Explosion;
};

type ChengyuRef = {
  text: string;
  pinyin: string;
  gloss: string;
};

// --- helpers (port of the loosely-typed catalog readers in content.go) -----

const asString = (v: unknown): string => (typeof v === "string" ? v : "");
const asInt = (v: unknown): number =>
  typeof v === "number" && Number.isFinite(v) ? Math.trunc(v) : 0;

// available defaults to true when absent — a missing flag must never hide a
// real book. Mirrors boolFromWithDefault(v, true) in content.go.
const asBoolDefaultTrue = (v: unknown): boolean => {
  if (v === null || v === undefined) return true;
  return typeof v === "boolean" ? v : true;
};

const firstNonEmpty = (...vals: string[]): string =>
  vals.find((v) => v !== "") ?? "";

// --- books list (port of Service.Books() in content.go) --------------------

type SeedTranslator = {
  translator: string;
  year?: number;
  license?: string;
};

type CatalogChapter = {
  id: string;
  order: number;
  title?: string;
  title_en?: string;
  title_en_source?: string;
  character_count?: number;
  reading_unit_count?: number;
};

type Book = {
  slug: string;
  title: string;
  chapter_count: number;
  chapters?: CatalogChapter[];
  source_title?: string;
  pedagogy_note?: string;
  blurb?: string;
  background?: string;
  seed_translator?: SeedTranslator;
  v1: boolean;
  available: boolean; // always emitted (no omitempty in Go struct)
  display_name?: string;
  name_zh?: string;
  name_pinyin?: string;
  name_en?: string;
  tradition?: string;
  form?: string;
  year?: number;
  tier?: string;
  difficulty?: string;
  curriculum_order?: number | null;
  commentary_on?: string;
};

const TIER_RANK: Record<string, number> = { S: 0, A: 1, B: 2 };

function seedTranslatorFrom(v: unknown): SeedTranslator | undefined {
  if (!v || typeof v !== "object") return undefined;
  const m = v as Record<string, unknown>;
  const translator = asString(m.translator);
  if (translator === "") return undefined;
  const out: SeedTranslator = { translator };
  const year = asInt(m.year);
  if (year) out.year = year;
  const license = asString(m.license);
  if (license) out.license = license;
  return out;
}

// catalogChapters trims the on-disk array down to the public CatalogChapter
// shape. The on-disk title is already simplified for every readable book, so
// no simplification here — parity with the Go behavior today (it runs Simplify
// idempotently). If a book's catalog is ever stored traditional, build-content
// would need to simplify here too; for now the canon is simplified on disk.
function catalogChapters(raw: unknown): CatalogChapter[] | undefined {
  if (!Array.isArray(raw) || raw.length === 0) return undefined;
  const out: CatalogChapter[] = [];
  for (const e of raw) {
    if (!e || typeof e !== "object") continue;
    const m = e as Record<string, unknown>;
    const ch: CatalogChapter = {
      id: asString(m.id),
      order: asInt(m.order),
    };
    const title = asString(m.title);
    if (title) ch.title = title;
    const titleEn = asString(m.title_en);
    if (titleEn) ch.title_en = titleEn;
    const titleEnSource = asString(m.title_en_source);
    if (titleEnSource) ch.title_en_source = titleEnSource;
    const cc = asInt(m.character_count);
    if (cc) ch.character_count = cc;
    const ruc = asInt(m.reading_unit_count);
    if (ruc) ch.reading_unit_count = ruc;
    out.push(ch);
  }
  return out.length > 0 ? out : undefined;
}

async function loadCatalog(
  book: string
): Promise<Record<string, unknown>> {
  const path = join(CONTENT_ROOT, "books", book, "catalog.json");
  const data = await readFile(path, "utf8");
  return JSON.parse(data) as Record<string, unknown>;
}

async function buildBooks(): Promise<{ books: Book[] }> {
  const dir = join(CONTENT_ROOT, "books");
  const entries = await readdir(dir, { withFileTypes: true });
  const books: Book[] = [];
  for (const e of entries) {
    if (!e.isDirectory()) continue;
    const slug = e.name;
    const cat = await loadCatalog(slug);
    const displayName = asString(cat.display_name);
    const year = asInt(cat.year);
    const b: Book = {
      slug,
      title: firstNonEmpty(displayName, asString(cat.title), slug),
      chapter_count: asInt(cat.chapter_count),
      v1: typeof cat.v1 === "boolean" ? (cat.v1 as boolean) : false,
      available: asBoolDefaultTrue(cat.available),
      chapters: catalogChapters(cat.chapters),
    };
    // Optional fields — only set when present so JSON omits them, matching Go omitempty.
    const sourceTitle = asString(cat.source_title);
    if (sourceTitle) b.source_title = sourceTitle;
    const pedagogyNote = asString(cat.pedagogy_note);
    if (pedagogyNote) b.pedagogy_note = pedagogyNote;
    const blurb = asString(cat.blurb);
    if (blurb) b.blurb = blurb;
    const background = asString(cat.background);
    if (background) b.background = background;
    const seed = seedTranslatorFrom(cat.seed_translator);
    if (seed) b.seed_translator = seed;
    if (displayName) b.display_name = displayName;
    const nameZh = asString(cat.name_zh);
    if (nameZh) b.name_zh = nameZh;
    const namePinyin = asString(cat.name_pinyin);
    if (namePinyin) b.name_pinyin = namePinyin;
    const nameEn = asString(cat.name_en);
    if (nameEn) b.name_en = nameEn;
    const tradition = asString(cat.tradition);
    if (tradition) b.tradition = tradition;
    const form = asString(cat.form);
    if (form) b.form = form;
    if (year) b.year = year;
    const tier = asString(cat.tier);
    if (tier) b.tier = tier;
    const difficulty = asString(cat.difficulty);
    if (difficulty) b.difficulty = difficulty;
    if (cat.curriculum_order === null) {
      b.curriculum_order = null;
    } else if (typeof cat.curriculum_order === "number") {
      b.curriculum_order = Math.trunc(cat.curriculum_order);
    }
    const commentaryOn = asString(cat.commentary_on);
    if (commentaryOn) b.commentary_on = commentaryOn;
    books.push(b);
  }

  // Sort: curriculum_order asc (nulls last), then tier S<A<B, then slug.
  // SortSliceStable equivalent — Node's sort is not guaranteed stable per spec
  // but V8's is, and the final slug tiebreak makes ordering deterministic
  // regardless.
  books.sort((a, b) => {
    const ao = a.curriculum_order ?? null;
    const bo = b.curriculum_order ?? null;
    if (ao !== null && bo !== null && ao !== bo) return ao - bo;
    if (ao !== null && bo === null) return -1;
    if (ao === null && bo !== null) return 1;
    const ra = TIER_RANK[a.tier ?? ""] ?? 3;
    const rb = TIER_RANK[b.tier ?? ""] ?? 3;
    if (ra !== rb) return ra - rb;
    return a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0;
  });
  return { books };
}

// --- character index (port of loadCharIndex + buildTradToSimplified) -------
//
// Keyed by both the headword (character == simplified) and the single-rune
// traditional form. Headwords win on collision — the two-pass order matters.

type CharIndex = {
  entries: Map<string, CharEntry>;
  trad2simpl: Map<string, string>;
};

async function buildCharIndex(): Promise<CharIndex> {
  const path = join(CONTENT_ROOT, "references", "characters", "index.json");
  const data = await readFile(path, "utf8");
  const payload = JSON.parse(data) as { entries: CharEntry[] };

  // First pass: headword index (character → entry).
  const headword = new Map<string, CharEntry>();
  for (const e of payload.entries) {
    if (!e.character) continue;
    const head = Array.from(e.character)[0];
    if (!head) continue;
    headword.set(head, e);
  }

  // Second pass: dual-key. Traditional forms first (lower priority), then
  // headwords overwrite on collision.
  const entries = new Map<string, CharEntry>();
  for (const e of headword.values()) {
    const trad = Array.from(e.traditional ?? "")[0];
    if (trad) entries.set(trad, e);
  }
  for (const [rune, e] of headword) {
    entries.set(rune, e);
  }

  // trad → simpl map. Includes alias forms. last-wins on collision (none in canon).
  const trad2simpl = new Map<string, string>();
  const add = (from: string | undefined, to: string | undefined) => {
    if (!from || !to) return;
    const fr = Array.from(from)[0];
    const tr = Array.from(to)[0];
    if (!fr || !tr || fr === tr) return;
    trad2simpl.set(fr, tr);
  };
  for (const e of headword.values()) {
    add(e.traditional, e.simplified);
    for (const a of e.aliases ?? []) add(a, e.simplified);
  }
  return { entries, trad2simpl };
}

// --- chengyu reverse index (port of loadChengyuReverseIndex) ---------------
//
// Walks chengyu-catalog chapters, builds rune → ChengyuRef[] capped at 8/rune.

async function buildChengyuIndex(): Promise<Map<string, ChengyuRef[]>> {
  const PER_RUNE_CAP = 8;
  const out = new Map<string, ChengyuRef[]>();

  const dir = join(CONTENT_ROOT, "books", "chengyu-catalog", "chapters");
  let files: string[];
  try {
    files = await readdir(dir);
  } catch {
    return out; // chengyu absent → empty index; not fatal
  }
  for (const f of files) {
    if (!f.endsWith(".json")) continue;
    let payload: {
      chapter?: { reading_units?: Array<{ text: string; pinyin?: string; canonical_translations?: Array<{ text: string }> }> };
    };
    try {
      payload = JSON.parse(await readFile(join(dir, f), "utf8"));
    } catch {
      continue;
    }
    for (const u of payload.chapter?.reading_units ?? []) {
      const ref: ChengyuRef = {
        text: u.text,
        pinyin: u.pinyin ?? "",
        gloss: u.canonical_translations?.[0]?.text ?? "",
      };
      const seen = new Set<string>();
      for (const r of Array.from(u.text)) {
        if (seen.has(r)) continue;
        seen.add(r);
        const list = out.get(r);
        if (list && list.length >= PER_RUNE_CAP) continue;
        if (list) list.push(ref);
        else out.set(r, [ref]);
      }
    }
  }
  return out;
}

// --- main -------------------------------------------------------------------

async function main() {
  console.log(`[build-content] CONTENT_ROOT=${CONTENT_ROOT}`);
  await mkdir(OUT_DIR, { recursive: true });

  console.log("[build-content] building books.json…");
  const books = await buildBooks();
  await writeFile(join(OUT_DIR, "books.json"), JSON.stringify(books));
  console.log(`  → ${books.books.length} books`);

  console.log("[build-content] building char-index.json…");
  const charIdx = await buildCharIndex();
  // Map → array form for JSON. Re-key on load.
  await writeFile(
    join(OUT_DIR, "char-index.json"),
    JSON.stringify({
      entries: Array.from(charIdx.entries.entries()),
      trad2simpl: Array.from(charIdx.trad2simpl.entries()),
    })
  );
  console.log(`  → ${charIdx.entries.size} char entries`);

  console.log("[build-content] building chengyu-index.json…");
  const chengyu = await buildChengyuIndex();
  await writeFile(
    join(OUT_DIR, "chengyu-index.json"),
    JSON.stringify(Array.from(chengyu.entries()))
  );
  console.log(`  → ${chengyu.size} char → idiom entries`);

  console.log("[build-content] copying chapter payloads…");
  const copied = await copyChapters();
  console.log(`  → ${copied} chapter files`);

  console.log("[build-content] done.");
}

// Copy every book's chapters/*.json into the cache so the runtime can read
// chapters without the (large, external) content/ tree. The on-disk payload
// stays as-is — simplification is applied at read time in @/lib/content, same
// as the Go server's chapterSimplified() step.
async function copyChapters(): Promise<number> {
  let count = 0;
  const booksDir = join(CONTENT_ROOT, "books");
  const books = await readdir(booksDir, { withFileTypes: true });
  for (const b of books) {
    if (!b.isDirectory()) continue;
    const chDir = join(booksDir, b.name, "chapters");
    let files: string[];
    try {
      files = await readdir(chDir);
    } catch {
      continue; // stub book with no chapters
    }
    const dest = join(OUT_DIR, "chapters", b.name);
    await mkdir(dest, { recursive: true });
    for (const f of files) {
      if (!f.endsWith(".json")) continue;
      await copyFile(join(chDir, f), join(dest, f));
      count++;
    }
  }
  return count;
}

main().catch((err) => {
  console.error("[build-content] failed:", err);
  process.exit(1);
});
