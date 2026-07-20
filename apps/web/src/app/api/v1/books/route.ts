// GET /api/v1/books — list every cataloged book.
//
// Replaces the Go service's handleBooks. The dashboard client component fetches
// from here on mount. Server components import getBooks from @/lib/content
// directly (no fetch), so this route is browser-only.

import { NextResponse } from "next/server";
import { getBooks } from "@/lib/content";

export const dynamic = "force-dynamic";

export async function GET() {
  const books = await getBooks();
  return NextResponse.json({ books });
}
