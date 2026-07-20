import type { Metadata } from "next";
import { Fraunces } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { NavBar } from "@/components/NavBar";
import { BottomNav } from "@/components/BottomNav";
import { Footer } from "@/components/Footer";
import { SITE_DESCRIPTION, SITE_NAME, siteUrl } from "@/lib/site";

// Pre-paint theme script. Runs blocking in <head> BEFORE first paint so the
// <html> class matches the user's saved preference on the very first frame —
// no flash of the wrong theme. Sets only the class; the React hook
// (lib/theme.ts) re-applies it once mounted and keeps it in sync going forward,
// so this script's job is purely "no flash".
//
// Mirrors lib/theme.ts: only "dark" enables dark mode. Missing, corrupt, and
// legacy "system" values all fall back to light.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var p = localStorage.getItem("tbl:theme");
    if (p === "dark") document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
  } catch (e) {}
})();
`;

// Fraunces is a high-contrast contemporary serif with optical sizing — at
// display sizes the strokes get more dramatic, at text sizes it stays readable.
// Used for English; CJK still renders through Source Han / Noto Serif SC (which
// stay first in the serif stack so the right font wins per glyph). Self-hosted
// at build time by next/font — no runtime Google Fonts request.
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
  axes: ["opsz", "SOFT"], // optical size + the soft axis (warmer, less rigid)
});

export const metadata: Metadata = {
  metadataBase: siteUrl(),
  title: {
    default: SITE_NAME,
    template: `%s · ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={fraunces.variable} suppressHydrationWarning>
      {/* Pre-paint theme script (see THEME_INIT_SCRIPT above). The <html> .dark
          class is intentionally NOT set here — the script sets it before paint
          based on localStorage, so there's no flash of the wrong theme.
          suppressHydrationWarning covers the class the script
          adds (React won't see it server-side). */}
      {/* min-h-dvh + flex-col keeps content anchored to the viewport top on
          short pages (empty states, error pages); main's flex-1 absorbs the
          slack and on long pages the bottom scrolls off naturally. The Footer
          sits below main on every breakpoint; on mobile it carries the bottom
          padding (pb-24) that clears the fixed BottomNav. */}
      <body className="min-h-dvh flex flex-col">
        <Script id="theme-init" strategy="beforeInteractive">
          {THEME_INIT_SCRIPT}
        </Script>
        <NavBar />
        <main className="flex-1 max-w-3xl mx-auto px-5 py-8 w-full">
          {children}
        </main>
        <Footer />
        <BottomNav />
      </body>
    </html>
  );
}
