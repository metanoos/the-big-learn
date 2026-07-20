// GET /api/v1/books/[book]/chapters/[chapter] — one chapter payload.
//
// Replaces the Go service's handleChapter. The dashboard client component uses
// it to backfill bookmark previews. Server components import getChapter from
// @/lib/content directly.

import { NextRequest, NextResponse } from "next/server";
import { getChapter, ApiError } from "@/lib/content";

export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  {
    params,
  }: {
    params: Promise<{ book: string; chapter: string }>;
  }
) {
  const { book, chapter } = await params;
  try {
    const ch = await getChapter(book, chapter);
    return NextResponse.json(ch);
  } catch (err) {
    if (err instanceof ApiError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    return NextResponse.json(
      { error: "failed to load chapter" },
      { status: 500 }
    );
  }
}
