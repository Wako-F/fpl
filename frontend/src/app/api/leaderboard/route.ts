import { type NextRequest, NextResponse } from "next/server";
import { apiBase } from "@/lib/api";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const q = searchParams.get("q") ?? "";
  const limit = searchParams.get("limit") ?? "100";
  const endpoint = q
    ? `${apiBase}/leaderboard/search?q=${encodeURIComponent(q)}&limit=${limit}`
    : `${apiBase}/leaderboard?limit=${limit}`;
  const response = await fetch(endpoint, { cache: "no-store" });
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
