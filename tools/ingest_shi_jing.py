#!/usr/bin/env python3
"""Ingest the Classic of Poetry (诗经 / shi-jing) from Wikisource.

WHY THIS EXISTS
---------------
content/books/shi-jing/ shipped as a placeholder stub (available:false,
chapter_count:0). This script ingests the real text so the book is readable
in the web app, matching the schema already used by daodejing / lunyu /
chengyu-catalog.

SOURCES (both Wikisource — bulk-API-permitted; ctext.org is NOT used because
its ToS forbid automated download and will IP-ban)
  - Chinese verse: zh.wikisource.org/wiki/诗经  (complete, all 305 + 6 笙诗)
  - Legge English: en.wikisource.org, "Sacred Books of the East/Volume 3/
    The Shih" — James Legge, 1879. PARTIAL coverage (~100-150/305: this is
    the "Religious Portions" abridgment, not his complete 1871 She King).
    Odes without a transcribed Legge page ship with NO translation — honest
    gap, NOT fabricated. Same discipline as chengyu-catalog.

    The complete 1871 She King (all 305 odes, Mao order) is NOT used because
    it is only available from ctext (ToS-forbidden) or Internet Archive OCR
    (mediocre quality). The SBE abridgment is the cleanest license-clean +
    ToS-permitted + proofread source.

LEGGE EXTRACTION (rendered HTML, not wikitext)
  Each en-ws ode page is a <pages .../> transclusion stub from the SBE djvu —
  its WIKITEXT is bare (the old extractor returned None and shipped the ode
  untranslated). We fetch the RENDERED HTML (action=parse&prop=text), where
  the server has resolved the transclusion, and pull the verse out of the
  first <div class="wst-block-center"> (the rendered form of
  {{center block/s}}). Footnotes (sup.reference / ol.references) are dropped.

LEGGE ↔ ZH-WS ALIGNMENT (by title, not position)
  The SBE abridgment REORDERS the books (颂 first) and EXCERPTS stanzas
  ("Ode 5, Stanzas 1 and 2"), so positional (book/decade/ode) mapping to
  Mao order is WRONG. Instead each Legge page's {{header|notes=}} carries
  the ode's traditional characters as {{lang|zh-Hant|…}}; we convert to
  simplified and match against the zh-ws unit's title. An ode with no
  confident title match ships untranslated rather than misaligned — a wrong
  pairing is worse than no translation.

CHAPTER GROUPING
  One chapter per canonical subgroup: 周南, 召南, 邶风, ... 鹿鸣之什, ...
  清庙之什, 鲁颂, 商颂. This is the Mao-tradition navigation (and zh-ws's
  own TOC grouping). → ~30 chapters.

READING UNIT
  One per ode. The whole-poem Chinese text is the unit; Legge's whole-ode
  English (where available) is its canonical translation. Mirrors how
  daodejing stores one chapter = one unit with one Legge translation.

PINYIN + WORD GLOSSES
  This script writes minimal units (text + canonical_translations). Run
  tools/build_pinyin.py and tools/build_word_gloss.py afterwards to enrich
  every unit with pinyin_per_char and word_spans — they auto-discover all
  books, so shi-jing is picked up automatically.

IDIOMATIC, IDEMPOTENT, NETWORK-GENTLE
  - Caches every fetched page to tools/raw/shi-jing/<slug>.txt so re-runs
    don't re-fetch.
  - Sleeps between requests (Wikisource asks bots to be gentle).
  - Re-running overwrites content/books/shi-jing/ deterministically.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DST = REPO / "content" / "books" / "shi-jing"
CACHE = REPO / "tools" / "raw" / "shi-jing"

UA = (
    "the-big-learn-ingestion/1.0 "
    "(educational classical-text reader; one-time ingest; "
    "https://www.wikisource.org/)"
)
SLEEP = 1.0  # seconds between live requests — be a polite API client

ZH_ROOT = "诗经"  # the TOC page on zh-ws


# --- network ---------------------------------------------------------------

def _live_get(domain: str, path_or_query: str) -> str:
    """GET a URL, return body text. Retries on 429 with exponential backoff."""
    url = f"https://{domain}{path_or_query}"
    last_err = None
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and attempt < 4:
                wait = SLEEP * (2 ** attempt) * 4  # 4s, 8s, 16s, 32s
                print(f"      429 rate-limited; backing off {wait:.0f}s (attempt {attempt + 1}/5)", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise last_err  # type: ignore[misc]


def fetch_wikitext(domain: str, page: str, cache_key: str) -> str:
    """Fetch a page's wikitext via the MediaWiki API, with on-disk cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / f"{cache_key}.wt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    q = urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "wikitext", "format": "json"}
    )
    body = _live_get(domain, f"/w/api.php?{q}")
    time.sleep(SLEEP)
    try:
        wt = json.loads(body)["parse"]["wikitext"]["*"]
    except (KeyError, json.JSONDecodeError):
        # Page missing or API error — cache the empty result so we don't
        # retry forever, but surface it.
        wt = ""
    cache_file.write_text(wt, encoding="utf-8")
    return wt


