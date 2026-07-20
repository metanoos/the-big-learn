"use client";

// CharacterPopover is the speech-bubble that opens above a clicked CJK char.
// It's portaled to <body> and positioned with `position: fixed` so it floats
// above the page chrome (sticky NavBar, pinned ChatBar) instead of pushing
// content down like the old inline card did.
//
// Placement: above the char by default — reading flow means text above the
// clicked char is already-read, so the bubble never obstructs what's next. It
// may overlap the sticky navbar (z-50 sits above z-10); it only flips below
// when the bubble would actually clip off the top of the viewport. A small
// rotated-square notch points at the char's horizontal center, re-pointing on
// flip.
//
// The bubble tracks the anchor on scroll/resize (the anchor is in normal page
// flow; the portal isn't), so listeners recompute while open. No scroll-lock —
// reading should stay unobstructed and the bubble follows along.
//
// Dismissal is owned by ChapterReader (click-anywhere-outside + Escape here).
// The root carries [data-char-popover] so the dismiss listener treats clicks
// inside the bubble as inside the reader (doesn't close on internal clicks).
//
// (File kept as CharacterPopover.tsx so the existing import path is stable;
// the export is CharacterPopover.)

import { useEffect, useLayoutEffect, useState } from "react";
import { createPortal } from "react-dom";
import { type WordSpan } from "@/lib/api";
import { addReviewEntry } from "@/lib/reviewChars";
import { CharBreakdown, splitWordPinyin } from "./CharBreakdown";

type Placement = "above" | "below";
type Pos = { top: number; left: number; placement: Placement; arrowX: number } | null;

// Vertical gap between the bubble and the char. The bubble may overlap the
// sticky navbar (it's translucent chrome and the popover sits at z-50, above
// the navbar's z-10), so no navbar clearance is reserved — text above the
// clicked char is already-read, so "above" is always the better side for
// reading flow. We only flip below when the bubble would actually clip off the
// top of the viewport.
const GAP = 8;
// Minimum top margin — the bubble's top edge must stay this far from the
// viewport's top so the notch/card aren't flush against the screen edge.
const TOP_MARGIN = 4;

