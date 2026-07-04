"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useState } from "react";

export function NavBar() {
  const { user, loading, login, register, logout } = useAuth();
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b border-stone-200 bg-stone-50/80 backdrop-blur sticky top-0 z-10">
      <nav className="max-w-3xl mx-auto px-5 h-14 flex items-center justify-between">
        <Link href="/" className="font-serif text-lg text-stone-800">
          大學 <span className="text-stone-400 text-sm font-sans">The Big Learn</span>
        </Link>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/" className="text-stone-600 hover:text-stone-900">
            Library
          </Link>
          {loading ? null : user ? (
            <>
              <span className="text-stone-500">{user.username}</span>
              <button
                onClick={() => logout()}
                className="text-stone-500 hover:text-stone-900"
              >
                Sign out
              </button>
            </>
          ) : (
            <button
              onClick={() => setOpen((v) => !v)}
              className="text-stone-600 hover:text-stone-900"
            >
              Sign in
            </button>
          )}
        </div>
      </nav>
      {open && !user && (
        <AuthSheet
          onLogin={login}
          onRegister={register}
          onClose={() => setOpen(false)}
        />
      )}
    </header>
  );
}

function AuthSheet({
  onLogin,
  onRegister,
  onClose,
}: {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (username: string, email: string, password: string) => Promise<void>;
  onClose: () => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "login") await onLogin(email, password);
      else await onRegister(username, email, password);
      onClose();
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    }
  }

  return (
    <div className="border-t border-stone-200 bg-white px-5 py-4">
      <form onSubmit={submit} className="max-w-sm mx-auto space-y-3">
        <div className="flex gap-2 text-sm">
          <button
            type="button"
            onClick={() => setMode("login")}
            className={`flex-1 py-1.5 rounded ${mode === "login" ? "bg-stone-800 text-white" : "text-stone-500"}`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => setMode("register")}
            className={`flex-1 py-1.5 rounded ${mode === "register" ? "bg-stone-800 text-white" : "text-stone-500"}`}
          >
            Create account
          </button>
        </div>
        {mode === "register" && (
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
            className="w-full px-3 py-2 border border-stone-300 rounded text-sm"
          />
        )}
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
          required
          className="w-full px-3 py-2 border border-stone-300 rounded text-sm"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password (min 8 chars)"
          required
          className="w-full px-3 py-2 border border-stone-300 rounded text-sm"
        />
        {error && <p className="text-rose-600 text-xs">{error}</p>}
        <button
          type="submit"
          className="w-full py-2 bg-stone-800 text-white rounded text-sm hover:bg-stone-700"
        >
          {mode === "login" ? "Sign in" : "Create account"}
        </button>
        <p className="text-xs text-stone-400">
          Required to submit translations, vote, or comment. Reading is anonymous.
        </p>
      </form>
    </div>
  );
}
