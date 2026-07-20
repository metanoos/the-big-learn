# The Big Learn

A reading platform for classical Chinese texts. Readers read canonical works
line-by-line with multiple English translations side-by-side and a
per-character breakdown, save lines, and track progress. The library is
organized as a curated curriculum — the Four Books first, then Daoist classics,
the Five Classics, poetry, statecraft, sutras, and primers — each book tagged
by tradition, tier, year, and form.

**No accounts.** All reader state — reading progress, saved lines (bookmarks),
and the character review pile — lives in the browser's localStorage and never
leaves the device. The backend is a stateless, read-only layer over the
canonical `content/` JSON. There is no database, telemetry, or per-reader
identifier.

**Status:** under active development. Not yet deployed.

## What's here

```
content/
  books/<book>/{catalog.json, chapters/*.json}   # canonical content (read-only in prod)
  references/characters/index.json               # per-char pinyin/zhuyin/senses (render-time)
  SOURCES.md                                     # full translation attribution + licenses
  TAXONOMY.md                                    # two-facet categorization (tradition × form)
tools/
  clean_content.py    # Phase 1: migrate + clean da-xue content into ./content
  build_chengyu.py    # Phase 2: rebuild 1,000-idiom catalog w/ pinyin + CC-CEDICT
apps/web/            # Next.js frontend
services/api/        # Go backend
```

## Content

The library is organized by two orthogonal facets — **tradition**
(confucian / daoist / buddhist / secular) and **form** (philosophy / history
/ ritual / divination / poetry / prose-fiction / primer / idiom /
strategy-treatise) — plus cross-cutting tags (year, tier, difficulty) and a
hand-set curriculum order. The library presents that order as narrated
sections, while the facets remain visible on each card. See
[`content/TAXONOMY.md`](./content/TAXONOMY.md) for the full
vocabulary and the reasoning behind the two-facet model.

**v1 library:** Da Xue, Zhong Yong, Lunyu, Mengzi, Daodejing, Sanguo Yanyi,
Shi Jing (partial English coverage), and Bai Jia Xing (Chinese-only). The Five
Confucian/Daoist seed texts use James Legge's public-domain translations;
Sanguo uses Brewitt-Taylor prose plus clearly labeled GLM verse. See
[`content/SOURCES.md`](./content/SOURCES.md) for full attribution and the
reasoning behind translator choices.

**Chengyu catalog:** 1,000 four-character idioms in 20 themed chapters. 100%
pinyin coverage (CC-CEDICT + per-character index); 52.8% have CC-CEDICT
translations, the rest are honest gaps the platform's users fill. Where a
machine rendering is used for a line with no public-domain human translation,
it carries a model byline (e.g. "GLM · 2026 · machine-generated") so it never
passes silently as canon — the prior catalog's meaning-inverting errors came
from an unattributed Google-Translate fallback, and we don't repeat that.

**Readable but not yet promoted to v1:** Sunzi Bingfa, San Zi Jing, Qian Zi
Wen, and the Chengyu reference catalog. They remain visible while editorial
review and provenance work continues.

**Roadmap:** the Tier-S/A gaps the library doesn't carry yet — Zhou Yi,
Zhuangzi, Chu Ci, and Zuozhuan — are listed with status and rationale in
[`content/SOURCES.md`](./content/SOURCES.md).

## Regenerating content

```bash
# Phase 1: re-clean classical books from ../da-xue/content
python3 tools/clean_content.py

# Phase 2: rebuild chengyu (downloads CC-CEDICT once, ~4MB, cached at /tmp)
python3 tools/build_chengyu.py
```

Both scripts are read-only on their sources and only write under `content/`.

## Product thesis

The wedge is **side-by-side reading**: canonical Chinese texts presented with
multiple public-domain English translations and a per-character breakdown, so
a reader sees every interpretive choice. Not a phrasebook — the unit is the
line, read closely, with the heart beside each line acting as a private,
device-local save. Where a line has no human translation yet, a model-generated
rendering may be shown with a model byline rather than left blank — the goal
is honest framing, never a silent machine pass-off. The library is organized
as a curated curriculum — the Four Books first, then Daoist classics, the Five
Classics, poetry, statecraft, sutras, and primers — each book tagged by
tradition, tier, year, and form.

## Architecture

```
apps/web/        # Next.js frontend — all reader state in localStorage
services/api/    # Stateless Go API — read-only access to content/ JSON
content/         # Canonical texts and character references
```

Reader state (per-browser, never sent to the server):
- `tbl:read`           — `"book:chapter"` set (chapters opened)
- `tbl:bookmarks`      — `"book:chapter:line"` list (saved lines)
- `tbl:bookmark-details` — Chinese/translation previews for saved lines
- `tbl:review-chars`   — characters or multi-character words expanded in the popover

The Review page can export and restore these values as a private JSON backup,
so a reader can move progress between browsers without introducing accounts or
a server database.

The server keeps no persistent state. It reads the canonical JSON files and
caches parsed content in memory for the lifetime of the process.

## Running locally

No database or Docker service is required.

Prerequisites: Node.js 20.9 or newer, npm, Go 1.25 or newer, and Python 3.12+
for the content validators.

```bash
# Terminal 1 — content API
cd services/api && go run ./cmd/server

# Terminal 2 — web app
cd apps/web && npm run dev
```

Open <http://localhost:3100>.

## Verification

```bash
# Web unit/config checks + production build
cd apps/web && npm test && npm run build && npm run test:e2e

# API tests
cd services/api && go test ./...

# All catalog/chapter contracts + Sanguo translation safeguards
python3 tools/validate_content.py
python3 tools/validate_sanguo.py --show-outliers 0
```

The same checks run in GitHub Actions. See [`DEPLOYMENT.md`](./DEPLOYMENT.md)
for the provider-neutral production contract and launch checklist.
