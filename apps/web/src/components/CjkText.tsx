// CjkText is the plain-Display path for Chinese text that should NOT be
// annotated: no pinyin ruby, no per-char click targets. Used for book titles,
// source titles, comment bodies, activity snippets — anywhere we want the CJK
// serif stack and correct glyph rendering without the reading-surface machinery.
//
// Distinct from AnnotatedText (which builds pinyin ruby + click handlers and
// requires a pre-built PinyinMap). When you just want the glyphs to render
// right, use this; when you want the reader-surface annotation, use AnnotatedText.
//
// No "use client": this is a pure presentational wrapper, safe in Server and
// Client components alike.

export function CjkText({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <span className={`cjk ${className}`.trim()}>{children}</span>;
}
