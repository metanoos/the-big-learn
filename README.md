# The Big Learn

A collaborative translation platform for classical Chinese texts. Readers read
canonical works line-by-line, see multiple English translations side-by-side
(canonical sources seeded), submit their own translations, vote, comment, and
get private LLM feedback on draft translations before publishing.

**Status:** under active development. Content layer complete; platform build
in progress. Not yet deployed.

## What's here

```
content/
  books/<book>/{catalog.json, chapters/*.json}   # canonical content (read-only in prod)
  references/characters/index.json               # per-char pinyin/zhuyin/senses (render-time)
  SOURCES.md                                     # full translation attribution + licenses
tools/
  clean_content.py    # Phase 1: migrate + clean da-xue content into ./content
  build_chengyu.py    # Phase 2: rebuild 1,000-idiom catalog w/ pinyin + CC-CEDICT
docs/                # product + design notes (planned)
apps/web/            # Next.js frontend (planned, Phase 4)
services/api/        # Go backend (planned, Phase 3)
```

## Content

**v1 canon** (curated, cleaned): Da Xue, Zhong Yong, Lunyu, Mengzi, Daodejing.
English seed translation: James Legge (public domain). See
[`content/SOURCES.md`](./content/SOURCES.md) for full attribution and the
reasoning behind translator choices.

**Chengyu catalog:** 1,000 four-character idioms in 20 themed chapters. 100%
pinyin coverage (CC-CEDICT + per-character index); 52.8% have CC-CEDICT
translations, the rest are honest gaps the platform's users fill. No machine
translations are seeded — the prior catalog's meaning-inverting errors came
from a Google-Translate fallback, and we don't repeat that.

**Deferred** (copied as-is, not v1): Sunzi Bingfa, San Zi Jing, Qian Zi Wen,
Sanguo Yanyi. Sanguo has a known translation-misalignment problem to repair
before promotion.

## Regenerating content

```bash
# Phase 1: re-clean classical books from ../da-xue/content
python3 tools/clean_content.py

# Phase 2: rebuild chengyu (downloads CC-CEDICT once, ~4MB, cached at /tmp)
python3 tools/build_chengyu.py
```

Both scripts are read-only on their sources and only write under `content/`.

## Product thesis

Not a phrasebook app. The wedge is the **translation-triangulation loop**:
canonical sources side-by-side + reader posits their own + LLM feedback +
community voting. Producing a translation forces engagement with every
character; comparing against Legge and peers surfaces interpretive choices
you'd otherwise miss; the LLM loop gives a private first read before public
exposure.

This supersedes the prior `agent-skill-the-big-learn/PRODUCT.md` "text-first,
no standalone app" thesis. See `docs/` (planned) for the current product
spec.