# --- wikitext cleanup ------------------------------------------------------

# Language converter: -{zh-hans:简; zh-hant:繁}- → take the traditional form
_LANG_CONV = re.compile(r"-\{[^}]*\}-")


def _resolve_lang_conv(s: str) -> str:
    def pick(m: re.Match) -> str:
        inner = m.group()[2:-2]  # strip -{ }-
        # prefer zh-hant / zh-tw / hk, else first option's text after ":"
        for part in inner.split(";"):
            part = part.strip()
            if part.startswith(("zh-hant:", "zh-tw:", "zh-hk:", "zh-mo:")):
                return part.split(":", 1)[1]
        # no variant tag: return the whole thing (single-form converter)
        if ":" not in inner:
            return inner
        return inner.split(":", 1)[1] if ":" in inner else inner

    prev = None
    cur = s
    while prev != cur:  # nested converters
        prev = cur
        cur = _LANG_CONV.sub(pick, cur)
    return cur


def _strip_wikitext_templ(s: str) -> str:
    """Resolve simple templates we encounter in verse lines.

    {{另|逑|仇}}  → 逑   (the canonical/first reading)
    {{·}} etc.    → pass through
    """
    # {{另|A|B}} → A  (zh-ws "variant reading" template: first arg is canonical)
    s = re.sub(r"\{\{另\|([^|}]+)\|[^}]*\}\}", r"\1", s)
    # generic: collapse any remaining {{...}} with no pipe to empty
    s = re.sub(r"\{\{[^|}]*\}\}", "", s)
    return s


def clean_verse_line(raw: str) -> str:
    """Turn one raw wikitext verse line into clean traditional Chinese."""
    s = raw.strip()
    # A leading ':' is wikitext indent markup, not content. Strip it here so
    # bare ":" stanza separators normalize to "" (caught as blank upstream)
    # and verse lines lose their indent prefix uniformly.
    s = s.lstrip(":").strip()
    s = _resolve_lang_conv(s)
    s = _strip_wikitext_templ(s)
    s = s.replace("&nbsp;", " ")
    return s.strip()


# --- TOC parsing -----------------------------------------------------------

def parse_toc(wikitext: str) -> list[tuple[str, str, list[str]]]:
    """Parse the 诗经 root page into an ordered list of (section, subgroup, [odes]).

    Top-level ==SECTION== markers delimit 国风 / 小雅 / 大雅 / 周颂 / 鲁颂 / 商颂.
    Inside, '''SUBGROUP''' bold headers (周南, 鹿鸣之什, ...) each introduce a
    list of # [[/odename|...]] links. For 颂 (no 什 grouping) the subgroup name
    falls back to the section name.
    """
    parts = re.split(r"\n(==[^=]+==)\n", "\n" + wikitext + "\n")
    chapters: list[tuple[str, str, list[str]]] = []
    i = 1
    while i < len(parts):
        section = parts[i].strip("= \n")
        body = parts[i + 1] if i + 1 < len(parts) else ""
        bold_chunks = re.split(r"'''([^']+)'''", body)
        if len(bold_chunks) == 1:
            # No bold subgroup headers — group the whole section as one chapter.
            odes = re.findall(r"\[\[/([^|\]]+)\|", body)
            if odes:
                chapters.append((section, section, odes))
        else:
            for j in range(1, len(bold_chunks), 2):
                subgroup = bold_chunks[j].strip()
                after = bold_chunks[j + 1] if j + 1 < len(bold_chunks) else ""
                odes = re.findall(r"\[\[/([^|\]]+)\|", after)
                if odes:
                    chapters.append((section, subgroup, odes))
        i += 2
    return chapters


# --- per-ode verse ---------------------------------------------------------

