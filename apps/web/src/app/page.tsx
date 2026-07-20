import { getBooks } from "@/lib/api";
import { LibraryBooks } from "@/components/LibraryBooks";

// Home is the library. The pitch lives in the heading ("Read the books that
// shaped the Chinese character") and the section intros; there's no separate
// landing page. Server-rendered for canonical content (catalog, chapter
// counts); LibraryBooks layers the signed-in reader's progress on top and
// groups books into named sections (Four Books → Daoist → Five Classics → …).
export const dynamic = "force-dynamic";

export default async function Home() {
  let books: import("@/lib/api").Book[] = [];
  let error = "";
  try {
    books = await getBooks();
  } catch (e: any) {
    error = e.message;
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="font-serif text-2xl text-stone-900 dark:text-stone-100 mb-1">
          Read the books that shaped the Chinese character.
        </h1>
      </section>

      {error && (
        <p className="text-rose-600 dark:text-rose-400 text-sm">
          Couldn't reach the API: {error}. Is the backend running on :8180?
        </p>
      )}

      <LibraryBooks books={books} />
    </div>
  );
}
