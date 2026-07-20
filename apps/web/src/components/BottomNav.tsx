"use client";

// Bottom tab bar — the app's primary navigation on mobile. Two destinations:
//   Read (/)           — the books themselves (the front door)
//   Review (/dashboard) — your saved lines and words
//
// Mobile-only (md:hidden). On desktop the same destinations live in the top
// NavBar as text links — that's the conventional web layout and frees the
// bottom of the page for content. Fixed to the viewport bottom and constrained
// to the same max-w-3xl column so it stays centered on wide screens.
//
// Active state uses usePathname: Read on "/" and the reading routes beneath
// it (so a reader mid-book can see where they are), Review on "/dashboard".

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  {
    href: "/",
    label: "Read",
    icon: BookIcon,
    match: (p: string) => p === "/" || p.startsWith("/books"),
  },
  {
    href: "/dashboard",
    label: "Review",
    icon: BookmarkIcon,
    match: (p: string) => p.startsWith("/dashboard"),
  },
] as const;

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary"
      className="fixed bottom-0 inset-x-0 z-20 md:hidden border-t border-stone-200 dark:border-stone-800 bg-stone-50/95 dark:bg-stone-950/95 backdrop-blur"
    >
      <div className="max-w-3xl mx-auto grid grid-cols-2">
        {TABS.map(({ href, label, icon: Icon, match }) => {
          const active = match(pathname);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-col items-center justify-center gap-0.5 py-2 text-[11px] transition-colors ${
                active
                  ? "text-stone-900 dark:text-stone-100"
                  : "text-stone-400 hover:text-stone-700 dark:text-stone-500 dark:hover:text-stone-300"
              }`}
            >
              <Icon className="w-5 h-5" />
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

// Outlined icons — kept inline (no icon dependency) to match LineView's
// approach. 24×24 viewBox, currentColor stroke, drawn on a symmetric grid so
// they stay crisp at the rendered 20×20 and read as peers.
function BookIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {/* Open book: two pages rising from a shared spine. The verb "read" over
          the noun "library" — a single book the reader is in, not a shelf. */}
      <path d="M12 6c-1.5-1-4-1.5-6-1.5H4v12h2c2 0 4.5.5 6 1.5 1.5-1 4-1.5 6-1.5h2v-12h-2c-2 0-4.5.5-6 1.5z" />
      <path d="M12 6v13" />
    </svg>
  );
}

// Ribbon bookmark — Review holds a reader's saved lines and words, so the
// bookmark signals "your saved places" rather than a chart's "analytics".
function BookmarkIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 4h12v16l-6-4-6 4z" />
    </svg>
  );
}
