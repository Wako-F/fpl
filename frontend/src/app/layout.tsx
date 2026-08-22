import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://fplke.vercel.app"),
  title: { default: "FPL Kenya — the Kenyan FPL data desk", template: "%s | FPL Kenya" },
  description: "Live 2026/27 Fantasy Premier League standings, player analysis, weekly stories, and open methodology for Kenyan managers.",
  openGraph: {
    title: "FPL Kenya — the Kenyan FPL data desk",
    description: "The 2026/27 FPL season through a Kenyan lens.",
    type: "website",
    locale: "en_KE",
  },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[#f7f6f0] text-stone-950">
        <a href="#main-content" className="skip-link">Skip to content</a>
        {children}
      </body>
    </html>
  );
}
