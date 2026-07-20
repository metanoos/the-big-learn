"use client";

// Quiet contact footer, bottom of every page. Replaces the old "Support the
// library" patronage link — the reading experience is free and ad-free, and
// this is the one place a reader can find a human: questions, corrections,
// pointing at a bad translation. The lead-in names those uses on purpose, so
// the mail that arrives is the mail that's worth reading.
//
// Anti-harvesting: the address is shipped as two halves (user / host, from
// lib/site.ts) and assembled into a real mailto: only after mount. The
// server-rendered HTML contains no contiguous address string, so cheap regex
// scrapers miss it. Pre-hydration and no-JS visitors see the human-readable
// "user [at] host [dot] tld" form — not clickable, but legible.
//
// Visible on all breakpoints (the old Support footer was desktop-only because
// the mobile BottomNav occupied the viewport bottom; this one sits *below*
// main content, so it belongs on mobile too). The fixed BottomNav still
// overlays the viewport bottom on mobile — the layout clears it with bottom
// padding on this footer rather than on <main>, since this is now the
// bottom-most content element.

import { useEffect, useState } from "react";
import { CONTACT_EMAIL_HOST, CONTACT_EMAIL_USER } from "@/lib/site";

export function Footer() {
  // null until mount: server and first client paint render the obfuscated
  // [at]/[dot] text (no mailto, no full address). After mount we swap in the
  // real link. The brief flash of the muted text is intentional and harmless —
  // it's the same information, just not yet clickable.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const address = `${CONTACT_EMAIL_USER}@${CONTACT_EMAIL_HOST}`;

  return (
    <footer className="max-w-3xl mx-auto px-5 py-6 border-t border-stone-200 dark:border-stone-800 mt-8 pb-24 md:pb-6">
      <div className="text-xs text-stone-500 dark:text-stone-400 leading-relaxed">
        Questions, corrections, or a translation worth fixing?{" "}
        {mounted ? (
          <a
            href={`mailto:${address}`}
            className="underline underline-offset-4 hover:text-stone-800 dark:hover:text-stone-200"
          >
            {address}
          </a>
        ) : (
          <span className="text-stone-400 dark:text-stone-500">
            {CONTACT_EMAIL_USER} [at] {CONTACT_EMAIL_HOST.replace(".", " [dot] ")}
          </span>
        )}
      </div>
    </footer>
  );
}
