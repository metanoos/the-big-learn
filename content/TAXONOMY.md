# Taxonomy

How books in the library are categorized. This is the single source of truth
for the facet vocabulary used in every `catalog.json`, surfaced in the API,
and rendered by the library UI's view toggle.

## Two axes, not one

A single `category` field can't describe the canon, because a book belongs to
a **tradition** *and* a **form** at the same time. Shi Jing is confucian
*tradition* and poetry *form* — forcing it into one bucket lies about the
other. So every book carries both facets, independently.

## Facets

Every `catalog.json` carries these fields at the top level:

### `tradition` — the philosophical/religious lineage
- `confucian` — 儒 (Four Books, Five Classics). Primers with a Confucian didactic program, like San Zi Jing, also count as `confucian`.
- `daoist` — 道 (Daodejing, Zhuangzi, Liezi)
- `buddhist` — 佛 (Heart / Diamond / Platform Sutras)
- `secular` — neither (Sunzi, Sanguo, Qian Zi Wen). Primers follow their own tradition: San Zi Jing is `confucian` (it opens with Mencian doctrine 人之初性本善, prescribes the Four Books, and teaches filial piety); Qian Zi Wen is `secular` (a Zhou Xingsi literacy copybook with no doctrinal program).

### `form` — what kind of text
The genre of the text, mapped to the Chinese bibliographic tradition
(经史子集 + 释). The earlier catch-all `classic` was a status word, not a
genre — it sat inconsistently next to genre words and lumped the Lunyu
together with the Zhou Yi. The current vocabulary separates them:
- `philosophy` — 子 / argumentative prose, including the philosophical 经
  across traditions (Mengzi, Han Feizi, Lunyu, Da Xue, Zhong Yong, Daodejing,
  Zhuangzi, Liezi, the Buddhist sutras — `tradition: buddhist` marks the
  lineage; a sutra is a philosophical text)
- `history` — 史 / narrative history (Shang Shu, Chun Qiu, Zuozhuan)
- `ritual` — specialist 经 on rites (Li Ji)
- `divination` — specialist 经 on mantic practice (Zhou Yi)
- `poetry` — 诗 (verse: Shi Jing, Chu Ci, Tang anthology)
- `prose-fiction` — 小说 (narrative: the Four Great Novels)
- `primer` — 蒙学 (beginner verse texts read cover-to-cover: San Zi Jing, Qian Zi Wen)
- `idiom` — a reference catalog of idioms (chengyu), not a read-cover-to-cover text
- `strategy-treatise` — 兵 (Sunzi and its kin)

### `year` — when it took shape
A single integer, **negative for BCE** (e.g. `-400` = 400 BCE, `649` =
649 CE). This is a scholarly-consensus approximation, not a precise
publication date — most of these texts took shape over centuries and were
redacted repeatedly, so the value is one representative composition or
compilation point. The library renders it via `formatYear` as `400 BCE` /
`649 CE`. Where a text is itself an anthology of much older material (e.g.
Tang 300, a Qing-era anthology of Tang poems), `year` is the date of the
*book as the reader meets it*, not its sources.

### `tier` — cultural footprint (S > A > B)
A claim about the **text itself**, independent of the platform.
- `S` — backbone of the language; quoted constantly for 2,000 years
- `A` — major, central to its tradition
- `B` — influential but specialized or narrower in reach

Tier ranks *importance*, not difficulty and not "fits our product." The
distinction matters: a Tier-S text can be hard to present well (Chun Qiu),
and a Tier-B text can be a great read. Tier drives within-group ordering.

### `difficulty` — reader-facing on-ramp
`foundational` · `intermediate` · `advanced`

### `curriculum_order` — hand-set pedagogy sequence
A positive integer placing the book in the recommended reading order, or
`null` if the book isn't in the curriculum. This is editorial, not derivable
from the other facets. Drives the default "Curriculum" view.

## Library layout

The library is a single curated curriculum, not a faceted browser. Books are
grouped into named, narrated sections in priority order:

1. **The Four Books 四书** — the Confucian core (Da Xue, Zhong Yong, Lunyu, Mengzi)
2. **Daoist Classics 道家** — Daodejing, Zhuangzi, Liezi
3. **The Five Classics 五经** — Shi Jing, Shang Shu, Li Ji, Zhou Yi, Chun Qiu, Zuozhuan
4. **Poetry & Literature 诗词文学** — Chu Ci, Tang 300, Sanguo Yanyi
5. **Statecraft & Strategy 兵政** — Sunzi Bingfa, Han Feizi
6. **Buddhist Sutras 佛经** — Heart Sutra, Diamond Sutra
7. **Primers 蒙学** — San Zi Jing, Qian Zi Wen

Sections are **not a catalog field** — they're derived in
`apps/web/src/lib/libraryViews.ts` from the existing facets + slug sets, so
the schema stays clean. Within a section, books sort by `curriculum_order`
then tier then slug.

Each card carries its four facet tags (tradition · tier · year · form)
visibly — that's what makes the curriculum comprehensible without a
view-toggle. An earlier design had a Tradition/Tier/Period/Form toggle; it
was removed because the catalog is small enough to read as one curated path,
and the toggle obscured the editorial sequence.

## Non-goals

- **No `wedge_fit` tag.** An earlier design tagged each book by how well it
  suited a "translation-triangulation loop." That loop was removed (see
  README product thesis); the tag no longer means anything.
- **No filter/hide, no view toggle.** The library is one curated curriculum.
  Facets surface as card tags, not as regrouping views; placeholders are
  dimmed, never hidden.
- **URLs stay flat.** `/books/<slug>` only. Facets never enter the URL — a
  book's tradition/form/tier can change without breaking any link.

## Placeholders

A catalog may exist without ingested content — a `available: false` stub that
reserves the book's place in the library so the tier set is visible and the
curriculum reads completely. Placeholders:

- appear **dimmed and non-clickable** in the library grid (no hover, no
  progress bar — there's nothing to read yet),
- keep their tier badge + cross-cutting facets, because *where the book will
  live* is the reason to show it,
- resolve `/books/<slug>` to a "coming soon" page if visited directly (the
  URL is stable for when content lands),
- default to `available: true` when the field is absent, so a missing flag
  never accidentally hides a real book.

`available` is a content-state flag, not a taxonomy facet — it doesn't appear
in the view toggle. See `content/SOURCES.md` for which texts are placeholders
today and the ingestion order.

## Non-goals

- **No `wedge_fit` tag.** An earlier design tagged each book by how well it
  suited a "translation-triangulation loop." That loop was removed (see
  README product thesis); the tag no longer means anything.
- **No filter/hide.** The library view toggle regroups and resorts; it never
  hides books. A reader always sees the whole catalog (placeholders included).
- **URLs stay flat.** `/books/<slug>` only. Facets never enter the URL — a
  book's tradition/form/tier can change without breaking any link.
