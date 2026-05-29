import Link from "next/link";
import { ArrowRight, Database, Trophy } from "@phosphor-icons/react/dist/ssr";
import {
  ArchetypeChart,
  DistributionChart,
  GameweekPulseChart,
  PercentileLadderChart,
  RankBandChart,
  RankBandHeatmap,
  SupporterClubChart,
} from "@/components/charts";
import { CompactManagerTable } from "@/components/insight-tables";
import { SectionLabel, SiteHeader, StatBlock, navCards } from "@/components/shell";
import { getInsights, getLeaderboard, getOverview } from "@/lib/api";
import { primaryManagerName, secondaryManagerName } from "@/lib/display";

export const dynamic = "force-dynamic";

const nf = new Intl.NumberFormat("en-US");

function asArray<T>(value: T[] | string | null | undefined): T[] {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

export default async function Home() {
  const [overview, insights, leaders] = await Promise.all([getOverview(), getInsights(), getLeaderboard(8)]);
  const chaosWeek = overview.gameweeks.reduce((best, row) =>
    Number(row.volatility) > Number(best.volatility) ? row : best
  );

  return (
    <>
      <SiteHeader />
      <main>
        <section className="border-b border-stone-950/10">
          <div className="mx-auto grid min-h-[78dvh] max-w-[1500px] grid-cols-1 gap-10 px-5 py-12 md:grid-cols-[1.35fr_0.65fr] md:px-8 md:py-20">
            <div className="flex flex-col justify-between gap-12">
              <div>
                <h1 className="max-w-5xl text-4xl font-semibold leading-[0.98] tracking-tight text-stone-950 sm:text-5xl md:text-7xl">
                  Kenya&apos;s Fantasy Premier League season, in data.
                </h1>
                <p className="mt-6 max-w-2xl text-lg leading-8 text-stone-600">
                  Final standings, manager profiles, weekly histories, player data, and derived season metrics
                  for 445,629 Kenyan managers.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
                <StatBlock label="Kenyan managers" value={nf.format(overview.summary.managers)} detail="full country league scrape" />
                <StatBlock label="Champion score" value={nf.format(overview.summary.max_points)} detail="highest final total" />
                <StatBlock label="Median score" value={nf.format(Number(overview.summary.median_points))} detail="national midpoint" />
              </div>
            </div>

            <aside className="panel self-end rounded-lg p-5">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold">Top of Kenya</div>
                  <div className="text-xs text-stone-500">Final country league standings</div>
                </div>
                <Trophy size={22} weight="duotone" className="text-[#1f6b4d]" />
              </div>
              <div className="divide-y divide-stone-950/10">
                {leaders.map((row) => (
                  <Link
                    href={`/managers/${row.entry}`}
                    key={row.entry}
                    className="group grid grid-cols-[3rem_1fr_auto] items-center gap-3 py-3"
                  >
                    <span className="mono-num text-sm text-stone-500">#{row.rank}</span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-stone-950 group-hover:text-[#1f6b4d]">
                        {primaryManagerName(row)}
                      </span>
                      <span className="block truncate text-xs text-stone-500">{secondaryManagerName(row)}</span>
                    </span>
                    <span className="mono-num text-sm font-semibold">{nf.format(row.total)}</span>
                  </Link>
                ))}
              </div>
              <Link
                href="/leaderboard"
                className="mt-5 inline-flex items-center gap-2 rounded-md bg-stone-950 px-4 py-3 text-sm font-semibold text-[#fffdf7] transition active:translate-y-px"
              >
                Open leaderboard <ArrowRight size={16} />
              </Link>
            </aside>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-14 md:px-8 md:py-20">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {navCards.map((card) => {
              const Icon = card.icon;
              return (
                <Link
                  href={card.href}
                  key={card.label}
                  className="panel group flex items-center justify-between rounded-lg p-5 transition hover:-translate-y-0.5 hover:bg-white"
                >
                  <span className="text-lg font-semibold">{card.label}</span>
                  <Icon size={22} className="text-[#1f6b4d] transition group-hover:translate-x-1" />
                </Link>
              );
            })}
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-10 md:px-8">
          <SectionLabel kicker="Distribution" title="Final points across the Kenya league." />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.68fr_0.32fr]">
            <div className="panel rounded-lg p-5">
              <DistributionChart data={overview.distribution} />
            </div>
            <div className="grid gap-5">
              <StatBlock label="Top 1% threshold" value={nf.format(Number(overview.summary.p99_points))} />
              <StatBlock label="Top 10% threshold" value={nf.format(Number(overview.summary.p90_points))} />
              <StatBlock label="Most volatile gameweek" value={`GW${chaosWeek.event}`} detail={`${chaosWeek.volatility} std dev`} />
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-16 md:px-8">
          <SectionLabel kicker="Weekly scoring" title="Average points across the season." />
          <div className="panel rounded-lg p-5">
            <GameweekPulseChart data={overview.gameweeks} />
          </div>
        </section>

        <section id="rank-bands" className="mx-auto max-w-[1500px] px-5 py-16 md:px-8">
          <SectionLabel kicker="Rank bands" title="How scoring and bench points vary by final rank." />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.62fr_0.38fr]">
            <div className="panel rounded-lg p-5">
              <RankBandChart data={overview.rankBands} />
            </div>
            <div className="panel rounded-lg p-5">
              <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
                <Database size={18} className="text-[#1f6b4d]" />
                Process metrics
              </div>
              <div className="divide-y divide-stone-950/10">
                {overview.rankBands.map((band) => (
                  <div key={band.band} className="grid grid-cols-[5.5rem_1fr_auto] gap-3 py-3 text-sm">
                    <span className="font-semibold">{band.band}</span>
                    <span className="text-stone-500">avg value {band.avg_team_value}</span>
                    <span className="mono-num font-semibold">{band.avg_weekly_points}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-16 md:px-8">
          <SectionLabel kicker="Percentiles" title="Point thresholds across the table." />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.55fr_0.45fr]">
            <div className="panel rounded-lg p-5">
              <PercentileLadderChart data={insights.percentiles} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              {insights.percentiles.slice(0, 6).map((row) => (
                <StatBlock key={row.label} label={row.label} value={nf.format(row.points)} />
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-16 md:px-8">
          <SectionLabel kicker="Archetypes" title="Manager groups based on scoring patterns." />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.58fr_0.42fr]">
            <div className="panel rounded-lg p-5">
              <ArchetypeChart data={insights.archetypes} />
            </div>
            <div className="panel rounded-lg p-5">
              <div className="divide-y divide-stone-950/10">
                {insights.archetypes.map((row) => (
                  <div key={row.archetype} className="grid grid-cols-[1fr_auto] gap-4 py-3">
                    <div>
                      <div className="font-semibold">{row.archetype}</div>
                      <div className="text-xs text-stone-500">
                        avg {row.avg_weekly_points} pts/week, volatility {row.avg_volatility}
                      </div>
                    </div>
                    <div className="mono-num text-right font-semibold">{nf.format(row.managers)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-16 md:px-8">
          <SectionLabel kicker="Band heatmap" title="Average weekly points by rank band." />
          <div className="panel rounded-lg p-5">
            <RankBandHeatmap data={insights.rankBandGameweeks} />
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-16 md:px-8">
          <SectionLabel kicker="Club support" title="Declared favourite clubs among Kenyan managers." />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.62fr_0.38fr]">
            <div className="panel rounded-lg p-5">
              <SupporterClubChart data={insights.favoriteTeams} />
            </div>
            <div className="panel rounded-lg p-5">
              <div className="mb-4 text-sm font-semibold">Declared favourite clubs</div>
              <div className="divide-y divide-stone-950/10">
                {insights.favoriteTeams.slice(0, 8).map((team) => (
                  <div key={team.team_id} className="grid grid-cols-[1fr_auto] gap-4 py-3">
                    <div>
                      <div className="font-semibold">{team.team_name}</div>
                      <div className="text-xs text-stone-500">
                        avg {team.avg_total} pts, best rank #{nf.format(team.best_rank)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="mono-num font-semibold">{nf.format(team.managers)}</div>
                      <div className="mono-num text-xs text-stone-500">{team.share_pct}%</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-16 md:px-8">
          <SectionLabel kicker="Weekly leaders" title="Top scores from selected gameweeks." />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {insights.extremes.slice(0, 6).map((week) => (
              <div key={week.event} className="panel rounded-lg p-5">
                <div className="mb-4 flex items-baseline justify-between">
                  <h3 className="text-lg font-semibold tracking-tight">GW{week.event}</h3>
                  <span className="mono-num text-xs uppercase tracking-[0.18em] text-stone-500">top score</span>
                </div>
                <div className="divide-y divide-stone-950/10">
                  {asArray<(typeof week.top_scores)[number]>(week.top_scores).slice(0, 5).map((row) => (
                    <Link
                      key={`${week.event}-${row.entry}`}
                      href={`/managers/${row.entry}`}
                      className="grid grid-cols-[1fr_auto] gap-4 py-2 text-sm transition hover:text-[#1f6b4d]"
                    >
                      <span className="truncate font-semibold">{primaryManagerName(row)}</span>
                      <span className="mono-num">{row.points}</span>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto grid max-w-[1500px] grid-cols-1 gap-5 px-5 py-16 md:px-8 lg:grid-cols-2">
          <CompactManagerTable
            title="Most consistent profiles"
            rows={insights.consistency}
            metricLabel="ratio"
            metricKey="consistency_ratio"
          />
          <CompactManagerTable
            title="Best points per million"
            rows={insights.efficiency}
            metricLabel="ppm"
            metricKey="points_per_million"
          />
        </section>
      </main>
    </>
  );
}
