import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Review",
  description: "Review saved words and lines stored privately in this browser.",
  alternates: { canonical: "/dashboard" },
  robots: { index: false, follow: false },
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return children;
}
