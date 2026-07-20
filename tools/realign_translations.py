#!/usr/bin/env python3
"""
Conservatively repair forward-leaked translation content in lunyu + mengzi.

ROOT CAUSE (precise)
--------------------
In a minority of chapters, Legge's English translation is segmented slightly
behind the Chinese source: unit N's source is too long for its translation, so
the spillover text sits at the START of unit N+1's translation. Most units in
most chapters are correctly aligned; only specific regions drift.

This is the same class of error as the zhong-yong 26/27/29 fixes (a Legge
sentence landed on the wrong side of a unit boundary), just at slightly larger
scale in these two books.

STRATEGY (conservative)
-----------------------
1. DETECT drift regions: find pairs (i, i+1) where unit i's translation ends
   mid-thought (no terminal punctuation) AND unit i+1's translation opens with
   content that semantically belongs to unit i's source.
2. CONFIRM via anchor: derive the expected English opening of unit i+1 from its
   source (e.g. 司马牛问 -> "Si Ma Niu asked"). Find that anchor in unit i+1's
   translation. Everything BEFORE the anchor is leaked overflow from unit i.
3. REPAIR: move the overflow prefix from unit i+1 to the end of unit i.
   Iterate over each chapter until no more repairs are possible (capped to
   avoid runaway).
4. NEVER touch a unit unless an anchor-based split is found. Well-aligned
   chapters (the majority) are left completely unchanged.

Only `canonical_translations[0].text` is rewritten; all other structure is
preserved by parse + reserialize with the same formatting as the corpus.

USAGE
-----
  python3 tools/realign_translations.py lunyu           # dry-run, write review
  python3 tools/realign_translations.py mengzi
  python3 tools/realign_translations.py --apply lunyu   # write changes
"""
from __future__ import annotations
import argparse, json, glob, os, re
from typing import Optional

# ----------------------------------------------------------------------------
# Name maps: Chinese name -> list of possible Legge romanizations (opening tag).
# Used to find where unit N+1's OWN content begins inside its translation.
# ----------------------------------------------------------------------------
LUNYU_NAMES = {
    '颜渊': ['Yan Yuan'], '颜回': ['Yan Hui'],
    '仲弓': ['Zhong Gong'],
    '司马牛': ['Si Ma Niu'],
    '樊迟': ['Fan Chi'],
    '子贡': ['Zi Gong'],
    '子路': ['Zi Lu'],
    '子张': ['Zi Zhang'],
    '子夏': ['Zi Xia'],
    '子游': ['Zi You'],
    '曾子': ['The philosopher Zeng', 'Zeng'],
    '有子': ['The philosopher You', 'You'],
    '闵子骞': ['Min Ziqian', 'Min Zi Qian'],
    '冉求': ['Ran Qiu'], '冉有': ['Ran You'],
    '宰我': ['Zai Wo'],
    '原宪': ['Yuan Xian'],
    '林放': ['Lin Fang'],
    '季康子': ['Ji Kang Zi', 'Ji Kang'],
    '孟武伯': ['Meng Wu Bo'],
    '孟懿子': ['Meng Yi Zi', 'Meng Yi'],
    '卫灵公': ['The duke Ling of Wei', 'duke Ling of Wei', 'Duke Ling of Wei'],
    '阳货': ['Yang Huo'],
    '孔子': ['Confucius'],
    '子产': ['Zi Chan'],
    '管仲': ['Guan Zhong'],
    '叶公': ['The duke of She', 'duke of She', 'Duke of She'],
    '王孙贾': ['Wang Sun Jia'],
    '仪封人': ['The border-warden of Yi', 'border-warden of Yi'],
    '陈成子': ['Chen Cheng Zi'],
    '蘧伯玉': ['Qu Bo Yu'],
    '公叔文子': ['Gongshu Wen Zi', 'Gong Shu Wen Zi'],
    '公明贾': ['Gongming Jia', 'Gong Ming Jia'],
    '公山弗扰': ['Gongshan Furao', 'Gong Shan Furao'],
    '佛肸': ['Fo Xi'],
    '陈司败': ['The minister of crime in Chen', 'minister of crime in Chen'],
    '陈子禽': ['Chen Zi Qin'],
    '陈亢': ['Chen Kang'],
    '孔文子': ['Kong Wen Zi'],
    '令尹': ['The minister of instruction', 'minister of instruction', 'Ling Yin'],
    '子文': ['Zi Wen'],
    '臧武仲': ['Zang Wuzhong'],
    '孟公绰': ['Meng Gongchuo'],
    '公绰': ['Gongchuo'],
    '原壤': ['Yuan Rang'],
    '微生亩': ['Wei Sheng Mu'],
    '微生高': ['Wei Sheng Gao'],
    '泰伯': ['Tai Bo'],
    '伯夷': ['Bo Yi'], '叔齐': ['Shu Qi'],
    '柳下惠': ['Liu Xia Hui'],
    '周公': ['The duke of Zhou', 'duke of Zhou', 'Duke of Zhou'],
    '尧': ['Yao'], '舜': ['Shun'], '禹': ['Yu'], '汤': ['Tang'],
    '子桑伯子': ['Zi Sang Bo Zi', 'Zisang Bozi'],
    '棘子成': ['Ji Zi Cheng', 'Jizicheng'],
    '子羔': ['Zi Gao', 'Zigao'],
    '季子然': ['Ji Zi Ran', 'Jizi Ran'],
    '子张': ['Zi Zhang'],
    '澹台灭明': ['Tantai Mieming', 'Tan Tai Mie Ming'],
    '申枨': ['Shen Cheng', 'Shen Tang'],
    '孺悲': ['Ru Bei', 'Rubei'],
    '孺子': ['Ru Zi'],
    '互乡': ['the village of Hu Xiang', 'Hu Xiang'],
    '阙党': ['the neighborhood of Que Dang', 'Que Dang'],
    '达巷党人': ['The man of Da Xiang', 'man of the village of Da Xiang'],
    '史鱼': ['Shi Yu', 'the historian Yu'],
}

