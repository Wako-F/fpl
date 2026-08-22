import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "https://fplke.vercel.app";
  return ["", "/leaderboard", "/players", "/stories", "/lab", "/methodology", "/archive/2025-26", "/privacy"].map((path) => ({ url: `${base}${path}`, lastModified: new Date(), changeFrequency: path === "/archive/2025-26" ? "yearly" : "daily", priority: path === "" ? 1 : 0.7 }));
}
