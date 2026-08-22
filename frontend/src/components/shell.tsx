import Link from "next/link";
import { ChartLineUp, Notebook, SoccerBall, Users } from "@phosphor-icons/react/dist/ssr";
import { DesktopNav, MobileNav } from "@/components/mobile-nav";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-stone-950/10 bg-[#f7f6f0]/86 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1500px] items-center justify-between px-5 py-4 md:px-8">
        <Link href="/" className="group flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-[0.45rem] bg-stone-950 text-sm font-semibold text-[#f7f6f0] transition duration-200 group-hover:-translate-y-0.5">
            FK
          </span>
          <span>
            <span className="block text-sm font-semibold tracking-tight">FPL Kenya</span>
            <span className="block font-mono text-[10px] uppercase tracking-[0.22em] text-stone-500">
              2026/27 · live data desk
            </span>
          </span>
        </Link>
        <DesktopNav />
        <MobileNav />
      </div>
    </header>
  );
}

export function StatBlock({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="border-t border-stone-950/12 pt-4">
      <div className="mono-num text-2xl font-semibold tracking-tight text-stone-950 sm:text-3xl md:text-4xl">{value}</div>
      <div className="mt-1 text-sm font-medium text-stone-700">{label}</div>
      {detail ? <div className="mt-1 truncate text-xs text-stone-500">{detail}</div> : null}
    </div>
  );
}

export function SectionLabel({ kicker, title }: { kicker: string; title: string }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-5">
      <div>
        <div className="mono-num mb-2 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">{kicker}</div>
        <h2 className="max-w-3xl text-2xl font-semibold tracking-tight text-stone-950 md:text-5xl">{title}</h2>
      </div>
    </div>
  );
}

export const navCards = [
  { href: "/leaderboard", label: "Kenya leaderboard", icon: Users },
  { href: "/players", label: "Player watch", icon: SoccerBall },
  { href: "/stories", label: "Weekly report", icon: Notebook },
  { href: "/lab", label: "Data lab", icon: ChartLineUp },
];

export function DataStatus({ status }: { status: "live" | "provisional" | "final" }) {
  const label = status === "final" ? "Final" : status === "provisional" ? "Provisional" : "Live";
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[0.68rem] uppercase tracking-[0.18em] text-stone-600">
      <span className={`size-2 rounded-full ${status === "final" ? "bg-[#1f6b4d]" : "bg-amber-500 animate-pulse"}`} />
      {label} data
    </span>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-stone-950/10">
      <div className="mx-auto grid max-w-[1500px] gap-8 px-5 py-10 text-sm text-stone-600 md:grid-cols-[1fr_auto] md:px-8">
        <p className="max-w-xl leading-6">
          Independent FPL analysis for Kenyan managers. Not affiliated with the Premier League.
          Live figures remain subject to official review.
        </p>
        <nav aria-label="Footer navigation" className="flex flex-wrap items-start gap-x-5 gap-y-2">
          <Link href="/methodology" className="hover:text-stone-950">Methodology</Link>
          <Link href="/archive/2025-26" className="hover:text-stone-950">2025/26 archive</Link>
          <Link href="/privacy" className="hover:text-stone-950">Privacy</Link>
        </nav>
      </div>
    </footer>
  );
}