export function CharacterPopover({
  char,
  anchor,
  word,
  onClose,
}: {
  char: string;
  anchor: HTMLElement | null;
  // The compound the clicked char belongs to (null if the char stands alone,
  // or word spans aren't in use for this line). When the word is multi-char
  // AND has a gloss, a word-level section renders above the per-char defs —
  // the token's meaning, on top of the breakdown. Single-char words or null
  // gloss render the per-char-only view (the legacy behavior).
  word?: WordSpan | null;
  onClose: () => void;
}) {
  // showWord: does this click carry a real multi-char token with a gloss? When
  // true, the bubble shows the word section AND a per-constituent-char
  // breakdown (one row per char in the word). When false, it renders the
  // legacy single-char view. Derived up here because the fetch effect below
  // needs it to decide which chars to look up.
  const showWord = !!word && word.word.length > 1 && !!word.gloss;
  // The chars we'll show breakdown rows for: every char in the word (when the
  // word layer is on), or just the clicked char.
  const charsToShow = showWord && word ? Array.from(word.word) : [char];
  // Per-char pinyin carved from the word's build-time reading (one syllable per
  // char, aligned to charsToShow). Empty when there's no word context; the
  // breakdown then falls back to each char's index reading at render.
  const charPinyin = showWord && word
    ? splitWordPinyin(word.pinyin, charsToShow.length)
    : null;

  const [pos, setPos] = useState<Pos>(null);
  // The portal target is set in an effect so SSR doesn't try to touch document.
  const [mounted, setMounted] = useState(false);

  // Save the expanded token to the reader's per-browser review list. When the
  // click opened a compound, save the whole compound with its build-time
  // pinyin AND its word-level gloss + provenance — so the dashboard expansion
  // can render the word def above the per-char breakdown, matching this
  // popover. Single-char clicks save just the char. MRU-promotes on re-open.
  useEffect(() => {
    if (showWord && word) {
      addReviewEntry(
        word.word,
        word.pinyin ?? undefined,
        word.gloss ?? undefined,
        word.source,
      );
    } else {
      addReviewEntry(char);
    }
  }, [char, word, showWord]);

  // Escape closes. No scroll-lock or autofocus — both would defeat the point
  // of a floating bubble (locking the body or yanking focus interrupts reading).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => setMounted(true), []);

  // Position the bubble relative to the anchor. Recomputed on scroll/resize so
  // the bubble stays glued to the char as the reader scrolls, AND on the
  // bubble's own size changes (a ResizeObserver on the bubble) — so when the
  // breakdown rows stream in and the bubble grows, it re-anchors and re-flips
  // instead of clipping or leaving the notch misaligned. The char defs are now
  // fetched inside CharBreakdown (not hoisted here), so self-observation is
  // what catches those layout changes; the parent no longer tracks fetch state.
  // useLayoutEffect avoids a flash of the bubble at (0,0) before the first
  // measurement lands.
  useLayoutEffect(() => {
    if (!anchor) return;
    const el = document.querySelector("[data-char-popover]") as HTMLElement | null;
    const measure = () => {
      if (!anchor) return;
      // Anchor gone from the DOM → close (the line was unmounted, e.g. nav).
      if (!anchor.isConnected) {
        onClose();
        return;
      }
      const a = anchor.getBoundingClientRect();
      const bubbleW = el?.offsetWidth ?? 0;
      const bubbleH = el?.offsetHeight ?? 0;
      const vw = document.documentElement.clientWidth;

      // Prefer above (reading flow: text above the char is already-read, text
      // below is unread, so above never obstructs what's next). Flip below only
      // when the bubble would clip off the top of the viewport — the bubble is
      // allowed to overlap the sticky navbar (z-50 sits above z-10).
      const roomAbove = a.top - TOP_MARGIN;
      const placement: Placement =
        roomAbove >= bubbleH + GAP ? "above" : "below";

      // Center the bubble on the char's midpoint, clamped into the viewport.
      const center = a.left + a.width / 2;
      const margin = 8;
      const maxLeft = vw - bubbleW - margin;
      let left = center - bubbleW / 2;
      left = Math.max(margin, Math.min(left, maxLeft));

      // Arrow x is the offset from the bubble's left edge to the char center.
      // Clamped so the notch never escapes the bubble.
      let arrowX = center - left;
      const arrowMin = 14;
      const arrowMax = bubbleW - 14;
      arrowX = Math.max(arrowMin, Math.min(arrowX, arrowMax));

      const top =
        placement === "above"
          ? a.top - bubbleH - GAP
          : a.bottom + GAP;

      setPos({ top, left, placement, arrowX });
    };
    measure();
    // Capture-phase scroll so we react before the paint shows a stale bubble.
    document.addEventListener("scroll", measure, true);
    window.addEventListener("resize", measure);
    // Self-observe: when the bubble's box changes (rows populating, word
    // section rendering), re-measure so placement + arrow stay correct.
    const ro = el ? new ResizeObserver(() => measure()) : null;
    if (el && ro) ro.observe(el);
    return () => {
      document.removeEventListener("scroll", measure, true);
      window.removeEventListener("resize", measure);
      ro?.disconnect();
    };
  }, [anchor, word, onClose]);

  if (!mounted) return null;

  const body = (
    <div
      role="note"
      aria-label={`Definition of ${char}`}
      aria-live="polite"
      data-char-popover
      className="char-popover"
      style={
        pos
          ? {
              position: "fixed",
              top: `${pos.top}px`,
              left: `${pos.left}px`,
              // CSS var consumed by the ::before notch so it tracks the char.
              ["--arrow-x" as string]: `${pos.arrowX}px`,
            }
          : { position: "fixed", top: "-9999px", left: "-9999px", visibility: "hidden" }
      }
      data-placement={pos?.placement ?? "above"}
    >
      {showWord && (
        <div className="cjk-word-section">
          {/* text-lg lives on the container (not the word span) so the pinyin
              span's 0.48em resolves against the word's size — same pinyin:char
              proportion and stone-400/500 color as the reader's ruby > rt. The
              word itself carries .cjk-inline so the compound renders in the same
              serif as the reading surface and book titles (it previously
              inherited sans + font-semibold, the only CJK title that did). */}
          <div className="flex items-baseline gap-2 flex-wrap text-lg">
            <span className="cjk-inline">{word!.word}</span>
            {word!.pinyin && (
              <span className="text-[0.48em] text-stone-400 dark:text-stone-500">
                {word!.pinyin}
              </span>
            )}
          </div>
          <div className="mt-0.5 text-sm">{word!.gloss}</div>
          {/* Provenance label so the reader knows whether this is a curated
              classical sense or CC-CEDICT's modern-Mandarin gloss. Honest
              framing: the modern gloss is a starting point, not a classical
              authority. */}
          <div className="mt-1 text-[10px] uppercase tracking-wide text-stone-400 dark:text-stone-500">
            {word!.source === "classical-override"
              ? "classical (curated)"
              : word!.source === "CC-CEDICT"
                ? "CC-CEDICT (modern)"
                : ""}
          </div>
        </div>
      )}
      {/* Per-char breakdown, shared with the dashboard's saved-token panel via
          CharBreakdown — a token reads identically whether expanded here, in the
          reader, or on the dashboard. One row per constituent char; the word
          section above (when present) carries the token-level gloss. */}
      <CharBreakdown chars={charsToShow} pinyinOverride={charPinyin} />
    </div>
  );

  return createPortal(body, document.body);
}
