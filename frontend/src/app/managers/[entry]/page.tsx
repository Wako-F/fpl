import Link from "next/link";
import { ArrowLeft, ChartLineUp } from "@phosphor-icons/react/dist/ssr";
import { ManagerJourneyChart } from "@/components/charts";
import { SiteHeader, StatBlock } from "@/components/shell";
import { getManager } from "@/lib/api";
import { primaryManagerName, secondaryManagerName } from "@/lib/display";

export const dynamic = "force-dynamic";

const nf = new Intl.NumberFormat("en-US");

export default async function ManagerPage({ params }: { params: Promise<{ entry: string }> }) {
  const { entry } = await params;
  const detail = await getManager(entry);

  if (!detail.manager) {
    return (
      <>
        <SiteHeader />
        <main className="mx-auto max-w-4xl px-5 py-20 md:px-8">
          <Link href="/leaderboard" className="mb-8 inline-flex items-center gap-2 text-sm font-semibold text-[#1f6b4d]">
            <ArrowLeft size={16} /> Back to leaderboard
          </Link>
          <h1 className="text-4xl font-semibold tracking-tight">Manager not found.</h1>
        </main>
      </>
    );
  }

  const bestGw = detail.history.reduce((best, row) => (row.points > best.points ? row : best), detail.history[0]);
  const worstGw = detail.history.reduce((worst, row) => (row.points < worst.points ? row : worst), detail.history[0]);

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <Link href="/leaderboard" className="mb-8 inline-flex items-center gap-2 text-sm font-semibold text-[#1f6b4d]">
          <ArrowLeft size={16} /> Back to leaderboard
        </Link>

        <section className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_25rem]">
          <div>
            <div className="mono-num mb-4 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">
              Kenya rank #{nf.format(detail.manager.rank)}
            </div>
            <h1 className="max-w-5xl text-4xl font-semibold leading-none tracking-tight sm:text-5xl md:text-7xl">
              {primaryManagerName(detail.manager)}
            </h1>
            <p className="mt-4 max-w-2xl text-lg leading-8 text-stone-600">
              Managed by {detail.manager.player_name}. {secondaryManagerName(detail.manager) === "Team name reset by FPL" ? "The public team name was reset by FPL. " : ""}
              A 38-gameweek profile of points, volatility, team value, bench points, and final rank.
            </p>
          </div>
          <div className="panel rounded-lg p-5">
            <div className="mb-5 flex items-center gap-2 text-sm font-semibold">
              <ChartLineUp size={18} className="text-[#1f6b4d]" />
              Season summary
            </div>
            <div className="grid gap-5">
              <StatBlock label="Final points" value={nf.format(detail.manager.total)} />
              <StatBlock label="Overall FPL rank" value={nf.format(detail.manager.summary_overall_rank)} />
              <StatBlock label="Average weekly points" value={String(detail.stats?.avg_points ?? "0")} />
            </div>
          </div>
        </section>

        <section className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-4">
          <StatBlock label={`Best week: GW${bestGw.event}`} value={String(bestGw.points)} />
          <StatBlock label={`Hardest week: GW${worstGw.event}`} value={String(worstGw.points)} />
          <StatBlock label="Bench points" value={nf.format(detail.stats?.bench_points ?? 0)} />
          <StatBlock label="Avg team value" value={String(detail.stats?.avg_team_value ?? "0")} />
        </section>

        {detail.metrics ? (
          <section className="mt-12 grid grid-cols-1 gap-5 lg:grid-cols-[0.38fr_0.62fr]">
            <div className="panel rounded-lg p-5">
              <div className="mono-num mb-3 text-xs uppercase tracking-[0.2em] text-[#1f6b4d]">Report card</div>
              <div className="text-2xl font-semibold tracking-tight">{detail.metrics.archetype}</div>
              <div className="mt-5 grid gap-5">
                <StatBlock label="Consistency ratio" value={String(detail.metrics.consistency_ratio)} />
                <StatBlock label="Points per million" value={String(detail.metrics.points_per_million)} />
                <StatBlock label="Transfer cost" value={nf.format(detail.metrics.transfer_cost)} />
              </div>
            </div>
            <div className="panel rounded-lg p-5">
              <div className="mb-4 text-sm font-semibold">Season twins</div>
              <div className="divide-y divide-stone-950/10">
                {detail.similar.map((row) => (
                  <Link
                    key={row.entry}
                    href={`/managers/${row.entry}`}
                    className="grid grid-cols-[4rem_1fr_auto] gap-4 py-3 text-sm transition hover:text-[#1f6b4d]"
                  >
                    <span className="mono-num text-stone-500">#{nf.format(row.rank)}</span>
                    <span>
                      <span className="block font-semibold">{primaryManagerName(row)}</span>
                      <span className="block text-xs text-stone-500">{row.archetype}</span>
                    </span>
                    <span className="mono-num font-semibold">{row.distance}</span>
                  </Link>
                ))}
              </div>
            </div>
          </section>
        ) : null}

        <section className="mt-12">
          <div className="panel rounded-lg p-5">
            <ManagerJourneyChart data={detail.history} />
          </div>
        </section>

        <section className="mt-8 panel rounded-lg">
          <div className="border-b border-stone-950/10 p-5">
            <h2 className="text-xl font-semibold tracking-tight">Weekly ledger</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-stone-950/10 text-xs uppercase tracking-[0.16em] text-stone-500">
                <tr>
                  <th className="px-5 py-3">GW</th>
                  <th className="px-5 py-3 text-right">Points</th>
                  <th className="px-5 py-3 text-right">Total</th>
                  <th className="px-5 py-3 text-right">Overall rank</th>
                  <th className="px-5 py-3 text-right">Bench</th>
                  <th className="px-5 py-3 text-right">Team value</th>
                  <th className="px-5 py-3 text-right">Hit cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-950/10">
                {detail.history.map((row) => (
                  <tr key={row.event}>
                    <td className="mono-num px-5 py-3">GW{row.event}</td>
                    <td className="mono-num px-5 py-3 text-right font-semibold">{row.points}</td>
                    <td className="mono-num px-5 py-3 text-right">{row.total_points}</td>
                    <td className="mono-num px-5 py-3 text-right">{nf.format(row.overall_rank)}</td>
                    <td className="mono-num px-5 py-3 text-right">{row.points_on_bench}</td>
                    <td className="mono-num px-5 py-3 text-right">{(row.value / 10).toFixed(1)}</td>
                    <td className="mono-num px-5 py-3 text-right">{row.event_transfers_cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </>
  );
}
