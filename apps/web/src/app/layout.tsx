import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { NavBar } from "@/components/NavBar";

export const metadata: Metadata = {
  title: "The Big Learn",
  description:
    "Read classical Chinese line by line. Compare translations, submit your own, and get feedback.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <NavBar />
          <main className="max-w-3xl mx-auto px-5 py-8">{children}</main>
          <footer className="max-w-3xl mx-auto px-5 py-12 text-xs text-stone-400">
            The Big Learn · canonical translations are public-domain (Legge) ·
            user translations © their authors
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
