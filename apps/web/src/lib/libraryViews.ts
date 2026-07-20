// Curriculum grouping + facet labels — pure logic, no React.
//
// The library is one curated reading path, split into named sections (Four
// Books → Daoist → Five Classics → …). The earlier view-toggle is gone: the
// catalog is small enough to read as a single curated curriculum, and the
// toggle was the source of the mess. Facets (tradition/tier/year/form)
// survive as card tags, not whole views.
//
// Sections are NOT a catalog field — they're derived from existing facets +
// slug sets here, so the schema stays clean. See content/TAXONOMY.md.

import type { Book } from "./api";

// Canonical vocabularies — only used now by facetLabel() for rendering card
// tags. Order no longer matters for grouping (there are no group-by-facet
// views), but the labels are the single source for pretty-printing facet
// values anywhere they appear.
const TRADITION_LABEL: Record<string, string> = {
  confucian: "Confucian",
  daoist:    "Daoist",
  buddhist:  "Buddhist",
  secular:   "Secular",
};
// `form` is the genre of the text. Philosophy covers argumentative/expository
// prose across traditions — the 子 (Mengzi, Han Feizi, Zhuangzi) and the
// philosophical 经 (Lunyu, Daodejing, the Buddhist sutras), since a sutra is a
// philosophical text and `tradition: buddhist` already marks the lineage.
// History is 史; ritual/divination are specialist 经; poetry/prose-fiction/
// primer/idiom/strategy-treatise are self-explanatory. The earlier catch-all
// "classic" was a status word, not a genre — it sat inconsistently next to
// genre words and lumped Lunyu with Zhou Yi.
const FORM_LABEL: Record<string, string> = {
  "philosophy":        "Philosophy",
  "history":           "History",
  "ritual":            "Ritual",
  "divination":        "Divination",
  "poetry":            "Poetry",
  "prose-fiction":     "Prose fiction",
  "primer":            "Primer",
  "idiom":             "Idiom catalog",
  "strategy-treatise": "Strategy",
};

// Format a composition year (negative = BCE) for card tags, with the era
// appended when known. Year is a scholarly-consensus approximation — the
// underlying texts often took shape over centuries, so this is a single
// representative point, not a precise publication date. The era is the
// dynasty or period label a Chinese reader would use ("Tang", "Ming");
// it is taken from the book's explicit `era` field when set (for books
// whose `year` is a publication/translation date rather than content era —
// Tang 300, Shi Jing), and otherwise derived from `year`.
export function formatYear(year: number | undefined, eraOverride?: string): string {
  if (!year && !eraOverride) return "";
  const era = eraOverride ?? eraForYear(year);
  const yr = year
    ? (year < 0 ? `${-year} BCE` : `${year} CE`)
    : "";
  return [yr, era].filter(Boolean).join(" · ");
}

// Map a year to its Chinese era label. Boundaries are scholarly consensus
// approximations — the same caveat as `year` itself. Pre-Qin is split into
// the periods readers actually use (Spring & Autumn vs. Warring States)
// rather than lumped, because the corpus clusters there.
export function eraForYear(year: number | undefined): string {
  if (year === undefined) return "";
  if (year < -770) return "Western Zhou";
  if (year < -475) return "Spring & Autumn";
  if (year < -221) return "Warring States";
  if (year < 220)  return "Qin–Han";
  if (year < 589)  return "Six Dynasties";
  if (year < 618)  return "Sui";
  if (year < 907)  return "Tang";
  if (year < 960)  return "Five Dynasties";
  if (year < 1279) return "Song";
  if (year < 1368) return "Yuan";
  if (year < 1644) return "Ming";
  if (year < 1912) return "Qing";
  return "Modern";
}


// --- Curriculum sections ----------------------------------------------------

// The Five Classics as a slug set (the 五经 + Zuozhuan, which is the canonical
// Chun Qiu commentary and is read alongside it).
const FIVE_CLASSICS = new Set([
  "shi-jing", "zhou-yi", "shang-shu", "li-ji", "chun-qiu", "zuozhuan",
]);
// The Four Books (四书), set explicitly so the section is unambiguous.
const FOUR_BOOKS = new Set(["da-xue", "zhong-yong", "lunyu", "mengzi"]);
// Confucian Masters outside the Four Books canon — pre-Qin (Xunzi), Han
// (Dong Zhongshu), and Song/Ming Neo-Confucians (Zhu Xi, Wang Yangming).
// The last three are reserved placeholders; slots land in chronological order.
const CONFUCIAN_MASTERS = new Set([
  "xunzi", "dong-zhongshu", "zhu-xi", "wang-yangming",
]);