MENGZI_NAMES = {
    '孟子': ['Mencius'],
    '公孙丑': ['Gong Sun Chou', 'Gongsun Chou'],
    '万章': ['Wan Zhang'],
    '公明仪': ['Gongming Yi', 'Gong Ming Yi'],
    '公明高': ['Gongming Gao', 'Gong Ming Gao'],
    '告子': ['The philosopher Gao', 'Gao'],
    '宋牼': ['Song Keng'],
    '屋庐子': ['Wu Lu Zi'],
    '淳于髡': ['Chunyu Kun', 'Chun Yu Kun'],
    '景春': ['Jing Chun'],
    '周霄': ['Zhou Xiao'],
    '彭更': ['Peng Geng'],
    '咸丘蒙': ['Xianqiu Meng', 'Xian Qiu Meng'],
    '桃应': ['Tao Ying'],
    '曹交': ['Cao Jiao'],
    '滕更': ['Teng Geng'],
    '滕文公': ['Duke Wen of Teng'],
    '梁惠王': ['King Hui of Liang', 'King Hui'],
    '梁襄王': ['King Xiang of Liang'],
    '齐宣王': ['King Xuan of Qi', 'King Xuan'],
    '齐桓公': ['Duke Huan of Qi', 'Duke Huan'],
    '齐景公': ['Duke Jing of Qi', 'Duke Jing'],
    '齐王': ['The king of Qi', 'king of Qi', 'King of Qi'],
    '邹穆公': ['Duke Mu of Zou', 'Mu of Zou'],
    '鲁平公': ['Duke Ping of Lu'],
    '鲁君': ['The prince of Lu', 'prince of Lu', 'prince of the State of Lu'],
    '宋王': ['The king of Song', 'king of Song'],
    '孔子': ['Confucius'],
    '曾子': ['The philosopher Zeng', 'Zeng'],
    '子思': ['Zi Si'],
    '子产': ['Zi Chan'],
    '公都子': ['Gongdu Zi', 'Gong Du Zi'],
    '陈臻': ['Chen Zhen'],
    '陈代': ['Chen Dai'],
    '陈相': ['Chen Xiang'],
    '陈良': ['Chen Liang'],
    '充虞': ['Chong Yu'],
    '高子': ['Gao Zi'],
    '乐正子': ['Yuezheng Zi', 'Yue Zheng Zi'],
    '沈同': ['Shen Tong'],
    '匡章': ['Kuang Zhang'],
    '戴不胜': ['Dai Busheng', 'Dai Bu Sheng'],
    '戴盈之': ['Dai Yingzhi', 'Dai Ying Zi'],
    '夷之': ['Yi Zhi'],
    '徐辟': ['Xu Pi'],
    '储子': ['Chu Zi'],
    '盆成括': ['Pencheng Kuo'],
    '北宫锜': ['Beigong Qi', 'Bei Gong Qi'],
    '北宫黝': ['Beigong You', 'Bei Gong You'],
    '孟施舍': ['Meng Shishe', 'Meng Shi She'],
    '曾西': ['Zeng Xi'],
    '瞽瞍': ['Gu Sou'],
    '伊尹': ['Yi Yin'],
    '傅说': ['Fu Yue'],
    '管仲': ['Guan Zhong'],
    '伯夷': ['Bo Yi'],
    '周公': ['The duke of Zhou', 'duke of Zhou'],
    '尧': ['Yao'], '舜': ['Shun'], '禹': ['Yu'], '汤': ['Tang'],
    '文王': ['King Wen'], '武王': ['King Wu'],
}

