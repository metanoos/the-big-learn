"use client";

// Top bar. On mobile it's brand only (the BottomNav holds primary nav). On
// desktop (md+) the two primary destinations surface here as text links, and
// BottomNav hides — desktop users get conventional left-to-right top-nav
// instead of a mobile tab bar pinned to the viewport.
//
// Active state mirrors BottomNav's matchers so the two stay in sync: Read
// on "/" + reading routes beneath it, Review on "/dashboard". There is no
// separate landing page — the library is the front door.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";

const NAV_LINKS = [
  {
    href: "/",
    label: "Read",
    match: (p: string) => p === "/" || p.startsWith("/books"),
  },
  {
    href: "/dashboard",
    label: "Review",
    match: (p: string) => p.startsWith("/dashboard"),
  },
] as const;

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-stone-200 dark:border-stone-800 bg-stone-50/80 dark:bg-stone-950/80 backdrop-blur sticky top-0 z-10">
      <nav className="max-w-3xl mx-auto px-5 h-14 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5">
            <SealMark className="h-10 w-10 shrink-0" />
            <span className="font-serif text-lg font-bold text-stone-800 dark:text-stone-200">
              The Big Learn
            </span>
          </Link>
          {/* Desktop primary nav — hidden on mobile, where BottomNav holds
              these same destinations. Active link goes solid; the trailing
              routes (e.g. /books/...) keep Library lit while reading. */}
          <div className="hidden md:flex items-center gap-5 text-sm">
            {NAV_LINKS.map(({ href, label, match }) => {
              const active = match(pathname);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={
                    active
                      ? "text-stone-900 dark:text-stone-100"
                      : "text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-200"
                  }
                >
                  {label}
                </Link>
              );
            })}
          </div>
        </div>
        {/* Theme toggle sits on the right, visible on all breakpoints (mobile
            has no other chrome in the top bar, so this is the right home).
            Same icon-button family as ToneColorToggle. */}
        <ThemeToggle />
      </nav>
    </header>
  );
}

// SealMark — the wordmark glyph, styled as a small 印章 (seal): 大 stacked over
// 学 inside a rounded square, amber fill with white glyphs. Evokes the
// classical mark of authorship/identity, which fits a site named for 大学. The
// amber is the Confucian tradition color (see tailwind.config.ts) — 大学 is the
// founding Confucian text, so the seal lands as more than decoration.
//
// SVG (not an <img>) so it stays crisp at any DPR and inherits sizing via
// className. Glyphs are <text> in the serif stack so they render with the same
// Source Han / Noto Serif SC faces as body CJK. Rounded corners (3px in the
// 32×32 box) read as "app icon" rather than literal ink seal, softening the
// mark so it sits calmly in a chrome-free bar.
function SealMark({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      aria-label="大学"
      role="img"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="32" height="32" rx="3" fill="#b45309" />
      <text
        x="16"
        y="8"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize="15"
        fontWeight="700"
        fill="#ffffff"
        style={{ fontFamily: '"Source Han Serif", "Noto Serif SC", "Songti SC", serif' }}
      >
        大
      </text>
      <text
        x="16"
        y="22"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize="15"
        fontWeight="700"
        fill="#ffffff"
        style={{ fontFamily: '"Source Han Serif", "Noto Serif SC", "Songti SC", serif' }}
      >
        学
      </text>
    </svg>
  );
}
