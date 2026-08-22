import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";
import { SiteFooter, SiteHeader, StatBlock } from "@/components/shell";
import { getLeaderboard, getOverview } from "@/lib/api";
import { primaryManagerName, secondaryManagerName } from "@/lib/display";

export const metadata: Metadata = { title: "2025/26 archive", description: "The completed 2025/26 FPL Kenya season archive." };
export const revalidate = 86_400;
const nf = new Intl.NumberFormat("en-KE");

export default async function ArchivePage() {
  const [overview, leaders] = await Promise.all([getOverview(), getLeaderboard(10)]);
  return (
    <>
      <SiteHeader />
      <main id="main-content" className="mx-auto max-w-[1500px] px-5 py-12 md:px-8 md:py-20">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-semibold text-[#1f6b4d]"><ArrowLeft size={16} /> Back to 2026/27</Link>
        <div className="mt-10 font-mono text-xs uppercase tracking-[0.22em] text-stone-500">Completed season · archive</div>
        <h1 className="mt-5 max-w-6xl text-balance text-5xl font-semibold leading-[0.93] tracking-[-0.05em] sm:text-6xl md:text-8xl">The 2025/26 Kenya season.</h1>
        <p className="mt-7 max-w-[65ch] text-lg leading-8 text-stone-600">A frozen reference point for the season-aware platform. These figures do not mix with current 2026/27 standings.</p>

        <section className="mt-14 grid grid-cols-2 gap-x-6 gap-y-8 lg:grid-cols-4">
          <StatBlock label="Kenyan managers" value={nf.format(overview.summary.managers)} />
          <StatBlock label="Champion score" value={nf.format(overview.summary.max_points)} />
          <StatBlock label="Median score" value={nf.format(Number(overview.summary.median_points))} />
          <StatBlock label="Gameweeks" value={String(overview.gameweeks.length)} />
        </section>

        <section className="mt-16 grid gap-8 md:grid-cols-[0.38fr_0.62fr]">
          <div><div className="font-mono text-xs uppercase tracking-[0.2em] text-[#1f6b4d]">Final table</div><h2 className="mt-3 text-4xl font-semibold tracking-[-0.04em]">Top ten in Kenya.</h2></div>
          <ol className="divide-y divide-stone-950/10 border-y border-stone-950/10">
            {leaders.map((row) => <li key={row.entry} className="grid grid-cols-[3rem_1fr_auto] gap-4 py-4"><span className="font-mono text-stone-500">#{row.rank}</span><span><span className="block font-semibold">{primaryManagerName(row)}</span><span className="block text-xs text-stone-500">{secondaryManagerName(row)}</span></span><span className="font-mono font-semibold">{nf.format(row.total)}</span></li>)}
          </ol>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
