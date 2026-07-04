// API client for the Go backend. Uses fetch with credentials so the session
// cookie flows.
//
// Base URL handling:
//   - In the browser: same-origin "/api/v1" (Next.js rewrites /api/* to the
//     Go backend — see next.config.js — so the session cookie is shared).
//   - In server components / route handlers: relative URLs don't work (no
//     host), so we use the absolute API_BASE_URL env var, defaulting to the
//     local dev backend.
const BASE =
  typeof window === "undefined"
    ? `${process.env.API_BASE_URL || "http://localhost:8080"}/api/v1`
    : "/api/v1";

export type Book = {
  slug: string;
  title: string;
  chapter_count: number;
  source_title?: string;
  pedagogy_note?: string;
  v1: boolean;
};

export type CanonicalTranslation = {
  translator: string;
  year?: number;
  license: string;
  source_url: string;
  text: string;
};

export type ReadingUnit = {
  id: string;
  order: number;
  text: string;
  pinyin?: string;
  pinyin_source?: string;
  character_count: number;
  canonical_translations: CanonicalTranslation[];
};

export type Chapter = {
  chapter: {
    id: string;
    order: number;
    title: string;
    summary: string;
    text: string;
    character_count: number;
    reading_unit_count: number;
    reading_units: ReadingUnit[];
  };
  provider: string;
  source_title: string;
  source_url: string;
};

export type Translation = {
  id: string;
  line_id: number;
  user_id: string;
  username: string;
  body: string;
  status: string;
  note?: string | null;
  created_at: string;
  published_at?: string | null;
  vote_score: number;
};

export type Comment = {
  id: string;
  line_id: number;
  user_id: string;
  username: string;
  parent_id?: string | null;
  referenced_translation_id?: string | null;
  body: string;
  created_at: string;
};

export type FeedbackResult = {
  chars_correct: string;
  grammar: string;
  key_terms?: { term: string; user_did: string; comment: string }[];
  suggested: string;
  encouragement: string;
};

export type LineBundle = {
  book: string;
  chapter: number;
  line: number;
  unit: ReadingUnit;
  translations: Translation[];
  comments: Comment[];
};

export type User = { id: string; username: string; role: string; email_verified: boolean };

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.error || res.statusText);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// --- content (anonymous) ---------------------------------------------------

export const getBooks = () => req<Book[]>("/books").then((r) => (r as any).books ?? r);
export const getChapter = (book: string, chapter: number | string) =>
  req<Chapter>(`/books/${book}/chapters/${chapter}`);
export const getLineBundle = (book: string, chapter: number, line: number) =>
  req<LineBundle>(`/lines/${book}/${chapter}/${line}`);

// --- auth ------------------------------------------------------------------

export const register = (username: string, email: string, password: string) =>
  req<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
export const login = (email: string, password: string) =>
  req<User>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
export const logout = () => req("/auth/logout", { method: "POST" });
export const getMe = () => req<User>("/me");
export const resendVerification = () =>
  req("/auth/resend-verification", { method: "POST" });

// --- UGC -------------------------------------------------------------------

export const publishTranslation = (
  book: string, chapter: number, line: number, body: string, note?: string
) =>
  req<Translation>(`/lines/${book}/${chapter}/${line}/translations`, {
    method: "POST",
    body: JSON.stringify({ body, note }),
  });

export const saveDraft = (
  book: string, chapter: number, line: number, body: string, note?: string
) =>
  req<Translation>(`/lines/${book}/${chapter}/${line}/drafts`, {
    method: "POST",
    body: JSON.stringify({ body, note }),
  });

export const createComment = (
  book: string, chapter: number, line: number,
  body: string, opts?: { parentId?: string; translationId?: string }
) =>
  req<Comment>(`/lines/${book}/${chapter}/${line}/comments`, {
    method: "POST",
    body: JSON.stringify({
      body,
      parent_id: opts?.parentId,
      translation_id: opts?.translationId,
    }),
  });

export const vote = (targetType: "translation" | "comment", targetId: string, value: 1 | -1) =>
  req("/votes", {
    method: "POST",
    body: JSON.stringify({ target_type: targetType, target_id: targetId, value }),
  });

export const removeVote = (targetType: "translation" | "comment", targetId: string) =>
  req(`/votes/${targetType}/${targetId}`, { method: "DELETE" });

export const getFeedback = (
  book: string, chapter: number, line: number, attempt: string
) =>
  req<FeedbackResult>(`/lines/${book}/${chapter}/${line}/feedback`, {
    method: "POST",
    body: JSON.stringify({ attempt }),
  });

export const markRead = (book: string, chapter: number, line: number) =>
  req(`/lines/${book}/${chapter}/${line}/read`, { method: "POST" });

// --- dashboard ---

export type BookProgress = {
  book: string;
  title: string;
  v1: boolean;
  total_lines: number;
  read: number;
  translated: number;
  voted: number;
  commented: number;
};

export type UserActivity = {
  type: "translation" | "comment" | "draft";
  book: string;
  chapter: number;
  line: number;
  snippet: string;
  at: string;
};

export type ProgressBundle = {
  progress: BookProgress[];
  activity: UserActivity[];
};

export const getMyProgress = () => req<ProgressBundle>("/me/progress");