export type CurriculumSection = {
  id: string;
  // Structured section name, same shape as a book name: zh chars render with
  // pinyin ruby above, English follows after a middle dot (see AnnotatedName).
  // Pinyin is space-separated, one syllable per CJK char — sourced from the
  // project's own char index (content/references/characters/index.json), with
  // the one context-specific override 著 zhù in 四大名著 (the index's generic
  // reading is the aspectual zhe).
  name_en: string;
  name_zh?: string;
  name_pinyin?: string;
  intro: string;       // one-line (or short paragraph for Four Books)
};

// Ordered. The matcher (sectionForBook) walks this list and assigns each book
// to the FIRST section that claims it, so order is significant — Four Books
// before Daoist before Five Classics resolves the overlaps.
export const CURRICULUM_SECTIONS: CurriculumSection[] = [
  {
    id: "four-books",
    name_en: "The Four Books",
    name_zh: "四书",
    name_pinyin: "sì shū",
    intro:
      "The Confucian core. Confucius — teaching in the fifth century BCE, " +
      "before China was China — shaped the civilization as deeply as Jesus " +
      "shaped the West. His students' notes became the Lunyu (Analects); his " +
      "follower Mencius extended the work into ethics, learning, and rule. " +
      "Da Xue and Zhong Yong are short on-ramps — a few pages each on how to " +
      "learn and how to stay centered; Lunyu and Mengzi are the heavy hitters.",
  },
  {
    id: "daoist",
    name_en: "Daoist Classics",
    name_zh: "道家",
    name_pinyin: "dào jiā",
    intro:
      "Confucianism's complement and reply. Where Confucius asks how to live " +
      "in the world, Daoism asks why you'd want to — the Daodejing in " +
      "compressed riddles, Zhuangzi in wild parables, Liezi in gentler tales.",
  },
  {
    id: "buddhist",
    name_en: "Buddhist Sutras",
    name_zh: "佛经",
    name_pinyin: "fó jīng",
    intro:
      "The one import in this library. Buddhism reached China from India " +
      "around the first century CE, traveling the Silk Road with monks and " +
      "a Sanskrit corpus that was translated into Chinese over the centuries " +
      "that followed — a rendering effort so large it reshaped the Chinese " +
      "language itself. The Diamond and Heart sutras are the two that anchored " +
      "Chan (Japanese: Zen).",
  },
  {
    id: "five-classics",
    name_en: "The Five Classics",
    name_zh: "五经",
    name_pinyin: "wǔ jīng",
    intro:
      "The older canon the Four Books were an on-ramp to — poetry (Shi Jing), " +
      "oracles (Zhou Yi), ritual (Li Ji), and history (Chun Qiu and its " +
      "commentary, Zuozhuan). These are the sources Confucius himself taught from.",
  },
  {
    id: "confucian-masters",
    name_en: "Confucian Masters",
    name_zh: "儒家诸子",
    name_pinyin: "rú jiā zhū zǐ",
    intro:
      "Confucian philosophers outside the Song-era Four Books canon. Xunzi — " +
      "the third of the great early Confucians, after Confucius and Mencius — " +
      "is the one carried here. He argued against Mencius that human nature is " +
      "bad (性恶) and only the deliberate artifice of ritual (礼) makes us " +
      "decent. Zhu Xi's Song compilers built the Four Books around Mencius and " +
      "left Xunzi out on exactly this point, so he stands in a peer section, " +
      "not the core.",
  },
  {
    id: "poetry",
    name_en: "Poetry",
    name_zh: "诗词",
    name_pinyin: "shī cí",
    intro:
      "The verse tradition beside the Shi Jing's northern odes — Qu Yuan's " +
      "laments in the Chu Ci (the southern source, tier A alongside the Shi " +
      "Jing), then the Tang poets at their peak. Both are anthologies, not " +
      "single works: the Chu Ci gathered Qu Yuan and his imitators; the Tang " +
      "300 collects Li Bai, Du Fu, Wang Wei, and dozens more. Future verse " +
      "(Song ci, Yuefu) lands here as it ships.",
  },
  {
    id: "novels",
    name_en: "Four Great Classical Novels",
    name_zh: "四大名著",
    name_pinyin: "sì dà zhù míng",
    intro:
      "The closed canon of Chinese vernacular fiction, four Ming- and Qing-era " +
      "novels every Chinese reader knows as a set. Sanguo Yanyi (Three " +
      "Kingdoms) and Xiyou Ji (Journey to the West) are carried now; Shui Hu " +
      "Zhuan (Water Margin) and Hong Lou Meng (Dream of the Red Chamber) are " +
      "the two still to come. The slots are reserved in canonical order below.",
  },
  {
    id: "statecraft",
    name_en: "Statecraft & Strategy",
    name_zh: "兵政",
    name_pinyin: "bīng zhèng",
    intro:
      "On war, law, and the holding of power. Sunzi on the strategy of force; " +
      "Han Feizi on law (法) as the reliable corrective for bad human nature — " +
      "Xunzi's premise pursued past ritual to coercion (see Confucian Masters " +
      "above).",
  },
  {
    id: "primers",
    name_en: "Primers",
    name_zh: "蒙学",
    name_pinyin: "méng xué",
    intro:
      "Children's primers — the verse textbooks a child memorized before " +
      "touching the classics. San Zi Jing packs a Confucian worldview into " +
      "three-character lines; Qian Zi Wen is a thousand non-repeating " +
      "characters in rhyme, written as a literacy copybook for a prince. " +
      "They were the front door to the rest of this library.",
  },
  {
    id: "reference",
    name_en: "Reference",
    name_zh: "参考",
    name_pinyin: "cān kǎo",
    intro:
      "Not a classic text but the project's own reference layer. The Chengyu " +
      "Catalog sits over the rest of the library: roughly a thousand idioms, " +
      "each linked back to the line where it was coined when that source ships " +
      "here — so a reader on 见贤思齐 jumps to Lunyu 4:22. It grows as more " +
      "classical texts are ingested.",
  },
];

