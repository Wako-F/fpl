import { NextResponse, type NextRequest } from "next/server";

const EXPENSIVE_CRAWLER_PATTERN =
  /(ahrefs|amazonbot|applebot|baiduspider|bingbot|bytespider|claudebot|crawler|datadog|dotbot|facebookexternalhit|gptbot|mj12bot|petalbot|semrush|spider|yandex)/i;

export function proxy(request: NextRequest) {
  const userAgent = request.headers.get("user-agent") ?? "";

  if (EXPENSIVE_CRAWLER_PATTERN.test(userAgent)) {
    return new NextResponse("Crawler access disabled for expensive dynamic routes.", {
      status: 403,
      headers: {
        "Cache-Control": "public, s-maxage=3600",
        "X-Robots-Tag": "noindex, nofollow",
      },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/managers/:path*", "/api/leaderboard"],
};