# Common Chinese opening patterns -> English anchor alternatives, when no name
# matches. These describe how the unit's OWN content should open in English.
SPEAKER_ANCHORS = [
    # (regex against chinese opening, list of english openers)
    (r'^孔子[曰对答]', ['Confucius said', 'Confucius replied', 'Confucius answered']),
    (r'^子曰', ['The Master said', 'The Master replied', 'The Master answered',
                'The Master observed', 'The Master remarked', 'The Master continued']),
    (r'^子曰', ['Confucius said', 'Confucius replied']),
    (r'^曾子曰', ['The philosopher Zeng said', 'Zeng said']),
    (r'^有子曰', ['The philosopher You said', 'You said']),
    (r'^孟子曰', ['Mencius said', 'Mencius replied', 'Mencius answered',
                  'Mencius observed', 'Mencius remarked', 'Mencius proceeded',
                  'Mencius continued', "'Mencius"]),
    (r'^万章[曰问]', ['Wan Zhang said', 'Wan Zhang asked', 'Wan Zhang replied']),
    (r'^公孙丑[曰问]', ['Gong Sun Chou said', 'Gong Sun Chou asked',
                       'Gongsun Chou asked']),
    (r'^告子[曰言]', ['The philosopher Gao said', 'Gao said']),
    (r'^诗[云曰]', ['It is said in the Book of Poetry', 'In the Book of Poetry',
                    'The Book of Poetry says', 'It is said in the Shijing']),
    (r'^书[曰云]', ['The Book of History says', 'The Shu says',
                    'It is said in the Shu', 'In the Book of History']),
]


def derive_anchor(src_text: str, names: dict[str, list[str]]) -> Optional[list[str]]:
    """Given a Chinese unit's source, derive the English opening phrase(s) that
    SHOULD begin its own translation. Returns None if no derivable anchor
    (e.g. the unit is a pure continuation like 曰：...)."""
    text = src_text.strip().lstrip('「『').strip()
    # Continuation units — no own anchor; cannot use as split point
    if re.match(r'^[曰：:，]', text):
        return None
    if text.startswith('曰') or text.startswith('问曰'):
        return None
    # Try speaker anchors
    for pattern, alts in SPEAKER_ANCHORS:
        if re.match(pattern, text):
            return alts
    # Name-driven: name at start, optionally followed by 问/曰/谓/对
    for cn_name in sorted(names.keys(), key=lambda x: -len(x)):
        if text.startswith(cn_name):
            rest = text[len(cn_name):]
            en_names = names[cn_name]
            if rest.startswith('问'):
                return [f"{en} asked" for en in en_names]
            if rest[:1] in ('曰', '言', '谓'):
                return [f"{en} said" for en in en_names] + en_names
            if rest.startswith('对'):
                return [f"{en} replied" for en in en_names] + en_names
            # Bare name at start
            return en_names
    # "或问" / "或曰" patterns
    if text.startswith('或问') or text.startswith('或曰'):
        return ['Some one asked', 'Some one said', 'Somebody asked']
    # Narrative patterns: "X御" (X was driving), "X率尔而对" (X answered hastily)
    # These open with a name that the name-map already would have caught, so if
    # we got here, no name matched. Try generic "The philosopher/scholar".
    # No anchor derivable
    return None