# zh-ws ode pages are NOT uniform. Three shapes seen in the wild:
#   1. <onlyinclude><poem>…</poem></onlyinclude>     (e.g. 周南 pages)
#   2. == section == \n === ODENAME === \n :verse    (e.g. 邶风, 周颂)
#   3. inline verse paragraphs, no indent            (e.g. 邶-柏舟)
# Plus: header may be simplified (鹿鸣 vs 鹿鸣), and duplicate ode names
# (柏舟 in both 邶 and 鄘) put TWO poems on one page. The extractor below
# handles all of these; it returns a LIST (one string per poem on the page),
# so dup-name pages yield two units.

_OPENCC_FALLBACK = str.maketrans({"鸣": "鸣"})


def _to_simplified(s: str) -> str:
    """Trad→simp for header comparison only (opencc if available)."""
    try:
        from opencc import OpenCC

        return OpenCC("t2s").convert(s)
    except ImportError:
        return s.translate(_OPENCC_FALLBACK)


# Headings whose body is NOT verse. Stored in SIMPLIFIED form because the
# extractor compares against _to_simplified(header) — covers both trad & simp
# page variants with one canonical key each.
_NON_VERSE_HEADINGS = {
    "毛诗序",  # 毛诗序
    "注解",  # 注解 / 注释
    "注释",
    "解释",  # 解释
    "鲁诗说",  # 鲁诗说
    "齐诗说",  # 齐诗说
    "韩诗说",  # 韩诗说
    "鲁齐韩三家说",  # 鲁齐韩三家说 — combined scholium header
    "三家诗说",  # 三家诗说
    "韩诗叙",  # 韩诗叙 — Han-school gloss
    "故实",  # 故实 — historical-anecdote commentary section
    "安大简本",  # 安大简本 — manuscript-variant text (archaic alt readings)
    "上博简",  # 上博简
    "清华简",  # 清华简
    "竹书",  # 竹书
}

# The 6 笙诗 ( Mouth-organ pieces) are titled but textless. zh-ws marks them
# with "有其义而亡其辞" ("has its meaning but lacks its words") or similar.
_SHENGYI_MARKERS = ("有其义而亡其辞", "有其义而亡其词", "辞亡", "亡其辞")


def _is_commentary(line: str) -> bool:
    """Reject Mao-preface / colophon / 笙诗-marker lines.

    NOTE: we deliberately do NOT treat 「」-quoted text as commentary — verse
    legitimately embeds quoted dialogue (e.g. 陟岵: 父曰：「嗟予子！...」).
    The reliable prose signal is a leading 《 (毛诗序 / colophon), which no
    verse line begins with.
    """
    if line.startswith("毛诗序"):
        return True
    if (
        line.startswith("《")
        and line.count("》") >= 1
        and ("句" in line or "章" in line)
    ):
        return True  # 《X》，N章M句 colophon
    if any(m in line for m in _SHENGYI_MARKERS):
        return True  # 笙诗 textless marker
    return False


