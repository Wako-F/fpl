import Link from "next/link";
import { GameweekPulseChart } from "@/components/charts";
import { SiteHeader, StatBlock } from "@/components/shell";
import { getClub } from "@/lib/api";
import { primaryManagerName } from "@/lib/display";

export const dynamic = "force-dynamic";

const nf = new Intl.NumberFormat("en-US");

export default async function ClubPage({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  const detail = await getClub(teamId);

  if (!detail.club) {
    return (
      <>
        <SiteHeader />
        <main className="mx-auto max-w-4xl px-5 py-20 md:px-8">
          <h1 className="text-4xl font-semibold tracking-tight">Club not found.</h1>
        </main>
      </>
    );
  }

  const gameweeks = detail.gameweeks.map((row) => ({
    ...row,
    median_points: row.avg_points,
    max_points: 0,
    volatility: "0",
    p90_points: row.avg_points,
    p10_points: row.avg_bench_points,
  }));

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <div className="mb-10 max-w-5xl">
          <div className="mono-num mb-3 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">
            Favourite club: {detail.club.short_name}
          </div>
          <h1 className="text-4xl font-semibold leading-none tracking-tight sm:text-5xl md:text-7xl">
            {detail.club.team_name} supporters in Kenya&apos;s FPL season.
          </h1>
        </div>

        <section className="grid grid-cols-1 gap-5 md:grid-cols-4">
          <StatBlock label="Declared supporters" value={nf.format(detail.club.managers)} detail={`${detail.club.share_pct}% of Kenya`} />
          <StatBlock label="Average total" value={String(detail.club.avg_total)} />
          <StatBlock label="Best Kenya rank" value={`#${nf.format(detail.club.best_rank)}`} />
          <StatBlock label="Bench points avg" value={String(detail.club.avg_bench_points)} />
        </section>

        <section className="mt-14 panel rounded-lg p-5">
          <GameweekPulseChart data={gameweeks} />
        </section>

        <section className="mt-10 panel rounded-lg">
          <div className="border-b border-stone-950/10 p-5">
            <h2 className="text-xl font-semibold tracking-tight">Top supporter seasons</h2>
          </div>
          <div className="divide-y divide-stone-950/10">
            {detail.leaders.slice(0, 25).map((row) => (
              <Link
                href={`/managers/${row.entry}`}
                key={row.entry}
                className="grid grid-cols-[4rem_1fr_auto] gap-4 px-5 py-3 text-sm transition hover:bg-stone-950/[0.025]"
              >
                <span className="mono-num text-stone-500">#{nf.format(row.rank)}</span>
                <span className="font-semibold">{primaryManagerName(row)}</span>
                <span className="mono-num font-semibold">{nf.format(row.total)}</span>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