def find_own_anchor_pos(translation: str, anchor_alts: list[str]) -> Optional[int]:
    """Find the earliest position in `translation` where any anchor alternative
    begins (case-insensitive). Used to locate where unit N+1's OWN content
    starts, so we can identify the leaked prefix from unit N."""
    t_low = translation.lower()
    best = None
    for alt in anchor_alts:
        # Prefer a position that's a sentence/clause start (preceded by space,
        # quote, or start of string)
        for m in re.finditer(re.escape(alt.lower()), t_low):
            pos = m.start()
            # Good split point if preceded by ". ", "! ", "? ", '" ', or start
            before = translation[:pos].rstrip()
            if (pos == 0 or before.endswith(('.', '!', '?', '"', ';"', '"'))
                    or before.endswith((',"', ';"'))):
                if best is None or pos < best:
                    best = pos
                    break
        # If no clean split point, accept any position as last resort
        if best is None:
            pos = t_low.find(alt.lower())
            if pos >= 0 and (best is None or pos < best):
                best = pos
    return best


def _chapter_median_ratio(en_units, cn_units):
    """Median translation-words / source-chars ratio for the chapter."""
    ratios = sorted(len(e.split()) / max(len(c), 1)
                    for e, c in zip(en_units, cn_units) if c)
    if not ratios:
        return 1.0
    return ratios[len(ratios) // 2]


def _split_backward(en, cn_units, names, median, log):
    """Backward-split pass: when unit i is OVERLOADED (its translation contains
    content for later units), find the anchor for unit i+1 inside unit i's
    translation, split there, and prepend the suffix to unit i+1.

    This handles cases like lunyu-12 u9-u12 where 4 units' worth of English is
    lumped onto one unit:
      u9 TR = "Si Ma Niu," (truncated)
      u12 TR = "Other men... Zi Xia said... Death and life... superior man..."
    The forward-leak pass moves content u12->u11->u10->u9 by finding each
    unit's anchor; the backward-split here catches the residual overload by
    detecting that u12 still contains anchors for u10/u11.
    """
    changed = True
    iterations = 0
    while changed and iterations < 12:
        changed = False
        iterations += 1
        for i in range(len(en) - 1, 0, -1):  # scan backward (latest overload first)
            cur = en[i]
            # Is unit i overloaded? Its translation is much longer than expected.
            expected = max(int(len(cn_units[i]) * median), 10)
            if len(cur.split()) < expected * 1.8:
                continue
            # Does it contain an anchor for unit i (confirming it starts correctly)?
            own_anchor = derive_anchor(cn_units[i], names)
            if own_anchor is None:
                continue
            own_pos = find_own_anchor_pos(cur, own_anchor)
            if own_pos is None or own_pos > 20:
                continue  # doesn't start with its own content; can't trust split
            # Find an anchor for the PRECEDING unit i-1 inside cur (after own_pos).
            # If found, everything from start to that anchor belongs to unit i-1.
            prev_anchor = derive_anchor(cn_units[i - 1], names)
            if prev_anchor is None:
                continue
            # Search for prev_anchor AFTER own_pos (it should appear later, as
            # the preceding unit's content got appended here)
            prev_pos = _find_anchor_after(cur, prev_anchor, own_pos + expected)
            if prev_pos is None:
                continue
            leaked = cur[:prev_pos].rstrip()
            remaining = cur[prev_pos:].strip()
            if len(leaked.split()) < 6 or len(remaining.split()) < 4:
                continue
            # Compatibility: the leaked content should contain a name from unit i-1's source
            prev_names_cn = {n for n in names if n in cn_units[i - 1]}
            if prev_names_cn:
                prev_names_en = set()
                for cn_n in prev_names_cn:
                    prev_names_en.update(names[cn_n])
                if not any(en_n.lower() in leaked.lower() for en_n in prev_names_en):
                    continue
            # Prepend leaked to unit i-1
            en[i - 1] = (en[i - 1].rstrip().rstrip(',-') + ' ' + leaked).strip()
            en[i] = remaining
            log.append({
                'unit_from': i + 1,
                'unit_to': i,
                'moved': leaked[:80],
                'src_from': cn_units[i][:60],
                'src_to': cn_units[i - 1][:60],
                'trigger': 'C-backward-split',
            })
            changed = True
            break
    return changed


def _find_anchor_after(text, anchor_alts, after_pos):
    """Like find_own_anchor_pos but only considers positions >= after_pos."""
    t_low = text.lower()
    best = None
    for alt in anchor_alts:
        for m in re.finditer(re.escape(alt.lower()), t_low):
            pos = m.start()
            if pos < after_pos:
                continue
            before = text[:pos].rstrip()
            if (before.endswith(('.', '!', '?', '"', ';"', '"'))
                    or before.endswith((',"', ';"'))):
                if best is None or pos < best:
                    best = pos
                    break
        if best is None:
            # any position after after_pos
            idx = t_low.find(alt.lower(), after_pos)
            if idx >= 0 and (best is None or idx < best):
                best = idx
    return best


def repair_chapter(cn_units: list[str], en_units: list[str], names: dict):
    """Iteratively repair forward-leaked content. Returns (new_en_units, log).

    Two complementary triggers:
      (A) MID-THOUGHT: unit i's translation ends without terminal punctuation,
          so the sentence completion leaked to the front of unit i+1.
      (B) TRUNCATED: unit i's translation is suspiciously short relative to its
          source (ratio < 0.4x chapter median) AND its source contains an
          unanswered speaker turn (e.g. a 子曰/孔子曰/孟子曰 reply). The leaked
          reply sits at the front of unit i+1, before unit i+1's own anchor.
    """
    en = list(en_units)  # mutable copy
    log = []
    median = _chapter_median_ratio(en_units, cn_units)
    changed = True
    iterations = 0
    while changed and iterations < 12:
        changed = False
        iterations += 1
        # Scan from EARLIEST to latest: a forward-leak at position i must be
        # resolved before any leak at i+1, since fixing i changes i's content
        # and may un-block or invalidate downstream repairs.
        for i in range(len(en) - 1):
            cur, nxt = en[i], en[i + 1]
            cur_ratio = len(cur.split()) / max(len(cn_units[i]), 1)

            # --- Trigger A: mid-thought ending ---
            trigger_a = not cur.rstrip().endswith(('.', '!', '?', '"'))

            # --- Trigger B: truncated unit with unanswered speaker turn ---
            # Source contains a reply/question/quote after the opening, indicating
            # the translation should be much longer than it is.
            has_reply = bool(re.search(
                r'[。？！」，；]\s*(子曰|孔子曰|孟子曰|曾子曰|有子曰|子贡曰|子路曰|曰[「：])',
                cn_units[i]))
            # Also flag: source ends with a complete quoted reply (」or 。)
            # but translation is far too short
            src_complete = bool(re.search(r'[」。！？」]\s*$', cn_units[i]))
            trigger_b = (cur_ratio < median * 0.45 and has_reply
                         and len(cur.split()) < 30)
            trigger_b_alt = (cur_ratio < median * 0.35 and src_complete
                             and len(cur.split()) < 20)
            if trigger_b_alt and not trigger_b:
                trigger_b = True

            if not (trigger_a or trigger_b):
                continue

            # Derive where unit i+1's OWN content should begin
            anchor_alts = derive_anchor(cn_units[i + 1], names)
            if anchor_alts is None:
                continue  # continuation unit; can't split
            pos = find_own_anchor_pos(nxt, anchor_alts)
            if pos is None or pos == 0:
                # Lookahead: anchor may be further ahead (multi-unit lump).
                # Search units i+2, i+3, ... for the anchor; if found at unit j,
                # pull the entire span [i+1 .. j-1]'s content + j's prefix back.
                found_j = None
                found_pos = None
                for j in range(i + 2, min(i + 6, len(en))):
                    jp = find_own_anchor_pos(en[j], anchor_alts)
                    if jp is not None:
                        found_j = j
                        found_pos = jp
                        break
                if found_j is None:
                    continue
                # GUARD: only attempt lookahead-lump when unit i is GENUINELY
                # truncated (low ratio AND short). The multi-shift guard below
                # protects against the dangerous cases, so we can be moderately
                # permissive here.
                if not (cur_ratio < median * 0.55 and len(cur.split()) < 18):
                    continue
                # Reconstruct: content from end of unit i through unit found_j
                # (up to found_pos) all belongs to unit i+1's region. Distribute
                # it across units i+1 .. found_j by the anchor of EACH of those
                # units found within the lump.
                # Simpler: concatenate i+1..found_j, then re-split by each unit's
                # own anchor in sequence.
                lump = ' '.join(en[k] for k in range(i + 1, found_j + 1))
                # find positions of anchors for i+1, i+2, ..., found_j in lump
                sub_anchors = []
                for k in range(i + 1, found_j + 1):
                    a = derive_anchor(cn_units[k], names)
                    if a is None:
                        sub_anchors.append(None)
                    else:
                        sub_anchors.append(a)
                # find first anchor (for unit i+1) in lump
                first_pos = find_own_anchor_pos(lump, sub_anchors[0]) if sub_anchors[0] else 0
                if first_pos is None:
                    continue
                # everything before first_pos is leaked to unit i
                leaked_lump = lump[:first_pos].rstrip()
                if len(leaked_lump.split()) < 4:
                    continue
                # GUARD: leaked content must not itself contain a DISTINCTIVE
                # anchor (proper name) for a unit EARLIER than i+1 — that would
                # indicate the region is already multi-shifted (content from
                # unit i-2, i-1 etc. is lumped in here). Generic discourse
                # markers ("The Master said", "Mencius said") are excluded from
                # this check because they appear throughout and would over-trigger.
                GENERIC_MARKERS = {'the master said', 'the master replied',
                                   'the master answered', 'mencius said',
                                   'mencius replied', 'confucius said',
                                   'confucius replied'}
                leaked_low = leaked_lump.lower()
                for k in range(max(0, i - 3), i + 1):
                    a = derive_anchor(cn_units[k], names)
                    if not a:
                        continue
                    for alt in a:
                        if alt.lower() in GENERIC_MARKERS:
                            continue  # too common to be a reliable signal
                        if alt.lower() in leaked_low:
                            leaked_lump = None
                            break
                    if leaked_lump is None:
                        break
                if leaked_lump is None:
                    continue
                # now split lump[first_pos:] by subsequent anchors
                rest = lump[first_pos:]
                cuts = [0]
                cursor = 0
                for k in range(1, len(sub_anchors)):
                    if sub_anchors[k] is None:
                        continue
                    p = _find_anchor_after(rest, sub_anchors[k], cursor + 3)
                    if p is not None and p > cuts[-1] + 3:
                        cuts.append(p)
                        cursor = p
                cuts.append(len(rest))
                # assign slices to units i+1 .. found_j
                new_slices = []
                ki = 1
                for ci in range(len(cuts) - 1):
                    new_slices.append(rest[cuts[ci]:cuts[ci+1]].strip())
                # pad if fewer slices than units
                while len(new_slices) < (found_j - i):
                    new_slices.append('')
                # apply
                en[i] = (cur.rstrip().rstrip(',-') + ' ' + leaked_lump).strip()
                for k in range(i + 1, found_j + 1):
                    en[k] = new_slices[k - (i + 1)] if (k - (i + 1)) < len(new_slices) else ''
                log.append({
                    'unit_from': i + 2,
                    'unit_to': i + 1,
                    'moved': leaked_lump[:80],
                    'src_from': cn_units[i + 1][:60],
                    'src_to': cn_units[i][:60],
                    'trigger': 'D-lookahead-lump',
                })
                changed = True
                break
            leaked = nxt[:pos].rstrip()
            remaining = nxt[pos:].strip()
            # Guards: don't move trivially-small prefixes, don't empty the donor
            if len(leaked.split()) < 4 or len(remaining.split()) < 4:
                continue
            # For trigger B, require the leaked content to be substantial
            # (it should contain the reply that unit i's source promised)
            if trigger_b and not trigger_a and len(leaked.split()) < 12:
                continue

            # COMPATIBILITY GUARD: in some mengzi regions the source and
            # translation are wholesale out of sync (different speakers/topics).
            # Verify the proposed split is sane: the donor unit (i+1) after the
            # move should still semantically match its own source. Check that
            # any proper-noun name in cn_units[i+1] also appears in `remaining`.
            donor_names_cn = {n for n in names if n in cn_units[i + 1]}
            if donor_names_cn:
                donor_names_en = set()
                for cn_n in donor_names_cn:
                    donor_names_en.update(names[cn_n])
                # `remaining` should contain at least one romanization of a name
                # that appears in the donor's own source. Case-insensitive.
                rem_low = remaining.lower()
                if not any(en_n.lower() in rem_low for en_n in donor_names_en):
                    continue  # donor's new content is about different people; skip

            # OVERSIZE GUARD: if the leaked prefix is much larger than the
            # receiving unit's expected translation length, this isn't a simple
            # single-unit leak — it's a multi-unit desync that this conservative
            # aligner cannot safely redistribute. Skip rather than overload.
            receiver_expected_words = max(int(len(cn_units[i]) * median), 8)
            if len(leaked.split()) > receiver_expected_words * 4:
                continue

            en[i] = (cur.rstrip().rstrip(',-') + ' ' + leaked).strip()
            en[i + 1] = remaining
            log.append({
                'unit_from': i + 2,
                'unit_to': i + 1,
                'moved': leaked[:80],
                'src_from': cn_units[i + 1][:60],
                'src_to': cn_units[i][:60],
                'trigger': 'B-truncated' if (trigger_b and not trigger_a) else 'A-midthought',
            })
            changed = True
            break  # restart scan after a change (content shifted)

        # --- Trigger C: backward-split (overloaded unit) ---
        # If we completed a full forward-leak scan with no changes, try the
        # inverse: split overloaded units that contain preceding units' content.
        if not changed and i == len(en) - 2:
            if _split_backward(en, cn_units, names, median, log):
                changed = True
    return en, log


def process_book(book: str, apply: bool, review_path: str):
    names = LUNYU_NAMES if book == 'lunyu' else MENGZI_NAMES
    review_lines = []
    stats = {'chapters': 0, 'units': 0, 'chapters_changed': 0,
             'units_changed': 0, 'moves': 0}

    for path in sorted(glob.glob(f'content/books/{book}/chapters/*.json')):
        with open(path, encoding='utf-8') as f:
            ch = json.load(f)
        units = ch['chapter']['reading_units']
        cn_units = [u['text'].replace('\n', ' ') for u in units]
        en_units = [u['canonical_translations'][0]['text'] for u in units]
        stats['chapters'] += 1
        stats['units'] += len(units)

        new_en, log = repair_chapter(cn_units, en_units, names)
        if not log:
            continue  # chapter unchanged

        stats['chapters_changed'] += 1
        stats['moves'] += len(log)
        # Count distinct units changed
        changed_idx = set()
        for entry in log:
            changed_idx.add(entry['unit_from'] - 1)
            changed_idx.add(entry['unit_to'] - 1)
        stats['units_changed'] += len(changed_idx)

        review_lines.append(f"\n## {os.path.basename(path)}  "
                            f"({len(log)} move{'s' if len(log)!=1 else ''})\n")
        for entry in log:
            review_lines.append(
                f"- [{entry['trigger']}] moved FROM u{entry['unit_from']} -> TO u{entry['unit_to']}: "
                f"\"{entry['moved']}...\"")
            review_lines.append(f"  - u{entry['unit_from']} SRC: `{entry['src_from']}`")
            review_lines.append(f"  - u{entry['unit_to']}   SRC: `{entry['src_to']}`")

        # Show before/after for each changed unit
        review_lines.append("\n  **Before/after:**")
        for idx in sorted(changed_idx):
            old = en_units[idx]
            new = new_en[idx]
            if old != new:
                review_lines.append(f"  - u{idx+1} SRC: `{cn_units[idx][:55]}`")
                review_lines.append(f"    - OLD: {old[:140]}")
                review_lines.append(f"    - NEW: {new[:140]}")

        if apply:
            for i, u in enumerate(units):
                if new_en[i] != en_units[i]:
                    u['canonical_translations'][0]['text'] = new_en[i]
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(ch, f, ensure_ascii=False, indent=2)
                f.write('\n')
            with open(path, encoding='utf-8') as f:
                json.load(f)  # validate

    mode = "APPLIED" if apply else "DRY-RUN"
    header = (f"# Realignment review ({book}) — {mode}\n\n"
              f"Chapters: {stats['chapters']} (changed: {stats['chapters_changed']}) | "
              f"Units: {stats['units']} (changed: {stats['units_changed']}) | "
              f"Moves: {stats['moves']}\n")
    with open(review_path, 'w', encoding='utf-8') as f:
        f.write(header + '\n'.join(review_lines) + '\n')

    print(f"[{mode}] {book}: chapters_changed={stats['chapters_changed']}, "
          f"units_changed={stats['units_changed']}, moves={stats['moves']}")
    print(f"  Review: {review_path}")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book', choices=['lunyu', 'mengzi', 'both'])
    ap.add_argument('--apply', action='store_true',
                    help='Write changes (default: dry-run only)')
    args = ap.parse_args()

    books = ['lunyu', 'mengzi'] if args.book == 'both' else [args.book]
    suffix = 'apply' if args.apply else 'dryrun'
    for b in books:
        process_book(b, apply=args.apply,
                     review_path=f'tools/realign_review_{b}_{suffix}.md')


if __name__ == '__main__':
    main()
