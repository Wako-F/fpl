import Link from "next/link";
import { ArrowLeft, ChartLineUp } from "@phosphor-icons/react/dist/ssr";
import { notFound } from "next/navigation";
import { ManagerJourneyChart } from "@/components/charts";
import { SiteFooter, SiteHeader, StatBlock } from "@/components/shell";
import { getLiveManager, type LiveManagerDetail } from "@/lib/api";
import { primaryManagerName, secondaryManagerName } from "@/lib/display";

export const revalidate = 120;
export const dynamicParams = true;

export function generateStaticParams() {
  return [];
}

const nf = new Intl.NumberFormat("en-KE");

export default async function ManagerPage({ params }: { params: Promise<{ entry: string }> }) {
  const { entry } = await params;
  if (!/^\d{1,10}$/.test(entry)) notFound();

  let detail: LiveManagerDetail;
  try {
    detail = await getLiveManager(entry);
  } catch {
    notFound();
  }
  const metrics = detail.metrics;
  const bestGw = detail.history.length
    ? detail.history.reduce((best, row) => (row.points > best.points ? row : best))
    : null;
  const worstGw = detail.history.length
    ? detail.history.reduce((worst, row) => (row.points < worst.points ? row : worst))
    : null;

  return (
    <>
      <SiteHeader />
      <main id="main-content" className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <Link href="/leaderboard" className="mb-10 inline-flex items-center gap-2 text-sm font-semibold text-[#1f6b4d] transition hover:gap-3">
          <ArrowLeft size={16} /> Back to leaderboard
        </Link>

        <section className="grid gap-10 lg:grid-cols-[1fr_24rem]">
          <div>
            <div className="font-mono text-xs uppercase tracking-[0.22em] text-[#1f6b4d]">2026/27 · Kenya rank #{nf.format(detail.manager.rank)}</div>
            <h1 className="mt-5 max-w-5xl text-balance text-5xl font-semibold leading-[0.92] tracking-[-0.05em] sm:text-6xl md:text-8xl">
              {primaryManagerName(detail.manager)}
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-stone-600">
              Managed by {detail.manager.player_name}. This profile updates through the latest collected gameweek and remains provisional until FPL locks the event.
            </p>
          </div>
          <aside className="bg-stone-950 p-6 text-[#fffdf7] md:rounded-[0.75rem]">
            <div className="mb-6 flex items-center gap-2 text-sm font-semibold text-[#d3ad68]"><ChartLineUp size={19} /> Current position</div>
            <div className="grid gap-6">
              <div><div className="font-mono text-4xl font-semibold">{nf.format(detail.manager.total)}</div><div className="mt-1 text-xs text-stone-400">FPL points</div></div>
              <div><div className="font-mono text-4xl font-semibold">#{nf.format(detail.manager.rank)}</div><div className="mt-1 text-xs text-stone-400">Kenya rank</div></div>
              <div><div className="font-mono text-4xl font-semibold">{detail.manager.summary_overall_rank ? `#${nf.format(detail.manager.summary_overall_rank)}` : "—"}</div><div className="mt-1 text-xs text-stone-400">Overall rank</div></div>
            </div>
          </aside>
        </section>

        <section className="mt-14 grid grid-cols-2 gap-x-6 gap-y-8 lg:grid-cols-4">
          <StatBlock label={bestGw ? `Best week · GW${bestGw.event}` : "Best week"} value={bestGw ? String(bestGw.points) : "—"} />
          <StatBlock label={worstGw ? `Hardest week · GW${worstGw.event}` : "Hardest week"} value={worstGw ? String(worstGw.points) : "—"} />
          <StatBlock label="Bench points" value={nf.format(metrics?.bench_points ?? 0)} />
          <StatBlock label="Average team value" value={metrics?.avg_team_value ? `£${metrics.avg_team_value}m` : "—"} />
        </section>

        {detail.history.length ? (
          <section className="mt-14 panel rounded-[0.75rem] p-5 md:p-7">
            <ManagerJourneyChart data={detail.history} />
          </section>
        ) : (
          <section className="mt-14 panel rounded-[0.75rem] p-8 text-sm text-stone-600">The manager history is queued for the next deep-cohort refresh.</section>
        )}

        <section className="mt-8 panel overflow-hidden rounded-[0.75rem]">
          <div className="border-b border-stone-950/10 p-5">
            <h2 className="text-xl font-semibold tracking-tight">Weekly ledger</h2>
            <p className="mt-1 text-xs text-stone-500">{secondaryManagerName(detail.manager)} · {metrics?.gameweeks ?? 0} collected gameweeks</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-stone-950/10 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-stone-500">
                <tr>
                  <th className="px-5 py-3">GW</th><th className="px-5 py-3 text-right">Points</th>
                  <th className="px-5 py-3 text-right">Total</th><th className="px-5 py-3 text-right">Overall rank</th>
                  <th className="px-5 py-3 text-right">Bench</th><th className="px-5 py-3 text-right">Team value</th>
                  <th className="px-5 py-3 text-right">Hit cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-950/10">
                {detail.history.map((row) => (
                  <tr key={row.event} className="transition hover:bg-white">
                    <td className="px-5 py-3 font-mono">GW{row.event}</td><td className="px-5 py-3 text-right font-mono font-semibold">{row.points}</td>
                    <td className="px-5 py-3 text-right font-mono">{row.total_points}</td><td className="px-5 py-3 text-right font-mono">{nf.format(row.overall_rank)}</td>
                    <td className="px-5 py-3 text-right font-mono">{row.points_on_bench}</td><td className="px-5 py-3 text-right font-mono">£{(row.value / 10).toFixed(1)}m</td>
                    <td className="px-5 py-3 text-right font-mono">{row.event_transfers_cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
