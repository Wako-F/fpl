import Link from "next/link";
import { ChartLineUp, Rows, Waveform } from "@phosphor-icons/react/dist/ssr";
import { MobileNav } from "@/components/mobile-nav";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-stone-950/10 bg-[#f7f6f0]/86 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1500px] items-center justify-between px-5 py-4 md:px-8">
        <Link href="/" className="group flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-md bg-stone-950 text-sm font-semibold text-[#f7f6f0]">
            FK
          </span>
          <span>
            <span className="block text-sm font-semibold tracking-tight">FPL Kenya</span>
            <span className="block font-mono text-[10px] uppercase tracking-[0.22em] text-stone-500">
              2025-26 season data
            </span>
          </span>
        </Link>
        <nav className="hidden items-center gap-1 text-sm text-stone-600 md:flex">
          <Link className="rounded-md px-3 py-2 transition hover:bg-stone-950/5 hover:text-stone-950" href="/">
            Overview
          </Link>
          <Link className="rounded-md px-3 py-2 transition hover:bg-stone-950/5 hover:text-stone-950" href="/leaderboard">
            Leaderboard
          </Link>
          <Link className="rounded-md px-3 py-2 transition hover:bg-stone-950/5 hover:text-stone-950" href="/lab">
            Lab
          </Link>
          <Link className="rounded-md px-3 py-2 transition hover:bg-stone-950/5 hover:text-stone-950" href="/stories">
            Stories
          </Link>
          <Link className="rounded-md px-3 py-2 transition hover:bg-stone-950/5 hover:text-stone-950" href="/methodology">
            Methodology
          </Link>
        </nav>
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
  { href: "/leaderboard", label: "Leaderboard", icon: Rows },
  { href: "/lab", label: "Data lab", icon: ChartLineUp },
  { href: "/methodology", label: "Data methodology", icon: Waveform },
];