def extract_verses(
    wikitext: str, ode_name_trad: str, subgroup: str | None = None
) -> list[str]:
    """Return a list of cleaned verse strings (one per poem on the page).

    Empty list when the page has no verse (the 6 笙诗 — titled but textless).

    Robust to the four zh-ws page shapes seen in the wild:
      - <onlyinclude><poem>…</poem></onlyinclude>   (sometimes unclosed)
      - == path == \n === ODE === \n :verse         (===header=== is the ode)
      - === 诗文 === \n :verse                       (header is literally 'poem')
      - inline verse, no indent                       (e.g. 邶-柏舟)
    And to: simplified headers (鹿鸣 vs 鹿鸣), duplicate ode names (柏舟 in
    邶 & 鄘 → two poems on one page), and prose scholia (毛诗序) interleaved.

    Strategy: normalize <poem> bodies to `:`-indented lines (so all shapes
    share one path), then collect maximal runs of verse lines. A verse line
    is an indented (`:`) line OR any line with Chinese verse punctuation,
    EXCLUDING prose (any line starting with 《 is scholium). Blank lines and
    bare `:` stanza separators never break a poem — only prose/headers do.

    For dup-name pages, when >1 poem is found and `subgroup` is given, only
    the poem whose most-recent header path contains the subgroup is kept.
    """
    # Normalize <poem>…</poem> bodies to `:`-indented lines.
    text = re.sub(
        r"<poem>(.*?)</poem>",
        lambda m: "\n"
        + "\n".join(":" + ln.lstrip(":") for ln in m.group(1).splitlines())
        + "\n",
        wikitext,
        flags=re.S,
    )
    # Strip multi-line {{...}} template blocks (header/notes/templates) that
    # span lines — single-line {{x}} is stripped per-line below, but {{header
    # | notes = ... }} carries prose across newlines and would leak otherwise.
    text = re.sub(r"\{\{[^{}]*\}\}", "", text, flags=re.S)
    # Wikitable dividers / markup that can hug verse lines:
    text = re.sub(r"\{\|[^|]*\|\}", "", text, flags=re.S)

    poems: list[tuple[str, list[str]]] = []
    cur_path = ""
    cur_lines: list[str] = []
    # Inside a commentary section (注解/毛诗序/安大简本/etc), suppress verse
    # collection — those sections hold scholia whose bullet lines contain 。 and
    # would otherwise be misread as verse. Cleared by the next verse section.
    in_commentary_section = False

    def flush() -> None:
        if cur_lines:
            # Append a COPY — clear() below empties the live list, so a bare
            # reference would leave poems holding an empty list.
            poems.append((cur_path, list(cur_lines)))
            cur_lines.clear()

    for raw in text.splitlines():
        s = raw.rstrip()
        stripped = s.strip()

        # Header (== or ===) → flush + maybe update path context.
        mh = re.match(r"^(={2,3})\s*([^=\n]+?)\s*\1$", stripped)
        if mh:
            h_raw = mh.group(2).strip()
            h = _to_simplified(h_raw)
            flush()
            level = len(mh.group(1))  # 2 for ==, 3 for ===
            if any(nv in h for nv in _NON_VERSE_HEADINGS):
                in_commentary_section = True  # suppress verse until next header
            else:
                in_commentary_section = False
                if "‧" in h_raw:
                    cur_path = h_raw  # full path (== 国风‧邶‧柏舟 ==)
                # else: bare ===ODE=== / ===诗文=== doesn't overwrite path
                # (it would erase the disambiguation context).
            continue

        # Skip everything inside a commentary section (注解 bullets etc.).
        if in_commentary_section:
            continue

        # Strip templates, refs, leftover tags.
        line = re.sub(r"\{\{[^}]*\}\}", "", stripped)
        line = re.sub(r"<ref[^>]*>.*?</ref>", "", line, flags=re.S)
        line = re.sub(r"<ref[^>]*/>", "", line)
        line = re.sub(r"<[^>]+>", "", line)
        line = clean_verse_line(line)
        if not line:
            continue  # blank / stanza-separator — keep cur_lines intact

        # Prose scholium: any line starting with 《 (毛诗序, colophon, etc.).
        # Verse never starts with 《. This is the cleanest verse/prose cut.
        if line.startswith("《"):
            flush()
            continue
        # Image/file transclusions and their captions — not verse.
        if stripped.startswith("[[File:") or stripped.startswith("[[Image:"):
            continue
        if _is_commentary(line):
            flush()
            continue

        was_indented = s.lstrip().startswith(":")
        # Verse punctuation: Chinese ，。；、 OR full-width space U+3000 (鸤鸠
        # uses 　as the tetrasyllabic separator instead of punctuation).
        if (was_indented or re.search(r"[，。；、　]", line)) and re.search(
            r"[一-鿿]", line
        ):
            cur_lines.append(line.lstrip(":").strip())
        else:
            # Non-indented, non-verse → prose boundary. Flush only if we've
            # been collecting verse; otherwise ignore (preamble/HTML cruft).
            if cur_lines:
                flush()
    flush()

    # Dup-name disambiguation FIRST — it's the strongest signal, so apply it
    # before dedupe/short-drop can accidentally remove the matching poem. A
    # page is a "dup-name page" when poems carry >1 distinct non-empty path
    # header (柏舟→邶&鄘; 扬之水→王&郑&唐; 白华→鹿鸣之什[笙诗]&鱼藻之什[real]).
    # Narrow to poems whose path contains this section's discriminator.
    distinct_paths = {p for (p, _) in poems if p}
    if subgroup and len(distinct_paths) > 1:
        # Discriminator strategy:
        #   风 subgroup (邶风)  → first char (邶): path is 国风‧邶‧柏舟
        #   什 subgroup (谷风之什) → 「之什」is unique per 雅 section, so use
        #     the FULL subgroup name; the path is 小雅‧谷风之什‧谷风.
        if subgroup.endswith("之什"):
            disc = subgroup  # 谷风之什 — distinguishes 小雅 sections cleanly
        else:
            disc = subgroup[0]  # 邶风 → 邶
        picked = [
            (p, ls)
            for (p, ls) in poems
            if disc in p or disc in _to_simplified(p)
        ]
        if picked:
            poems = picked

    # Dedupe near-identical poems: 三家诗 pages repeat the same verse under
    # multiple ===诗文=== sections (鲁/齐/韩 each). If two poems' texts are
    # equal (or one is a prefix of another), keep only the longest.
    seen: list[str] = []
    deduped: list[tuple[str, list[str]]] = []
    for p, ls in poems:
        text = " ".join(ls)
        if any(text == s or s.startswith(text) or text.startswith(s) for s in seen):
            continue
        seen.append(text)
        deduped.append((p, ls))
    poems = deduped

    # Drop short false-positive "poems": a real ode has ≥3 lines (even the
    # shortest single-stanza odes are 3+ lines). Scholia glosses that slip
    # through (e.g. "汉广，说人也。") are 1-2 lines. When MORE than one poem
    # survives on a page, drop any with fewer than 3 lines as scholium noise.
    if len(poems) > 1:
        poems = [(p, ls) for (p, ls) in poems if len(ls) >= 3]

    return [" ".join(ls) for (_, ls) in poems if ls]


