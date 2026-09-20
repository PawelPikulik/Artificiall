import { NextRequest, NextResponse } from "next/server";
import { askLLM } from "@/lib/llm";

export async function POST(req: NextRequest) {
  try {
    const { prompt, context } = await req.json();
    const start = Date.now();
    const result = await askLLM(`${prompt}\n\nContext: ${context}`);
    const durationMs = Date.now() - start;
    return NextResponse.json({ result, durationMs });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
