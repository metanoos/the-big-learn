// POST /api/v1/characters/batch — batch pinyin lookup.
//
// Replaces the Go service's handleCharacterBatch. Body: {"chars": ["大","学",...]}.
// Response: {"大":{"pinyin":"dà","has_entry":true}, ...}. Used by the reader
// to render pinyin above text and by ReviewChars on the dashboard.
//
// Mirrors the Go input-validation contract: reject unknown fields, cap at
// 2000 chars, 128 KiB body. The function layer enforces the 2000-char cap;
// we enforce the rest here.

import { NextRequest, NextResponse } from "next/server";
import { getCharPinyinBatch, ApiError } from "@/lib/content";

export const dynamic = "force-dynamic";

const MAX_BODY_BYTES = 128 * 1024;
const MAX_CHARS = 2000;

export async function POST(req: NextRequest) {
  let payload: unknown;
  try {
    // Read the body with a size cap, matching http.MaxBytesReader in the Go server.
    const text = await readLimited(req, MAX_BODY_BYTES);
    payload = JSON.parse(text);
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  if (!payload || typeof payload !== "object") {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  const obj = payload as Record<string, unknown>;
  // DisallowUnknownFields parity: anything other than {chars: [...]} is rejected.
  const keys = Object.keys(obj);
  if (keys.length !== 1 || keys[0] !== "chars") {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  const chars = obj.chars;
  if (!Array.isArray(chars)) {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  if (chars.length > MAX_CHARS) {
    return NextResponse.json(
      { error: `too many chars (max ${MAX_CHARS})` },
      { status: 400 }
    );
  }
  try {
    const map = await getCharPinyinBatch(chars as string[]);
    // Map → plain object for JSON. The Go server keys by the single rune.
    const out: Record<string, { pinyin: string | null; has_entry: boolean }> =
      {};
    for (const [k, v] of map) out[k] = v;
    return NextResponse.json(out);
  } catch (err) {
    if (err instanceof ApiError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    return NextResponse.json(
      { error: "failed to load pinyin" },
      { status: 500 }
    );
  }
}

async function readLimited(req: NextRequest, max: number): Promise<string> {
  const reader = req.body?.getReader();
  if (!reader) return "";
  const decoder = new TextDecoder();
  let received = 0;
  let out = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    received += value?.byteLength ?? 0;
    if (received > max) {
      throw new Error("body too large");
    }
    out += decoder.decode(value, { stream: true });
  }
  out += decoder.decode();
  return out;
}
