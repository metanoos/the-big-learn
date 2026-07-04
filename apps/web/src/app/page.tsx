import Link from "next/link";
import { getBooks, type Book } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Library() {
  let books: Book[] = [];
  let error = "";
  try {
    books = await getBooks();
  } catch (e: any) {
    error = e.message;
  }

  const v1 = books.filter((b) => b.v1);
  const deferred = books.filter((b) => !b.v1);

  return (
    <div className="space-y-10">
      <section>
        <h1 className="font-serif text-2xl text-stone-900 mb-1">The Big Learn</h1>
        <p className="text-stone-600 text-sm leading-relaxed max-w-prose">
          A collaborative translation platform for classical Chinese. Read line
          by line, see canonical translations beside reader submissions, vote on
          the ones that resonate, and — when you're moved — posit your own
          translation and get feedback before publishing.
        </p>
        <p className="text-stone-500 text-xs leading-relaxed max-w-prose mt-3 italic">
          This is new. Every canonical line already has James Legge's
          translation (public domain) to read against — but the reader
          translations, the comments, the voting are all still to be built by
          the people who show up early. If that's you, welcome.
        </p>
      </section>

      {error && (
        <p className="text-rose-600 text-sm">
          Couldn't reach the API: {error}. Is the backend running on :8080?
        </p>
      )}

      <section>
        <h2 className="text-xs uppercase tracking-wider text-stone-400 mb-3">
          Curriculum · v1
        </h2>
        <div className="grid gap-3">
          {v1.map((b) => (
            <BookCard key={b.slug} book={b} />
          ))}
        </div>
      </section>

      {deferred.length > 0 && (
        <section>
          <h2 className="text-xs uppercase tracking-wider text-stone-400 mb-3">
            More texts (deferred · not yet v1)
          </h2>
          <div className="grid gap-3 opacity-70">
            {deferred.map((b) => (
              <BookCard key={b.slug} book={b} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function BookCard({ book }: { book: Book }) {
  return (
    <Link
      href={`/books/${book.slug}`}
      className="block px-4 py-3 bg-white border border-stone-200 rounded hover:border-stone-400 transition-colors"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-serif text-stone-900">{book.title}</span>
        <span className="text-xs text-stone-400">{book.chapter_count} ch</span>
      </div>
      {book.source_title && (
        <span className="text-xs text-stone-500">{book.source_title}</span>
      )}
    </Link>
  );
}
