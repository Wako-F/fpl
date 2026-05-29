import Link from "next/link";
import { ConsistencyScatter, ValueRankScatter } from "@/components/charts";
import { CompactManagerTable } from "@/components/insight-tables";
import { AnimatedRankRace } from "@/components/rank-race";
import { SectionLabel, SiteHeader, StatBlock } from "@/components/shell";
import { getLab } from "@/lib/api";
import { managerIdentity, primaryManagerName } from "@/lib/display";

export const dynamic = "force-dynamic";

const nf = new Intl.NumberFormat("en-US");

export default async function LabPage() {
  const lab = await getLab();
  const topExplosion = lab.explosions[0];
  const topBench = lab.benchPain[0];

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <div className="mb-10 max-w-5xl">
          <div className="mono-num mb-3 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">
            Scatterplots, rank race, outliers
          </div>
          <h1 className="text-4xl font-semibold leading-none tracking-tight sm:text-5xl md:text-7xl">
            Experimental views of the Kenya FPL dataset.
          </h1>
        </div>

        <section className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <StatBlock label="Bench pain leader" value={nf.format(Number(topBench?.bench_points ?? 0))} detail={managerIdentity(topBench)} />
          <StatBlock label="Biggest one-week score" value={String(topExplosion?.points ?? 0)} detail={`GW${topExplosion?.event ?? "-"}`} />
          <StatBlock label="Race field" value="Top 50" detail="final Kenya leaderboard" />
        </section>

        <section className="mt-16">
          <SectionLabel kicker="Rank Race" title="The top 50 did not arrive in a straight line." />
          <div className="panel rounded-lg p-5">
            <AnimatedRankRace data={lab.race} />
          </div>
        </section>

        <section className="mt-16 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div>
            <SectionLabel kicker="Consistency" title="Average points versus volatility." />
            <div className="panel rounded-lg p-5">
              <ConsistencyScatter data={lab.scatter} />
            </div>
          </div>
          <div>
            <SectionLabel kicker="Value" title="Team value versus final rank." />
            <div className="panel rounded-lg p-5">
              <ValueRankScatter data={lab.scatter} />
            </div>
          </div>
        </section>

        <section className="mt-16 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <CompactManagerTable title="Bench Pain Hall of Fame" rows={lab.benchPain} metricLabel="bench" metricKey="bench_points" />
          <CompactManagerTable title="Biggest GW Explosions" rows={lab.explosions} metricLabel="points" metricKey="points" />
        </section>

        <section className="mt-16 panel rounded-lg">
          <div className="border-b border-stone-950/10 p-5">
            <h2 className="text-xl font-semibold tracking-tight">Top 100 weekly explosions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="border-b border-stone-950/10 text-xs uppercase tracking-[0.16em] text-stone-500">
                <tr>
                  <th className="px-5 py-3">GW</th>
                  <th className="px-5 py-3">Team</th>
                  <th className="px-5 py-3">Manager</th>
                  <th className="px-5 py-3 text-right">Points</th>
                  <th className="px-5 py-3 text-right">Final rank</th>
                  <th className="px-5 py-3 text-right">Bench</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-950/10">
                {lab.explosions.map((row) => (
                  <tr key={`${row.event}-${row.entry}`}>
                    <td className="mono-num px-5 py-3">GW{String(row.event)}</td>
                    <td className="px-5 py-3">
                      <Link href={`/managers/${row.entry}`} className="font-semibold hover:text-[#1f6b4d]">
                        {primaryManagerName(row)}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-stone-600">{row.player_name}</td>
                    <td className="mono-num px-5 py-3 text-right font-semibold">{row.points}</td>
                    <td className="mono-num px-5 py-3 text-right">#{nf.format(Number(row.final_rank))}</td>
                    <td className="mono-num px-5 py-3 text-right">{row.points_on_bench}</td>
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
