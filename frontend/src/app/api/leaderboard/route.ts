import { type NextRequest, NextResponse } from "next/server";
import { LIVE_REVALIDATE_SECONDS, apiBase } from "@/lib/api";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const q = searchParams.get("q") ?? "";
  const limit = searchParams.get("limit") ?? "100";
  const params = new URLSearchParams({ limit });
  if (q) params.set("q", q);
  const response = await fetch(`${apiBase}/v2/leaderboard?${params}`, {
    next: { revalidate: LIVE_REVALIDATE_SECONDS },
  });
  const payload = await response.json();
  return NextResponse.json(payload.rows ?? [], {
    status: response.status,
    headers: {
      "Cache-Control": `public, s-maxage=${LIVE_REVALIDATE_SECONDS}, stale-while-revalidate=300`,
    },
  });
}
