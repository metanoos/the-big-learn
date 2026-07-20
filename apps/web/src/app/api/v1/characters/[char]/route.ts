// GET /api/v1/characters/[char] — character popover breakdown.
//
// Replaces the Go service's handleCharacter. Serves the client-side popover
// (CharBreakdown.tsx) which fetches on click. Returns 404 for chars not in
// the index, matching the Go contract the client already expects.

import { NextRequest, NextResponse } from "next/server";
import { getCharacter, ApiError } from "@/lib/content";

export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ char: string }> }
) {
  const { char } = await params;
  try {
    const details = await getCharacter(decodeURIComponent(char));
    return NextResponse.json(details);
  } catch (err) {
    if (err instanceof ApiError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    return NextResponse.json(
      { error: "failed to load character" },
      { status: 500 }
    );
  }
}
