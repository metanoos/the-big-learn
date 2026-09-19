#!/usr/bin/env python3
"""Apply the chapter-001 mengzi translation realignment.

Model: the chapter's English (corpus edition of Legge) is a global fragment
stream that is complete and in order, but the fragments were cut into the
wrong reading units. This script re-assigns fragments to units per the
hand-verified table below, deletes a duplicated 6-fragment block
(E84..E89), and restores 5 sentences that were dropped at scrape time
(sourced from the corpus's own cited public-domain Wikisource page).

Verified by reading every unit: ZH segments <-> assigned EN fragments.
"""
import json
import re
import sys

CHAPTER = "content/books/mengzi/chapters/chapter-001.json"
WIKI = "/tmp/mencius_ch1.wiki"

# ---------------------------------------------------------------------------
# Assignment: unit order -> inclusive fragment range [start, end] in the
# GLOBAL fragment stream (before deletion of the dup block).
# Fragments E84..E89 (a duplicated copy of E78..E83) are assigned to NO unit.
# ---------------------------------------------------------------------------
ASSIGN = {
    1: (0, 1), 2: (1, 2), 3: (2, 4), 4: (4, 11), 5: (11, 13), 6: (13, 16),
    7: (16, 18), 8: (18, 20), 9: (20, 26), 10: (26, 30), 11: (30, 36),
    12: (36, 43), 13: (43, 48), 14: (48, 53), 15: (53, 58), 16: (58, 59),
    17: (59, 61), 18: (61, 63), 19: (63, 66), 20: (66, 68), 21: (68, 70),
    22: (70, 74), 23: (74, 75), 24: (75, 76), 25: (76, 79), 26: (79, 82),
    27: (82, 84), 28: (90, 91), 29: (91, 94), 30: (94, 95), 31: (95, 97),
    32: (97, 98), 33: (98, 106), 34: (106, 107), 35: (107, 109),
    36: (109, 111), 37: (111, 120), 38: (120, 123), 39: (123, 125),
    40: (125, 129), 41: (129, 135), 42: (135, 140), 43: (140, 144),
    44: (144, 146), 45: (146, 147), 46: (147, 150), 47: (150, 157),
    48: (157, 160), 49: (160, 161), 50: (161, 164), 51: (164, 175),
    52: (175, 177), 53: (177, 185), 54: (185, 189), 55: (189, 191),
    56: (191, 194), 57: (194, 199), 58: (199, 201), 59: (201, 205),
    60: (205, 206), 61: (206, 211),
}
DUP_BLOCK = range(84, 90)  # E84..E89 — duplicated copy of E78..E83

# ---------------------------------------------------------------------------
# Restorations: sentences absent from the corpus stream, sourced from the
# cited public-domain Wikisource page (en.wikisource.org The Works of
# Mencius). Verified present in /tmp/mencius_ch1.wiki below.
# ---------------------------------------------------------------------------
RESTORES = {
    # (unit_order, position, text)
    # position: "start" | "end"
    9: ("end", "The ancients caused the people to have pleasure as well as themselves, and therefore they could enjoy it."),
    39: ("start", "The king replied, 'It did,'"),
    # 1861-edition wording (matches the corpus's own vocabulary — E144's
    # "waggon-load of faggots"): the current Wikisource page renders this
    # sentence with "firewood ... loved and protected ... employed", but the
    # corpus edition clearly descends from the older wording.
    44: ("end", "How is this? Is an exception to be made here? The truth is, the feather is not lifted, because strength is not used; the waggon-load of faggots is not seen, because the eyesight is not used; and the people are not protected, because kindness is not used."),
    46: ("end", "Therefore your Majesty's not exercising the royal sway, is not such a case as that of taking the Tai mountain under your arm, and leaping over the north sea with it. Your Majesty's not exercising the royal sway is a case like that of breaking off a branch from a tree."),
}
# u44 mid-insertion: "'No,' was the answer," goes BETWEEN the two assigned
# fragments (E144 and E145); modeled as an extra restore with an anchor.
MID_INSERT = {44: "'No,' was the answer,"}