# --- Legge English (rendered-HTML extraction) -----------------------------

# Legge's Shi Jing translation exists in two editions:
#   - Chinese Classics Vol. IV (1871): COMPLETE (all 305 odes, Mao order).
#     Not on en-ws as proofread text; only IA OCR (rough) / ctext (ToS-
#     forbidden). Not used.
#   - Sacred Books of the East Vol. III (1879): ABRIDGMENT ("Religious
#     Portions of the Shih King" — excerpted stanzas, reordered books,
#     ~100-150 verse units). Fully proofread on en-ws. Used here.
# The abridgment's reordering (颂 first) and stanza-excerpts mean a
# positional (book/decade/ode) alignment to Mao order is WRONG. We align
# instead by CHINESE TITLE: every Legge ode page's {{header|notes=}} carries
# the ode's traditional characters as {{lang|zh-Hant|…}}, which we convert
# to simplified and match against the zh-ws unit's title_zh. A wrong pairing
# is worse than no translation, so an ode with no confident title match ships
# untranslated (honest gap) rather than misaligned.

SBE = "Sacred Books of the East/Volume 3/The Shih"


def list_legge_ode_pages() -> list[str]:
    """Enumerate every transcribed Legge ode subpage on en-ws.

    Returns the full page titles (e.g. '.../Book 2/Ode 4', '.../Ode 1' for
    the 颂 sub-branches that number odes directly without a Book/Decade
    segment). Follows allpages pagination.
    """
    pages: list[str] = []
    apcontinue: str | None = None
    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apprefix": SBE + "/",
            "apnamespace": "0",
            "aplimit": "500",
            "format": "json",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue
        q = urllib.parse.urlencode(params)
        body = _live_get("en.wikisource.org", f"/w/api.php?{q}")
        time.sleep(SLEEP)
        d = json.loads(body)
        for p in d.get("query", {}).get("allpages", []):
            title = p["title"]
            # Ode leaf pages end in "/Ode <N>"; branch/decade index pages
            # (and the 颂 sub-branch redirects "Kau"→"Kâu") are skipped.
            if re.search(r"/Ode \d+(,|$)", title):
                pages.append(title)
        if "continue" in d:
            apcontinue = d["continue"].get("apcontinue")
        else:
            break
    return pages


# --- Legge English: rendered-HTML verse extraction -------------------------

# Each ode subpage is a <pages .../> transclusion from the SBE djvu — its
# WIKITEXT is a bare stub, but the server-resolved RENDERED HTML (prop=text)
# contains the full ode: prose argument + the verse in a centered block.
# We fetch the rendered HTML and pull the verse out of the first
# <div class="wst-block-center"> (where en-ws renders {{center block/s}}).
# This recovers verse that the old wikitext-only extractor returned None for.


