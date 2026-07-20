// Cross-link block for the commentary relationship between two books. The
// relationship is encoded one-way in the catalog (`commentary_on`), e.g.
// Zuozhuan → chun-qiu; this component renders it from either side.
//
// Two distinct framings, because the relationship is asymmetric in practice:
//
//   - On the COMMENTARY (e.g. Zuozhuan): a soft "expands the [parent]" link.
//     Zuozhuan stands on its own as a work of narrative prose, so the parent
//     is referenced, not required.
//
//   - On the PARENT (e.g. Chun Qiu): a stronger caveat. The Chun Qiu alone is
//     a bare annal — nearly unreadable without the narrative Zuozhuan carries
//     — so we explicitly direct the reader to the commentary rather than let
//     them click into a date table.
//
// A book can in principle be both (no current case, but the schema allows it).
// No "use client" — server component, just presentational links.
import Link from "next/link";
import type { Book } from "@/lib/api";
import { displayName } from "@/lib/titles";

export function BookPairing({
  book,
  parent,
  commentaries,
}: {
  book: Book;
  parent: Book | null;
  commentaries: Book[];
}) {
  if (!parent && commentaries.length === 0) return null;

  return (
    <div className="space-y-2">
      {/* This book comments on a parent text. Soft framing — the commentary is
          standalone-readable, the parent is referenced as context. */}
      {parent && (
        <p className="text-sm text-stone-500 dark:text-stone-400">
          Expands{" "}
          <Link
            href={`/books/${parent.slug}`}
            className="underline decoration-stone-300 dark:decoration-stone-600 hover:text-stone-700 dark:hover:text-stone-200"
          >
            {displayName(parent)}
          </Link>
          .
        </p>
      )}

      {/* This book is the parent of one or more commentaries. Stronger framing
          — for the Chun Qiu case the bare text is nearly useless alone, so we
          actively direct the reader to the commentary for the narrative. */}
      {commentaries.length > 0 && (
        <p className="text-sm text-stone-500 dark:text-stone-400">
          For the narrative,{" "}
          {commentaries.map((c, i) => (
            <span key={c.slug}>
              {i > 0 && (i === commentaries.length - 1 ? " or " : ", ")}
              <Link
                href={`/books/${c.slug}`}
                className="underline decoration-stone-300 dark:decoration-stone-600 hover:text-stone-700 dark:hover:text-stone-200"
              >
                {displayName(c)}
              </Link>
            </span>
          ))}
          {" "}{commentaries.length === 1 ? "expands" : "expand"} {displayName(book)}.
        </p>
      )}
    </div>
  );
}
