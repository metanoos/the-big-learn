"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { exportReaderData, importReaderData } from "@/lib/readerData";

export function ReaderDataControls() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState("");

  function download() {
    try {
      const backup = exportReaderData();
      const blob = new Blob([JSON.stringify(backup, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `the-big-learn-reader-data-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("Backup downloaded.");
    } catch {
      setMessage("This browser blocked the backup download.");
    }
  }

  async function restore(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const imported = importReaderData(JSON.parse(await file.text()));
      setMessage(`Restored ${imported} reader settings. Reloading…`);
      window.setTimeout(() => window.location.reload(), 400);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not restore this backup.");
      event.target.value = "";
    }
  }

  return (
    <section className="border-t border-stone-200 pt-6 dark:border-stone-800">
      <h2 className="mb-2 text-xs uppercase tracking-wider text-stone-400 dark:text-stone-500">
        Reader data
      </h2>
      <p className="mb-3 text-sm text-stone-500 dark:text-stone-400">
        Download a private JSON backup of this browser&apos;s progress, saved
        lines, saved words, and display settings. Restore it on another device.
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={download}
          className="min-h-11 rounded border border-stone-300 px-3 text-sm text-stone-700 hover:bg-stone-100 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-900"
        >
          Download backup
        </button>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="min-h-11 rounded border border-stone-300 px-3 text-sm text-stone-700 hover:bg-stone-100 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-900"
        >
          Restore backup
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/json,.json"
          onChange={restore}
          hidden
          tabIndex={-1}
        />
      </div>
      {message && (
        <p className="mt-2 text-xs text-stone-500 dark:text-stone-400" role="status">
          {message}
        </p>
      )}
    </section>
  );
}
