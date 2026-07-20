import Link from "next/link";

export default function NotFound() {
  return (
    <div className="space-y-3 py-8">
      <h1 className="font-serif text-2xl text-stone-900 dark:text-stone-100">
        This page is not in the library.
      </h1>
      <p className="text-sm text-stone-500 dark:text-stone-400">
        The book or chapter may have moved, or it may not have been ingested yet.
      </p>
      <Link href="/" className="inline-block text-sm underline underline-offset-4">
        Return to the library
      </Link>
    </div>
  );
}