// Assign a book to its curriculum section. Priority-ordered: the first
// matching rule wins, so Four Books are pulled out before their tradition is
// consulted, Five Classics before their form, etc.
export function sectionIdForBook(b: Book): string {
  // Explicit slug pulls come first — these are books whose natural section
  // disagrees with their facet-derived one, so we resolve them deliberately.
  if (b.slug === "chengyu-catalog") return "reference";
  if (CONFUCIAN_MASTERS.has(b.slug)) return "confucian-masters";
  if (FOUR_BOOKS.has(b.slug)) return "four-books";
  if (b.tradition === "daoist") return "daoist";
  if (FIVE_CLASSICS.has(b.slug)) return "five-classics";
  if (b.form === "poetry") return "poetry";
  if (b.form === "prose-fiction") return "novels";
  if (b.form === "strategy-treatise" || b.slug === "han-feizi") return "statecraft";
  if (b.tradition === "buddhist") return "buddhist";
  if (b.form === "primer" || b.form === "idiom") return "primers";
  return "other";
}

export type CurriculumGroup = CurriculumSection & { books: Book[] };

// Group + order the books into curriculum sections. Sections with no books
// are dropped; an "Other" section is appended if any book matched no rule
// (defensive — shouldn't happen with the current catalog).
export function groupByCurriculum(books: Book[]): CurriculumGroup[] {
  const byId = new Map<string, Book[]>();
  for (const b of books) {
    const id = sectionIdForBook(b);
    if (!byId.has(id)) byId.set(id, []);
    byId.get(id)!.push(b);
  }
  const out: CurriculumGroup[] = [];
  for (const s of CURRICULUM_SECTIONS) {
    const items = byId.get(s.id);
    if (!items || items.length === 0) continue;
    // Within a section: curriculum_order (the hand-set reading sequence),
    // nulls last; tiebreak on tier then slug so placeholders land after real
    // books of the same section.
    items.sort((a, b) => {
      const ai = a.curriculum_order ?? Number.MAX_SAFE_INTEGER;
      const bi = b.curriculum_order ?? Number.MAX_SAFE_INTEGER;
      if (ai !== bi) return ai - bi;
      const ta = a.tier ?? "Z", tb = b.tier ?? "Z";
      if (ta !== tb) return ta < tb ? -1 : 1;
      return a.slug < b.slug ? -1 : 1;
    });
    out.push({ ...s, books: items });
  }
  const other = byId.get("other");
  if (other && other.length > 0) {
    out.push({ id: "other", name_en: "Other", intro: "", books: other });
  }
  return out;
}

// --- Facet labels (used by card tags) ---------------------------------------

export type FacetName = "tradition" | "form" | "year" | "tier";

// Pretty-print a facet value for card tags. Empty/unknown values return ""
// so callers can `.filter(Boolean)` and skip rendering. `year` is a number
// (negative = BCE), not a closed vocabulary, so it is formatted rather than
// looked up — see formatYear. The year label carries the era with it, so the
// caller does not need to thread `era` through this switch — see cardTagLabels.
export function facetLabel(facet: FacetName, value: string | number | undefined): string {
  if (value === undefined || value === "") return "";
  switch (facet) {
    case "tradition": return TRADITION_LABEL[value as string] ?? (value as string);
    case "form":      return FORM_LABEL[value as string] ?? (value as string);
    case "year":      return formatYear(value as number);
    case "tier":      return `Tier ${value}`;
  }
}

// The four tag badges every card shows, in display order. Returns the
// non-empty labels in that order so the card can render them uniformly.
// The year badge carries the era (e.g. "618 CE · Tang") when derivable —
// threaded from the book's explicit `era` field if set, else from `year`.
export function cardTagLabels(b: Book): string[] {
  return [
    facetLabel("tradition", b.tradition),
    facetLabel("tier", b.tier),
    b.year || b.era ? formatYear(b.year, b.era) : "",
    facetLabel("form", b.form),
  ].filter(Boolean);
}
