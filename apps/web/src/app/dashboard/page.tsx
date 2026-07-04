"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMyProgress, type ProgressBundle } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { displayName } from "@/lib/titles";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [data, setData] = useState<ProgressBundle | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!user) return;
    getMyProgress()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, [user]);

  if (loading) return <p className="text-stone-500 text-sm">Loading…</p>;

  if (!user) {
    return (
      <div className="space-y-2">
        <h1 className="font-serif text-2xl text-stone-900">Your dashboard</h1>
        <p className="text-stone-600 text-sm">
          Sign in to track what you've read, translated, and commented on.
        </p>
        <Link href="/" className="text-sm text-stone-500 underline">
          ← Back to library
        </Link>
      </div>
    );
  }

  if (err) return <p className="text-rose-600 text-sm">{err}</p>;
  if (!data) return <p className="text-stone-500 text-sm">Loading…</p>;

  const v1 = data.progress.filter((p) => p.v1);
  const rest = data.progress.filter((p) => !p.v1);
  const totalRead = data.progress.reduce((s, p) => s + p.read, 0);
  const totalTranslated = data.progress.reduce((s, p) => s + p.translated, 0);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="font-serif text-2xl text-stone-900">
          @{user.username}'s dashboard
        </h1>
        <p className="text-sm text-stone-500 mt-1">
          {totalRead} lines read · {totalTranslated} translations published
          {!user.email_verified && (
            <span className="text-amber-700 ml-2">
              · verify your email to publish
            </span>
          )}
        </p>
      </div>

      <section>
        <h2 className="text-xs uppercase tracking-wider text-stone-400 mb-3">
          Progress by book
        </h2>
        <div className="space-y-3">
          {v1.map((p) => (
            <ProgressRow key={p.book} p={p} />
          ))}
        </div>
        {rest.length > 0 && (
          <details className="mt-4">
            <summary className="text-xs text-stone-400 cursor-pointer">
              {rest.length} more (deferred texts)
            </summary>
            <div className="space-y-3 mt-3 opacity-70">
              {rest.map((p) => (
                <ProgressRow key={p.book} p={p} />
              ))}
            </div>
          </details>
        )}
      </section>

      <section>
        <h2 className="text-xs uppercase tracking-wider text-stone-400 mb-3">
          Recent activity
        </h2>
        {data.activity.length === 0 ? (
          <p className="text-sm text-stone-500 italic">
            Nothing yet. Open a chapter and start reading — or posit your first
            translation.
          </p>
        ) : (
          <ul className="space-y-2">
            {data.activity.map((a, i) => (
              <li key={i} className="text-sm">
                <Link
                  href={`/books/${a.book}/${a.chapter}#line-${a.line}`}
                  className="text-stone-600 hover:text-stone-900"
                >
                  <span className="text-xs uppercase text-stone-400 mr-2">
                    {a.type}
                  </span>
                  {a.snippet}
                  <span className="text-xs text-stone-400 ml-2">
                    {displayName(a.book)} {a.chapter}:{a.line}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function ProgressRow({ p }: { p: import("@/lib/api").BookProgress }) {
  const pct = p.total_lines > 0 ? Math.round((p.read / p.total_lines) * 100) : 0;
  return (
    <Link
      href={`/books/${p.book}`}
      className="block px-4 py-3 bg-white border border-stone-200 rounded hover:border-stone-400"
    >
      <div className="flex items-baseline justify-between mb-1">
        <span className="font-serif text-stone-900">
          {p.title || displayName(p.book)}
        </span>
        <span className="text-xs text-stone-400">
          {p.read}/{p.total_lines} read ({pct}%)
        </span>
      </div>
      <div className="h-1.5 bg-stone-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-500 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      {(p.translated > 0 || p.commented > 0 || p.voted > 0) && (
        <div className="flex gap-4 mt-2 text-xs text-stone-500">
          {p.translated > 0 && <span>✎ {p.translated} translated</span>}
          {p.commented > 0 && <span>💬 {p.commented} commented</span>}
          {p.voted > 0 && <span>▲ {p.voted} voted</span>}
        </div>
      )}
    </Link>
  );
}