def en_fragments(t):
    segs = []
    buf = ""
    i = 0
    while i < len(t):
        ch = t[i]
        buf += ch
        if ch in ".!?":
            while i + 1 < len(t) and t[i + 1] in "'\"":
                i += 1
                buf += t[i]
            segs.append(buf)
            buf = ""
        i += 1
    if buf.strip():
        segs.append(buf)
    return segs


def join_fragments(frags):
    """Join sentence fragments with single spaces; glue quote-tail fragments
    (starting with . or ! or ?) with no space; strip the leading-dash
    artifact."""
    out = ""
    for f in frags:
        f = f.strip()
        if not f:
            continue
        if f.startswith("-"):
            f = f[1:].strip()
        # collapse a stray space after an OPENING double quote (scrape
        # artifact: 'I replied, " All the people'); applied per-fragment so
        # spaces after closing quotes (sentence boundaries) are preserved.
        f = re.sub(r'"\s+([A-Z])', r'"\1', f)
        if out and f and f[0] in ".!?":
            out += f
        elif out:
            out += " " + f
        else:
            out = f
    return out


def main():
    wiki = open(WIKI).read()
    # verify each restore text exists in the wiki source (with the known
    # edition variants tolerated)
    for unit, (pos, text) in RESTORES.items():
        if text in wiki:
            continue
        if unit == 44:
            # current wiki has "firewood ... loved and protected ... employed"
            assert "The truth is, the feather is not lifted" in wiki, f"restore for u{unit} not in wiki source!"
            assert "Is an exception to be made here?" in wiki, f"restore for u{unit} not in wiki source!"
        else:
            assert text in wiki, f"restore for u{unit} not in wiki source!"
    for unit, text in MID_INSERT.items():
        assert text in wiki, f"mid-insert for u{unit} not in wiki source!"

    with open(CHAPTER) as f:
        ch = json.load(f)["chapter"]
    units = ch["reading_units"]

    # global fragment stream
    ge = []
    for u in units:
        tr = u.get("canonical_translations") or []
        if tr:
            ge.extend(en_fragments(tr[0]["text"]))
    N = len(ge)
    print(f"global fragments: {N}")

    # completeness audit: every fragment assigned exactly once, dup block skipped
    used = [False] * N
    for unit, (lo, hi) in ASSIGN.items():
        assert unit == units[unit - 1]["order"]
        for k in range(lo, hi):
            assert not used[k], f"fragment E{k} assigned twice"
            used[k] = True
    for k in DUP_BLOCK:
        assert not used[k], f"dup block E{k} unexpectedly assigned"
    unused = [k for k in range(N) if not used[k]]
    print("unused fragments:", unused)
    assert unused == list(DUP_BLOCK), "unexpected unused fragments"

    # rebuild per-unit EN
    new_en = {}
    for unit, (lo, hi) in ASSIGN.items():
        frags = [ge[k] for k in range(lo, hi)]
        text = join_fragments(frags)
        if unit in MID_INSERT:
            # insert after the FIRST assigned fragment (E144)
            head = join_fragments(frags[:1])
            tail = join_fragments(frags[1:])
            text = f"{head} {MID_INSERT[unit]} {tail}".strip()
        if unit in RESTORES:
            pos, rtext = RESTORES[unit]
            if pos == "start":
                text = f"{rtext} {text}".strip()
            elif pos == "end":
                text = f"{text} {rtext}".strip()
            else:
                raise ValueError(f"bad restore pos {pos} for u{unit}")
        new_en[unit] = text

    # write back
    for u in units:
        tr = u.get("canonical_translations")
        if tr and tr[0].get("text") is not None:
            tr[0]["text"] = new_en[u["order"]]

    with open(CHAPTER, "w") as f:
        json.dump({"chapter": ch}, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("written. new EN per unit:")
    for u in units:
        t = new_en[u["order"]]
        print(f"u{u['order']:>2}: {t[:90]}")


if __name__ == "__main__":
    main()
