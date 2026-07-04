import Link from "next/link";
import { getBooks, getChapter, type Book, type Chapter } from "@/lib/api";
import { displayName } from "@/lib/titles";

export const dynamic = "force-dynamic";

export default async function BookPage({
  params,
}: {
  params: Promise<{ book: string }>;
}) {
  const { book } = await params;

  // Fetch books list + first chapter in parallel.
  let books: Book[] = [];
  let first: Chapter | null = null;
  let loadError = "";
  try {
    [books, first] = await Promise.all([
      getBooks(),
      getChapter(book, 1).catch(() => null),
    ]);
  } catch (e: any) {
    loadError = e.message;
  }

  const meta = books.find((b) => b.slug === book);
  if (!meta) {
    return (
      <div className="text-stone-600 text-sm">
        Book “{book}” not found.{" "}
        <Link href="/" className="underline">Back to library</Link>
        {loadError && <span className="block text-stone-400 mt-2">{loadError}</span>}
      </div>
    );
  }
  const count = meta.chapter_count;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/" className="text-xs text-stone-400 hover:text-stone-600">
          ← Library
        </Link>
        <h1 className="font-serif text-2xl text-stone-900 mt-2">
          {displayName(meta.slug)}
        </h1>
        {first?.source_title && (
          <p className="text-sm text-stone-500">{first.source_title}</p>
        )}
        <p className="text-xs text-stone-400 mt-1">
          {count} chapter{count === 1 ? "" : "s"} · seed translation: James Legge (public domain)
        </p>
      </div>

      <ol className="space-y-1">
        {Array.from({ length: count }, (_, i) => i + 1).map((n) => (
          <li key={n}>
            <Link
              href={`/books/${book}/${n}`}
              className="block px-3 py-2 hover:bg-stone-100 rounded text-sm text-stone-700"
            >
              <span className="text-stone-400 mr-3">第{n}章</span>
              Chapter {n}
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}