def fetch_legge_html(page: str, cache_key: str) -> str:
    """Fetch the RENDERED HTML of a Legge ode page via action=parse.

    Cached to tools/raw/shi-jing/html_<key>.html. The rendered text resolves
    the djvu <pages/> transclusion server-side, so unlike the wikitext stub
    it carries the actual verse.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / f"html_{cache_key}.html"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    q = urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "text", "format": "json"}
    )
    body = _live_get("en.wikisource.org", f"/w/api.php?{q}")
    time.sleep(SLEEP)
    try:
        html = json.loads(body)["parse"]["text"]["*"]
    except (KeyError, json.JSONDecodeError):
        html = ""  # page missing or API error — cache empty, surface upstream
    cache_file.write_text(html, encoding="utf-8")
    return html


def _ode_cache_key(page: str) -> str:
    """Stable cache key from a Legge page title (branch+group+ode slug)."""
    # '.../Lessons from the States/Book 2/Ode 4' → 'Lessons_from_the_States_Book_2_Ode_4'
    tail = page.split(f"{SBE}/", 1)[-1] if SBE + "/" in page else page
    return urllib.parse.quote(tail.replace("/", "_"), safe="")


def extract_legge_verse(html: str) -> str | None:
    """Pull Legge's verse (the canonical translation) out of rendered HTML.

    Returns the verse with stanzas separated by blank lines and verse lines
    within a stanza separated by single newlines, or None when the page
    carries no transcribed verse block (genuinely untranslated — honest gap).

    Wikisource renders the verse inside <div class="wst-block-center"> with
    one <p> per stanza and <br/> between verse lines. We drop footnote
    markers, the trailing footnote list, page-number spans (typesetting
    metadata that splits words like "King Wăn" across page joins), and
    TemplateStyles <link> cruft — none are verse.
    """
    if not html:
        return None
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover - bs4 is a documented dep
        raise RuntimeError("beautifulsoup4 is required: pip install beautifulsoup4")
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one("div.wst-block-center")
    if block is None:
        return None
    # Drop non-verse cruft: footnotes (markers + list), page-number spans
    # (carry the printed page number, not verse — they fragment words where
    # a djvu page boundary falls mid-line), deduplicated-style links, and
    # Wikisource's reconstruct-bracket spans (⟨⟩ — ws-noexport display marks
    # around alternate readings Legge added from his later edition; the
    # reading text itself is in regular spans and is kept).
    # Decompose pagenum spans together with any wrapper span that would be
    # left empty (Wikisource wraps them as <span><span class="pagenum">…),
    # so the whitespace flanking the wrapper doesn't survive as a stray
    # line break mid-word. Do this BEFORE the other drops so the parent
    # is still navigable.
    for pn in list(block.select("span.pagenum")):
        parent = pn.parent
        pn.decompose()
        # If the wrapper span is now childless, drop it too — leaving it
        # would keep its surrounding whitespace as a text-node boundary.
        if parent and parent.name == "span" and not parent.find(True):
            parent.decompose()
    for sel in (
        "sup.reference",
        "ol.references",
        "span.__reconstruct_bracket",
        "link",
    ):
        for node in block.select(sel):
            node.decompose()
    # <br/> → newline (verse line break within a stanza).
    for br in block.find_all("br"):
        br.replace_with("\n")
    # One <p> per stanza. get_text with no separator avoids inserting
    # newlines at every inline tag boundary (which would shatter phrases
    # like "King <span>Wăn</span> is on high" into three lines). The HTML
    # source around each <br/> carries indentation/newlines, so a single
    # verse-line break surfaces as \n\n — collapse to \n within a stanza.
    stanzas = []
    for p in block.find_all("p"):
        s = p.get_text()
        s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)  # trim spaces around newlines
        s = re.sub(r"\n{2,}", "\n", s)  # one <br/> = one line, not a stanza gap
        # A decomposed pagenum span leaves its flanking source whitespace as
        # a \n mid-line ("And the\n appointment" where the page number was).
        # Legge's verse lines end in punctuation; a \n whose left side does
        # NOT end in verse punctuation (.,;:!?) and whose right side starts
        # lowercase is a mid-word split from a page boundary — rejoin it.
        s = re.sub(r"(?<![,.;:!?])\n([a-z])", r" \1", s)
        s = re.sub(r"[ \t]+", " ", s).strip()
        if s:
            stanzas.append(s)
    text = "\n\n".join(stanzas)
    # Strip zero-width spaces Wikisource inserts at page joins, and tidy
    # any spaces that landed adjacent to a newline.
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() or None


def build_legge_title_map(ode_pages: list[str]) -> dict[str, str]:
    """Map each zh-ws ode title (traditional) → Legge ode page title.

    For each Legge ode page, fetch its wikitext, extract the
    {{lang|zh-Hant|…}} chars from the {{header|notes=}} field, and key on
    them AS-IS (traditional). zh-ws serves 诗经 in traditional, so the unit
    title_zh at ingest time is traditional and matches directly — no
    trad→simp conversion here (the repo's to_simplified.py runs later as a
    separate pass over all fields; it would leave this matching logic
    broken if we keyed on simplified pre-conversion).

    A title mapping to multiple Legge pages (e.g. 柏舟 in both 邶 and 鄘) maps
    to the FIRST — the per-chapter loop walks zh-ws in Mao order and
    extract_verses(subgroup=...) already picks the right poem per section.
    """
    out: dict[str, str] = {}
    for page in ode_pages:
        wt = fetch_wikitext("en.wikisource.org", page, f"legge_{_ode_cache_key(page)}")
        if not wt:
            continue
        # The ode-title zh-Hant lives in notes=, but cross-refs to other
        # odes can appear too. Take every candidate; main() matches against
        # the unit's own title_zh, so only the right key lands.
        for zh_hant in re.findall(r"\{\{lang\|zh-Hant\|([^}]+)\}\}", wt):
            key = zh_hant.strip()
            if key and key not in out:
                out[key] = page
    return out


# --- unit + chapter construction -------------------------------------------

LEGGE = {
    "translator": "Legge",
    "year": 1879,
    "license": "public domain",
    "source_url": "https://en.wikisource.org/wiki/Sacred_Books_of_the_East/Volume_3",
}


def slugify(name: str) -> str:
    """ASCII-safe cache filename for a Chinese ode title."""
    return urllib.parse.quote(name, safe="") or "ode"


def build_unit(
    ode_name: str,
    order: int,
    chapter_id: str,
    verse: str,
    legge_text: str | None,
    global_num: int,
) -> dict:
    canonical = []
    if legge_text:
        canonical.append({**LEGGE, "text": legge_text})
    return {
        "id": f"{chapter_id}-line-{order:03d}",
        "order": order,
        "mao_number": global_num,
        "title_zh": ode_name,
        "character_count": len(verse),
        "text": verse,
        "canonical_translations": canonical,
    }


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


# --- driver ----------------------------------------------------------------

def main() -> int:
    print("== Classic of Poetry (诗经) ingestion ==")
    if not CACHE.exists():
        CACHE.mkdir(parents=True, exist_ok=True)

    # 1. TOC
    print("[1/5] Fetching zh-ws 诗经 TOC ...")
    toc_wt = fetch_wikitext("zh.wikisource.org", ZH_ROOT, "_TOC")
    chapters_meta = parse_toc(toc_wt)
    ode_total = sum(len(o) for _, _, o in chapters_meta)
    print(f"      {len(chapters_meta)} chapters, {ode_total} ode links")

    # 2. Legge index (best-effort; non-fatal if it fails)
    print("[2/5] Indexing en-ws Legge ode pages (best-effort) ...")
    try:
        legge_pages = list_legge_ode_pages()
        print(f"      {len(legge_pages)} Legge ode pages transcribed on en-ws")
    except Exception as e:
        print(f"      WARN: could not list Legge pages ({e}); shipping without EN")
        legge_pages = []

    # Build the title crosswalk: zh-ws ode title (simplified) → Legge page.
    # Title-based alignment (not positional) because the SBE Vol III text is
    # an abridgment that reorders books and excerpts stanzas — see module
    # docstring above. Each Legge page's {{header|notes=}} carries the ode's
    # traditional characters, which we convert to simplified to match.
    title_to_legge: dict[str, str] = {}
    if legge_pages:
        title_to_legge = build_legge_title_map(legge_pages)
        print(
            f"      {len(title_to_legge)} ode titles resolved via zh-Hant crosswalk"
        )

    # 3. Per-chapter: fetch every ode's verse + try Legge
    if DST.exists():
        import shutil

        shutil.rmtree(DST)
    (DST / "chapters").mkdir(parents=True)

    catalog_chapters = []
    global_num = 0
    units_with_verse = 0
    units_with_legge = 0
    skipped_sheng = 0

    for ch_idx, (section, subgroup, odes) in enumerate(chapters_meta, start=1):
        chapter_id = f"chapter-{ch_idx:03d}"
        reading_units = []
        chapter_chars = 0

        for ode_pos, ode_name in enumerate(odes, start=1):
            # Cache key is the page name (slugified) — dup ode names like 柏舟
            # resolve to ONE zh-ws page, so we fetch it once and let
            # extract_verses(subgroup=...) pick the right poem per section.
            wt = fetch_wikitext(
                "zh.wikisource.org",
                f"诗经/{ode_name}",
                slugify(ode_name),
            )
            verses = extract_verses(wt, ode_name, subgroup=subgroup)
            if not verses:
                skipped_sheng += 1  # 笙诗 — titled but textless
                continue

            # Legge attempt via title crosswalk. ode_name IS the zh-ws
            # simplified title, so it matches the key built in
            # build_legge_title_map directly. No positional book/decade
            # math — that was wrong for the reordered SBE abridgment.
            legge_text = None
            legge_page = title_to_legge.get(ode_name)
            if legge_page:
                try:
                    html = fetch_legge_html(legge_page, _ode_cache_key(legge_page))
                    legge_text = extract_legge_verse(html)
                except Exception:
                    legge_text = None

            # Most pages carry one poem; dup-name pages (柏舟) carry two but
            # extract_verses(subgroup=...) returns only this section's poem.
            for verse in verses:
                global_num += 1
                unit = build_unit(
                    ode_name,
                    len(reading_units) + 1,
                    chapter_id,
                    verse,
                    legge_text,
                    global_num,
                )
                reading_units.append(unit)
                chapter_chars += len(verse)
                units_with_verse += 1
                if legge_text:
                    units_with_legge += 1

        if not reading_units:
            continue  # chapter had only笙诗 — skip writing an empty file

        first_ode = odes[0] if odes else subgroup
        chapter_doc = {
            "chapter": {
                "id": chapter_id,
                "order": ch_idx,
                "title": f"{section}·{subgroup}" if section != subgroup else subgroup,
                "summary": first_ode,
                "text": " ".join(u["text"] for u in reading_units),
                "character_count": chapter_chars,
                "reading_unit_count": len(reading_units),
                "reading_units": reading_units,
                "supplemental_text": "",
                "supplemental_unit_count": 0,
                "supplemental_units": [],
            },
            "chapter_path": f"books/shi-jing/chapters/{chapter_id}.json",
            "provider": "wikisource",
            "schema_version": 2,
            "source_title": "诗经 (Chinese: zh.wikisource); Legge English: Sacred Books of the East, Vol. III (en.wikisource)",
            "source_url": "https://zh.wikisource.org/wiki/诗经",
        }
        (DST / "chapters" / f"{chapter_id}.json").write_text(
            dump(chapter_doc), encoding="utf-8"
        )
        catalog_chapters.append(
            {
                "chapter_path": f"books/shi-jing/chapters/{chapter_id}.json",
                "id": chapter_id,
                "order": ch_idx,
                "title": chapter_doc["chapter"]["title"],
                "summary": first_ode,
                "character_count": chapter_chars,
                "reading_unit_count": len(reading_units),
                "supplemental_unit_count": 0,
            }
        )
        print(
            f"      [{chapter_id}] {chapter_doc['chapter']['title']}: "
            f"{len(reading_units)} odes"
        )

    # 4. Catalog
    print("[4/5] Writing catalog.json ...")
    catalog = {
        "cache_dir": "books/shi-jing",
        "catalog_path": "books/shi-jing/catalog.json",
        "display_name": "Shi Jing 诗经",
        "name_zh": "诗经",
        "name_pinyin": "Shī Jīng",
        "name_en": "The Classic of Poetry",
        "v1": False,
        "available": True,
        "tradition": "confucian",
        "form": "poetry",
        "period": "pre-qin",
        "tier": "S",
        "difficulty": "intermediate",
        "curriculum_order": None,
        "title": "Classic of Poetry",
        "source_url": "https://zh.wikisource.org/wiki/诗经",
        "source_title": (
            "Chinese verse: zh.wikisource 诗经 (complete, all odes). "
            "English: James Legge, 'Sacred Books of the East' Vol. III (1879, "
            f"public domain) — partial coverage, {units_with_legge}/{units_with_verse} "
            "odes. Odes without a transcribed Legge page ship untranslated "
            "(honest gap, not fabricated)."
        ),
        "blurb": (
            "The oldest poetry anthology in the Chinese tradition; the source "
            "of much of the language's literary allusion. Confucius said "
            "reading it was essential."
        ),
        "provider": "wikisource",
        "seed_translator": {
            "translator": "Legge",
            "year": 1879,
            "license": "public domain",
        },
        "chapter_count": len(catalog_chapters),
        "chapters": catalog_chapters,
        "commentary_chapter_count": 0,
        "commentary_chapters": [],
    }
    (DST / "catalog.json").write_text(dump(catalog), encoding="utf-8")

    # 5. Report
    print("[5/5] Done.\n")
    print(f"  chapters written : {len(catalog_chapters)}")
    print(f"  odes with verse  : {units_with_verse}")
    print(f"  odes with Legge  : {units_with_legge} ({units_with_legge * 100 // max(units_with_verse, 1)}%)")
    print(f"  笙诗 (skipped)   : {skipped_sheng}")
    print(
        "\nNext: run tools/build_pinyin.py then tools/build_word_gloss.py "
        "(they auto-discover shi-jing).",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
