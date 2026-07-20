// Per-browser reading progress + line bookmarks. Stored in localStorage —
// there are no accounts, so the device-local store IS the source of truth for
// these. Reading progress and saved lines both work fully without a server
// round-trip and never leave the browser.
//
// Three keys:
//   - "tbl:read"             → string[] of `"book:chapter"` (read chapter set)
//   - "tbl:bookmarks"        → string[] of `"book:chapter:line"` (saved lines)
//   - "tbl:bookmark-details" → saved Chinese + translation previews by key
//
// All accessors are SSR-safe: they no-op on the server and survive a corrupt
// JSON blob without throwing. Writes broadcast a custom event so same-tab
// subscribers (library overlay, dashboard) can re-read live; cross-tab updates
// arrive through the native `storage` event, which listeners opt into.

const READ_KEY = "tbl:read";
const BOOKMARKS_KEY = "tbl:bookmarks";
const BOOKMARK_DETAILS_KEY = "tbl:bookmark-details";
export const READ_CHANGED_EVENT = "tbl:read-changed";
export const BOOKMARKS_CHANGED_EVENT = "tbl:bookmarks-changed";

// Read a string[] key defensively: only arrays of non-empty strings survive.
function readList(key: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x): x is string => typeof x === "string" && x.length > 0);
  } catch {
    return [];
  }
}

function writeList(key: string, event: string, list: string[], detail?: string) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(list));
    // Same-tab notification. The library overlay, chapter list, and dashboard
    // listen for this so progress saved while reading appears elsewhere.
    // `detail` carries the single changed entry key (e.g. "book:chapter:line")
    // so per-line subscribers can skip a full localStorage re-read when a
    // different entry changed — a chapter has many LineView instances, and
    // without this every one of them would re-parse the bookmark list on each
    // click. Cross-tab updates arrive via the native `storage` event instead.
    window.dispatchEvent(new CustomEvent(event, { detail }));
  } catch {
    /* quota / disabled storage — progress is best-effort, never fatal */
  }
}

// --- read chapters ---------------------------------------------------------

export function readKey(book: string, chapter: number) {
  return `${book}:${chapter}`;
}

export function getReadChapters(): Set<string> {
  return new Set(readList(READ_KEY));
}

export function isRead(book: string, chapter: number): boolean {
  return getReadChapters().has(readKey(book, chapter));
}

export function markChapterReadLocal(book: string, chapter: number) {
  const next = Array.from(new Set([...readList(READ_KEY), readKey(book, chapter)]));
  writeList(READ_KEY, READ_CHANGED_EVENT, next);
}

export function markChapterUnreadLocal(book: string, chapter: number) {
  const key = readKey(book, chapter);
  const next = readList(READ_KEY).filter((k) => k !== key);
  writeList(READ_KEY, READ_CHANGED_EVENT, next);
}

// Mark every chapter [1..total] for `book` read (or unread). Symmetric with
// markChapterReadLocal/Unread so the chapter-list + library callers can flip
// a whole book at once.
export function markBookReadLocal(book: string, total: number) {
  const have = new Set(readList(READ_KEY));
  for (let n = 1; n <= total; n++) have.add(readKey(book, n));
  writeList(READ_KEY, READ_CHANGED_EVENT, Array.from(have));
}

export function markBookUnreadLocal(book: string) {
  const next = readList(READ_KEY).filter((k) => !k.startsWith(`${book}:`));
  writeList(READ_KEY, READ_CHANGED_EVENT, next);
}

// --- bookmarks (saved lines) -----------------------------------------------
//
// The reader's heart is a private bookmark. It fills from this device-local
// record on reload and the dashboard lists the same data.

export function bookmarkKey(book: string, chapter: number, line: number) {
  return `${book}:${chapter}:${line}`;
}

export function getBookmarks(): string[] {
  return readList(BOOKMARKS_KEY);
}

export type BookmarkPreview = {
  text: string;
  translation?: string;
};

export function getBookmarkPreviews(): Record<string, BookmarkPreview> {
  if (typeof window === "undefined") return {};
  try {
    const parsed: unknown = JSON.parse(
      window.localStorage.getItem(BOOKMARK_DETAILS_KEY) || "{}",
    );
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const previews: Record<string, BookmarkPreview> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (!value || typeof value !== "object" || Array.isArray(value)) continue;
      const candidate = value as { text?: unknown; translation?: unknown };
      if (typeof candidate.text !== "string" || candidate.text.length === 0) continue;
      previews[key] = {
        text: candidate.text,
        ...(typeof candidate.translation === "string" && candidate.translation.length > 0
          ? { translation: candidate.translation }
          : {}),
      };
    }
    return previews;
  } catch {
    return {};
  }
}

export function saveBookmarkPreviews(previews: Record<string, BookmarkPreview>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(BOOKMARK_DETAILS_KEY, JSON.stringify(previews));
  } catch {
    /* quota / disabled storage — the bookmark itself still remains usable */
  }
}

export function isBookmarked(book: string, chapter: number, line: number): boolean {
  return getBookmarks().includes(bookmarkKey(book, chapter, line));
}

export function addBookmark(
  book: string,
  chapter: number,
  line: number,
  preview?: BookmarkPreview,
) {
  const key = bookmarkKey(book, chapter, line);
  if (preview) {
    saveBookmarkPreviews({ ...getBookmarkPreviews(), [key]: preview });
  }
  const next = [key, ...readList(BOOKMARKS_KEY).filter((k) => k !== key)];
  writeList(BOOKMARKS_KEY, BOOKMARKS_CHANGED_EVENT, next, key);
}

export function removeBookmark(book: string, chapter: number, line: number) {
  const key = bookmarkKey(book, chapter, line);
  const previews = getBookmarkPreviews();
  if (key in previews) {
    delete previews[key];
    saveBookmarkPreviews(previews);
  }
  const next = readList(BOOKMARKS_KEY).filter((k) => k !== key);
  writeList(BOOKMARKS_KEY, BOOKMARKS_CHANGED_EVENT, next, key);
}
