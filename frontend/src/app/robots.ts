import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/leaderboard", "/methodology", "/stories", "/lab", "/clubs", "/archetypes"],
        disallow: ["/managers/", "/api/"],
      },
    ],
  };
}
