// Portable backup/restore for the browser-only reader state. The app has no
// accounts or database, so an explicit JSON export is the only way to move
// progress between browsers or protect it before clearing site data.

const STORAGE_KEYS = [
  "tbl:read",
  "tbl:bookmarks",
  "tbl:bookmark-details",
  "tbl:review-chars",
  "tbl:tone-colors",
  "tbl:pinyin",
  "tbl:english",
  "tbl:theme",
] as const;

type StorageKey = (typeof STORAGE_KEYS)[number];

export type ReaderDataExport = {
  app: "the-big-learn";
  version: 1;
  exported_at: string;
  data: Partial<Record<StorageKey, unknown>>;
};

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function validValue(key: StorageKey, value: unknown): boolean {
  switch (key) {
    case "tbl:read":
    case "tbl:bookmarks":
      return isStringArray(value);
    case "tbl:bookmark-details":
      return isRecord(value) && Object.values(value).every((preview) => {
        if (!isRecord(preview) || typeof preview.text !== "string") return false;
        return preview.translation === undefined || typeof preview.translation === "string";
      });
    case "tbl:review-chars":
      return Array.isArray(value) && value.every((entry) =>
        typeof entry === "string" || (isRecord(entry) && typeof entry.text === "string"),
      );
    case "tbl:tone-colors":
    case "tbl:pinyin":
    case "tbl:english":
      return value === true || value === false;
    case "tbl:theme":
      return value === "light" || value === "dark";
  }
}

export function exportReaderData(): ReaderDataExport {
  const data: ReaderDataExport["data"] = {};
  for (const key of STORAGE_KEYS) {
    const raw = window.localStorage.getItem(key);
    if (raw === null) continue;
    try {
      data[key] = key === "tbl:theme" ? raw : JSON.parse(raw);
    } catch {
      // A corrupt key is omitted from a healthy backup instead of poisoning
      // the whole export.
    }
  }
  return {
    app: "the-big-learn",
    version: 1,
    exported_at: new Date().toISOString(),
    data,
  };
}

export function importReaderData(value: unknown): number {
  if (!isRecord(value) || value.app !== "the-big-learn" || value.version !== 1) {
    throw new Error("This is not a The Big Learn reader-data backup.");
  }
  if (!isRecord(value.data)) throw new Error("The backup has no readable data.");

  let imported = 0;
  for (const key of STORAGE_KEYS) {
    if (!(key in value.data)) continue;
    const item = value.data[key];
    if (!validValue(key, item)) {
      throw new Error(`The backup contains invalid data for ${key}.`);
    }
    window.localStorage.setItem(
      key,
      key === "tbl:theme" ? String(item) : JSON.stringify(item),
    );
    imported++;
  }
  if (imported === 0) throw new Error("The backup does not contain reader data.");
  return imported;
}
