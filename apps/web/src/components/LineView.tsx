"use client";

import { useEffect, useState } from "react";
import {
  getLineBundle,
  vote,
  removeVote,
  publishTranslation,
  createComment,
  getFeedback,
  type ReadingUnit,
  type Translation,
  type Comment,
  type FeedbackResult,
  ApiError,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

type LineBundle = {
  unit: ReadingUnit;
  translations: Translation[];
  comments: Comment[];
};

export function LineView({
  book,
  chapter,
  unit,
}: {
  book: string;
  chapter: number;
  unit: ReadingUnit;
}) {
  const line = unit.order;
  const [bundle, setBundle] = useState<LineBundle | null>(null);
  const [open, setOpen] = useState(false);

  // Lazy-load the bundle only when the line is expanded. Keeps the chapter
  // page light (no N+1 fetches for lines the reader hasn't engaged).
  useEffect(() => {
    if (!open || bundle) return;
    getLineBundle(book, chapter, line)
      .then((b) => setBundle({ unit: b.unit, translations: b.translations, comments: b.comments }))
      .catch(() => setBundle({ unit, translations: [], comments: [] }));
  }, [open, book, chapter, line, bundle, unit]);

  return (
    <article id={`line-${line}`} className="py-5 scroll-mt-20">
      {/* The Chinese line — always visible, clickable to expand the bundle */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-left w-full group"
      >
        <p className="cjk text-stone-900 group-hover:text-stone-700">
          <span className="text-stone-300 text-xs mr-3 font-sans align-middle">
            {line}
          </span>
          {unit.text}
        </p>
        {unit.pinyin && (
          <p className="text-sm text-stone-400 italic mt-1 ml-8">{unit.pinyin}</p>
        )}
      </button>

      {open && (
        <div className="mt-3 ml-8 space-y-5">
          {!bundle ? (
            <p className="text-xs text-stone-400">Loading…</p>
          ) : (
            <>
              <CanonicalTranslations unit={bundle.unit} />
              <UserTranslations
                translations={bundle.translations}
                onVoteChange={() => refetch(book, chapter, line, setBundle, unit)}
              />
              <PositLoop book={book} chapter={chapter} line={line} />
              <Comments
                book={book}
                chapter={chapter}
                line={line}
                comments={bundle.comments}
                translations={bundle.translations}
                onAdded={() => refetch(book, chapter, line, setBundle, unit)}
              />
            </>
          )}
        </div>
      )}
    </article>
  );
}

async function refetch(
  book: string,
  chapter: number,
  line: number,
  setBundle: (b: LineBundle) => void,
  fallbackUnit: ReadingUnit,
) {
  try {
    const b = await getLineBundle(book, chapter, line);
    setBundle({ unit: b.unit, translations: b.translations, comments: b.comments });
  } catch {
    /* keep stale */
  }
}

// --- canonical (seeded) translations --------------------------------------

function CanonicalTranslations({ unit }: { unit: ReadingUnit }) {
  if (!unit.canonical_translations?.length) return null;
  return (
    <div className="space-y-2">
      {unit.canonical_translations.map((c, i) => (
        <div key={i} className="border-l-2 border-amber-300 pl-3">
          <p className="text-stone-800 leading-relaxed">{c.text}</p>
          <p className="text-xs text-stone-400 mt-1">
            <span className="inline-block px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded mr-2">
              canonical
            </span>
            {c.translator}
            {c.year ? `, ${c.year}` : ""} · {c.license}
          </p>
        </div>
      ))}
    </div>
  );
}

// --- user translations + voting -------------------------------------------

function UserTranslations({
  translations,
  onVoteChange,
}: {
  translations: Translation[];
  onVoteChange: () => void;
}) {
  const { user } = useAuth();
  const [voted, setVoted] = useState<Record<string, 1 | -1>>({});

  async function toggle(id: string, value: 1 | -1) {
    if (!user) {
      alert("Sign in to vote.");
      return;
    }
    const current = voted[id];
    try {
      if (current === value) {
        await removeVote("translation", id);
        setVoted((v) => {
          const next = { ...v };
          delete next[id];
          return next;
        });
      } else {
        await vote("translation", id, value);
        setVoted((v) => ({ ...v, [id]: value }));
      }
      onVoteChange();
    } catch (e: any) {
      alert(e.message);
    }
  }

  if (!translations.length) {
    return (
      <p className="text-xs text-stone-400 italic">
        No reader translations yet. Be the first — posit one below.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {translations.map((t) => (
        <div key={t.id} className="flex gap-3">
          <div className="flex flex-col items-center pt-1 text-xs">
            <button
              onClick={() => toggle(t.id, 1)}
              className={`vote-btn ${voted[t.id] === 1 ? "active-up" : ""}`}
              aria-label="upvote"
            >
              ▲
            </button>
            <span className="text-stone-600 font-medium">{t.vote_score}</span>
            <button
              onClick={() => toggle(t.id, -1)}
              className={`vote-btn ${voted[t.id] === -1 ? "active-down" : ""}`}
              aria-label="downvote"
            >
              ▼
            </button>
          </div>
          <div className="flex-1">
            <p className="text-stone-800 leading-relaxed">{t.body}</p>
            <p className="text-xs text-stone-400 mt-1">
              <span className="text-stone-500">@{t.username}</span>
              {t.note && <span className="ml-2 italic">“{t.note}”</span>}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

// --- the posit-feedback loop (the wedge) ----------------------------------

function PositLoop({
  book,
  chapter,
  line,
}: {
  book: string;
  chapter: number;
  line: number;
}) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [attempt, setAttempt] = useState("");
  const [feedback, setFeedback] = useState<FeedbackResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [published, setPublished] = useState(false);

  if (!user) return null;

  async function getFb() {
    setLoading(true);
    setError("");
    setFeedback(null);
    try {
      setFeedback(await getFeedback(book, chapter, line, attempt));
    } catch (e: any) {
      if (e.status === 503) {
        setError("LLM feedback isn't configured on the server yet.");
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function publish() {
    setError("");
    try {
      await publishTranslation(book, chapter, line, attempt);
      setPublished(true);
      setAttempt("");
      setFeedback(null);
      setOpen(false);
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div className="border border-stone-200 rounded p-3 bg-stone-50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-stone-500 hover:text-stone-800"
      >
        {open ? "− close" : "+ posit your own translation"}
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          <p className="text-xs text-stone-500">
            Try translating this line yourself. Get private feedback first, then
            publish if you want it to appear beside the others.
          </p>
          <textarea
            value={attempt}
            onChange={(e) => setAttempt(e.target.value)}
            placeholder="Your translation…"
            rows={2}
            className="w-full px-3 py-2 border border-stone-300 rounded text-sm bg-white"
          />
          <div className="flex gap-2">
            <button
              onClick={getFb}
              disabled={!attempt.trim() || loading}
              className="px-3 py-1.5 text-xs bg-stone-200 text-stone-700 rounded hover:bg-stone-300 disabled:opacity-50"
            >
              {loading ? "Getting feedback…" : "Get feedback"}
            </button>
            <button
              onClick={publish}
              disabled={!attempt.trim() || published}
              className="px-3 py-1.5 text-xs bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50"
            >
              {published ? "Published" : "Publish"}
            </button>
          </div>
          {error && <p className="text-rose-600 text-xs">{error}</p>}
          {feedback && <FeedbackPanel fb={feedback} />}
        </div>
      )}
    </div>
  );
}

function FeedbackPanel({ fb }: { fb: FeedbackResult }) {
  return (
    <div className="text-xs space-y-2 border-t border-stone-200 pt-3 mt-2">
      <div className="flex gap-4 text-stone-600">
        <span>
          character accuracy:{" "}
          <strong className="text-stone-900">{fb.chars_correct}</strong>
        </span>
      </div>
      <p className="text-stone-700">
        <span className="text-stone-400">grammar:</span> {fb.grammar}
      </p>
      {fb.key_terms && fb.key_terms.length > 0 && (
        <ul className="space-y-1">
          {fb.key_terms.map((t, i) => (
            <li key={i} className="text-stone-700">
              <span className="cjk text-stone-900">{t.term}</span>{" "}
              <span className="text-stone-400">(you: “{t.user_did}”)</span> — {t.comment}
            </li>
          ))}
        </ul>
      )}
      <p className="text-stone-700">
        <span className="text-stone-400">one model rendering:</span>{" "}
        <em>{fb.suggested}</em>
      </p>
      <p className="text-emerald-700">{fb.encouragement}</p>
    </div>
  );
}

// --- comments --------------------------------------------------------------

function Comments({
  book,
  chapter,
  line,
  comments,
  translations,
  onAdded,
}: {
  book: string;
  chapter: number;
  line: number;
  comments: Comment[];
  translations: Translation[];
  onAdded: () => void;
}) {
  const { user } = useAuth();
  const [body, setBody] = useState("");
  const [refTrans, setRefTrans] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    try {
      await createComment(book, chapter, line, body, {
        translationId: refTrans || undefined,
      });
      setBody("");
      setRefTrans("");
      onAdded();
    } catch (e: any) {
      alert(e.message);
    }
  }

  return (
    <div className="space-y-2 pt-2 border-t border-stone-100">
      <p className="text-xs uppercase tracking-wider text-stone-400">
        {comments.length} comment{comments.length === 1 ? "" : "s"}
      </p>
      {comments.map((c) => {
        const ref = translations.find((t) => t.id === c.referenced_translation_id);
        return (
          <div key={c.id} className="text-sm">
            <span className="text-stone-500">@{c.username}: </span>
            <span className="text-stone-800">{c.body}</span>
            {ref && (
              <span className="text-xs text-stone-400 italic ml-2">
                (on “{ref.body.slice(0, 30)}…”)
              </span>
            )}
          </div>
        );
      })}
      {user && (
        <form onSubmit={submit} className="pt-2 space-y-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Add a comment…"
            rows={2}
            className="w-full px-2 py-1.5 border border-stone-200 rounded text-sm bg-white"
          />
          {translations.length > 0 && (
            <select
              value={refTrans}
              onChange={(e) => setRefTrans(e.target.value)}
              className="text-xs border border-stone-200 rounded px-2 py-1 bg-white"
            >
              <option value="">(general comment)</option>
              {translations.map((t) => (
                <option key={t.id} value={t.id}>
                  on @{t.username}'s translation
                </option>
              ))}
            </select>
          )}
          <button
            type="submit"
            disabled={!body.trim()}
            className="text-xs px-2 py-1 bg-stone-200 text-stone-700 rounded hover:bg-stone-300 disabled:opacity-50"
          >
            Comment
          </button>
        </form>
      )}
    </div>
  );
}
