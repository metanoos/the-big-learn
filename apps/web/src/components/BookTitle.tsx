// BookTitle — the three-part book name rendered with pinyin ruby above the
// Chinese characters, then the English label after a middle dot. Matches the
// reader's per-character pinyin rendering (same <ruby>/<rt> pattern + the one
// `ruby > rt` rule in globals.css: 0.48em, stone-400/500) so a book title's
// pinyin reads identically to pinyin above chars everywhere else.
//
// Used everywhere a book name appears: library cards, book detail header,
// dashboard rows, activity feed. Pass the whole book-like object so the
// structured name fields are available; if they're missing, degrades to
// display_name → title → slug (today's behavior).
//
// No "use client": presentational only, safe in Server and Client components.

import { CjkText } from "./CjkText";

export type BookName = {
  name_zh?: string;
  name_pinyin?: string;
  name_en?: string;
  display_name?: string;
  title?: string;
  slug: string;
};

// CJK Unified Ideographs. Used to pair each Chinese character with one
// pinyin syllable; non-CJK runes render bare and don't consume a syllable.
function isCJK(ch: string): boolean {
  const c = ch.codePointAt(0)!;
  return c >= 0x4e00 && c <= 0x9fff;
}

export function BookTitle({
  book,
  size = "card",
  className = "",
}: {
  book: BookName;
  size?: "card" | "page";
  className?: string;
}) {
  const zh = book.name_zh;

  // No Chinese name at all → fall back to display_name / title / slug as a
  // plain string. Keeps older catalogs rendering.
  if (!zh) {
    const fallback = book.display_name ?? book.title ?? book.slug;
    return (
      <CjkText className={className}>
        {fallback}
      </CjkText>
    );
  }

  const sizeClass = size === "page" ? "text-2xl" : "";

  return (
    <AnnotatedName
      zh={zh}
      pinyin={book.name_pinyin}
      en={book.name_en}
      className={`${sizeClass} ${className}`.trim()}
    />
  );
}

// AnnotatedName — the shared ruby+English rendering behind BookTitle. Chinese
// characters carry pinyin ruby above (one syllable per CJK char), then the
// English label after a middle dot. Same <ruby>/<rt> pattern + globals.css rt
// styling as the reader's per-character pinyin.
//
// BookTitle is the book-name specialist (it owns the display_name → title →
// slug fallback); this is the bare presentation, reused by curriculum section
// headings (LibraryBooks) and anywhere else a zh+pinyin+en name renders without
// book-specific fallbacks.
export function AnnotatedName({
  zh,
  pinyin,
  en,
  className = "",
}: {
  zh?: string;
  pinyin?: string;
  en?: string;
  className?: string;
}) {
  // No Chinese name at all → render the English alone (or nothing). Callers
  // that have a string fallback (e.g. BookTitle's slug path) handle it
  // themselves before reaching here.
  if (!zh) {
    return en ? <span className={className}>{en}</span> : null;
  }

  const chars = Array.from(zh);
  const syllables = pinyin ? pinyin.split(/\s+/).filter(Boolean) : [];
  const cjkCount = chars.filter(isCJK).length;
  // Pinyin must have one syllable per CJK character or the ruby alignment
  // would be wrong. If it doesn't (mis-curated data), degrade to plain zh
  // rather than render misleading ruby. Honest fallback.
  const aligned = syllables.length === cjkCount;

  return (
    <span className={className}>
      {aligned ? (
        chars.map((ch, i) => {
          // Walk a separate index for syllables so non-CJK runes don't
          // consume one. (Defensive — these titles are all-CJK today.)
          return (
            <CharWithRuby key={i} ch={ch} syllable={syllableFor(ch, i, chars, syllables)} />
          );
        })
      ) : (
        <CjkText>{zh}</CjkText>
      )}
      {en && (
        <span className="text-stone-500 dark:text-stone-400 group-hover:[color:inherit] font-sans font-normal">
          {" · "}
          {en}
        </span>
      )}
    </span>
  );
}

// One <ruby>char<rt>syllable</rt></ruby> for a CJK char, or bare text for
// non-CJK. syllableFor pre-computes the right syllable per char index. The
// `ruby-display` class is kept as a hook but carries no styling of its own —
// the <rt> picks up the shared `ruby > rt` rule (see globals.css), so a title
// char's pinyin matches the reader body's exactly.
function CharWithRuby({ ch, syllable }: { ch: string; syllable: string | null }) {
  if (!isCJK(ch) || syllable === null) {
    return <CjkText>{ch}</CjkText>;
  }
  return (
    <ruby className="ruby-display">
      <CjkText>{ch}</CjkText>
      <rt>{syllable}</rt>
    </ruby>
  );
}

// Map a char's index to its syllable. syllables pair with CJK chars in order;
// we count CJK chars up to (and including) index i to find the matching one.
function syllableFor(
  _ch: string,
  i: number,
  chars: string[],
  syllables: string[],
): string | null {
  if (!isCJK(chars[i])) return null;
  let cjkIndex = 0;
  for (let k = 0; k < i; k++) {
    if (isCJK(chars[k])) cjkIndex++;
  }
  return syllables[cjkIndex] ?? null;
}
