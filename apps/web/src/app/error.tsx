"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="space-y-3 py-8">
      <h1 className="font-serif text-2xl text-stone-900 dark:text-stone-100">
        The library could not load this page.
      </h1>
      <p className="text-sm text-stone-500 dark:text-stone-400">
        The content service may be temporarily unavailable. Your saved reading data is still on this device.
      </p>
      <button
        type="button"
        onClick={reset}
        className="min-h-11 rounded bg-stone-800 px-4 text-sm text-white hover:bg-stone-700 dark:bg-stone-200 dark:text-stone-900 dark:hover:bg-stone-300"
      >
        Try again
      </button>
    </div>
  );
}
