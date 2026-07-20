// The "about this book" block shown above a book's chapter list. Renders the
// longer `background` paragraph when the catalog carries one, falling back to
// the shorter `blurb` so every book shows something — placeholder catalogs
// (Shi Jing, Zhuangzi, the sutras, ...) ship a blurb today and a fuller
// background only once they're ingested. When neither is present we render
// nothing rather than a gap.
//
// This is plain presentational text, no client behavior — server component.
import type { Book } from "@/lib/api";

export function BookBackground({ book }: { book: Book }) {
  const text = book.background ?? book.blurb;
  if (!text) return null;
  return (
    <p className="text-sm leading-relaxed text-stone-600 dark:text-stone-300">
      {text}
    </p>
  );
}
