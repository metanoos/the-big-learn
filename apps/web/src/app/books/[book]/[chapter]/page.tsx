import Link from "next/link";
import { getChapter } from "@/lib/api";
import { LineView } from "@/components/LineView";

export const dynamic = "force-dynamic";

export default async function ChapterPage({
  params,
}: {
  params: Promise<{ book: string; chapter: string }>;
}) {
  const { book, chapter } = await params;
  const chapterNum = Number(chapter);
  let ch;
  try {
    ch = await getChapter(book, chapterNum);
  } catch (e: any) {
    return (
      <div className="text-stone-600 text-sm">
        {e.message}.{" "}
        <Link href={`/books/${book}`} className="underline">Back to {book}</Link>
      </div>
    );
  }

  const count = ch.chapter.reading_unit_count;
  const prev = chapterNum > 1 ? chapterNum - 1 : null;
  const next = chapterNum < 1000 ? chapterNum + 1 : null; // bound check via unit count below

  return (
    <div className="space-y-8">
      <div>
        <Link href={`/books/${book}`} className="text-xs text-stone-400 hover:text-stone-600">
          ← {book}
        </Link>
        <h1 className="font-serif text-xl text-stone-900 mt-2 cjk">
          {ch.chapter.title}
        </h1>
      </div>

      <div className="divide-y divide-stone-200">
        {ch.chapter.reading_units.map((u) => (
          <LineView
            key={u.id}
            book={book}
            chapter={chapterNum}
            unit={u}
          />
        ))}
      </div>

      <nav className="flex justify-between text-sm pt-4">
        {prev ? (
          <Link href={`/books/${book}/${prev}`} className="text-stone-600 hover:text-stone-900">
            ← Chapter {prev}
          </Link>
        ) : (
          <span />
        )}
        {next && next <= count + chapterNum && (
          <Link href={`/books/${book}/${next}`} className="text-stone-600 hover:text-stone-900">
            Chapter {next} →
          </Link>
        )}
      </nav>
    </div>
  );
}
