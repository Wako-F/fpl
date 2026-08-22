import Link from "next/link";
import { ArrowRight, Clock, Database, Trophy } from "@phosphor-icons/react/dist/ssr";
import { DataStatus, SectionLabel, SiteFooter, SiteHeader, StatBlock, navCards } from "@/components/shell";
import { getLiveOverview } from "@/lib/api";
import { primaryManagerName, secondaryManagerName } from "@/lib/display";

export const revalidate = 120;

const nf = new Intl.NumberFormat("en-KE");
const dateTime = new Intl.DateTimeFormat("en-KE", {
  timeZone: "Africa/Nairobi",
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZoneName: "short",
});

function eventStatus(event: Awaited<ReturnType<typeof getLiveOverview>>["event"]) {
  if (event?.finished && event.data_checked) return "final" as const;
  if (event?.finished) return "provisional" as const;
  return "live" as const;
}

export default async function Home() {
  const overview = await getLiveOverview();
  const status = eventStatus(overview.event);
  const gw = overview.event?.event ?? 1;
  const summary = overview.summary;
  const cohort = overview.cohort;

  return (
    <>
      <SiteHeader />
      <main id="main-content">
        <section className="border-b border-stone-950/10">
          <div className="mx-auto grid min-h-[72dvh] max-w-[1500px] gap-12 px-5 py-12 md:grid-cols-[1.25fr_0.75fr] md:px-8 md:py-20">
            <div className="flex flex-col justify-between gap-14">
              <div>
                <div className="mb-6 flex flex-wrap items-center gap-4">
                  <DataStatus status={status} />
                  <span className="font-mono text-xs text-stone-500">2026/27 · GW{gw}</span>
                </div>
                <h1 className="max-w-5xl text-balance text-5xl font-semibold leading-[0.92] tracking-[-0.055em] text-stone-950 sm:text-6xl md:text-[5.7rem]">
                  Gameweek {gw}, through a Kenyan lens.
                </h1>
                <p className="mt-7 max-w-[62ch] text-pretty text-lg leading-8 text-stone-600">
                  Live national standings, player performance, manager decisions, and the data work behind every number.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-x-6 gap-y-7 lg:grid-cols-4">
                <StatBlock
                  label="Captured managers"
                  value={nf.format(summary?.managers ?? 0)}
                  detail={overview.snapshot?.is_complete ? "complete standings snapshot" : "bounded snapshot"}
                />
                <StatBlock label="National leader" value={nf.format(summary?.max_points ?? 0)} detail="current total" />
                <StatBlock label="Cohort average" value={String(cohort.avg_points ?? "—")} detail={`${nf.format(cohort.managers)} managers`} />
                <StatBlock label="Top live score" value={String(overview.topPlayers[0]?.total_points ?? "—")} detail={overview.topPlayers[0]?.web_name ?? "awaiting fixtures"} />
              </div>
            </div>

            <aside className="self-end bg-stone-950 p-6 text-[#fffdf7] shadow-[0_28px_80px_-50px_rgba(31,29,24,0.9)] md:-mb-8 md:rounded-[0.75rem]">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <div className="font-mono text-[0.68rem] uppercase tracking-[0.2em] text-stone-400">Top of Kenya</div>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">Latest captured table</h2>
                </div>
                <Trophy size={28} weight="duotone" className="text-[#d3ad68]" />
              </div>
              {overview.leaders.length ? (
                <ol className="divide-y divide-white/10">
                  {overview.leaders.slice(0, 6).map((row) => (
                    <li key={row.entry}>
                      <Link href={`/managers/${row.entry}`} className="group grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 py-3.5">
                        <span className="font-mono text-sm text-stone-400">{row.rank}</span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-semibold group-hover:text-[#d3ad68]">{primaryManagerName(row)}</span>
                          <span className="block truncate text-xs text-stone-400">{secondaryManagerName(row)}</span>
                        </span>
                        <span className="font-mono text-sm font-semibold">{nf.format(row.total)}</span>
                      </Link>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="border-y border-white/10 py-8 text-sm leading-6 text-stone-300">
                  The first 2026/27 standings snapshot is being collected.
                </p>
              )}
              <Link href="/leaderboard" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[#d3ad68] transition hover:gap-3">
                Explore the leaderboard <ArrowRight size={16} />
              </Link>
            </aside>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 pt-20 md:px-8">
          <SectionLabel kicker="Match centre" title={`The shape of Gameweek ${gw}.`} />
          <div className="grid gap-5 lg:grid-cols-[0.62fr_0.38fr]">
            <div className="panel overflow-hidden rounded-[0.75rem]">
              <div className="flex items-center justify-between border-b border-stone-950/10 px-5 py-4">
                <div className="flex items-center gap-2 text-sm font-semibold"><Clock size={18} className="text-[#1f6b4d]" /> Fixtures</div>
                <span className="font-mono text-xs text-stone-500">Nairobi time</span>
              </div>
              <div className="divide-y divide-stone-950/10">
                {overview.fixtures.map((fixture) => (
                  <div key={fixture.fixture_id} className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-5 py-4 text-sm">
                    <span className="text-right font-semibold">{fixture.team_h_short}</span>
                    <span className="min-w-24 text-center font-mono text-xs text-stone-500">
                      {fixture.started || fixture.finished
                        ? `${fixture.team_h_score ?? 0} — ${fixture.team_a_score ?? 0}`
                        : dateTime.format(new Date(fixture.kickoff_time))}
                    </span>
                    <span className="font-semibold">{fixture.team_a_short}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-[#e9eee8] p-6 md:rounded-[0.75rem]">
              <div className="font-mono text-[0.68rem] uppercase tracking-[0.2em] text-[#1f6b4d]">Deep cohort</div>
              <h3 className="mt-3 text-2xl font-semibold tracking-tight">Decision data, with the sample attached.</h3>
              <p className="mt-4 text-sm leading-6 text-stone-600">
                Bench, transfer, captaincy, and chip figures use the manager cohort we can refresh responsibly. Every published figure includes its sample size and status.
              </p>
              <dl className="mt-6 grid grid-cols-2 gap-5">
                <div><dt className="text-xs text-stone-500">Median</dt><dd className="mt-1 font-mono text-2xl font-semibold">{cohort.median_points ?? "—"}</dd></div>
                <div><dt className="text-xs text-stone-500">Bench avg</dt><dd className="mt-1 font-mono text-2xl font-semibold">{cohort.avg_bench_points ?? "—"}</dd></div>
              </dl>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-20 md:px-8">
          <SectionLabel kicker="Player pulse" title="Who is moving the gameweek." />
          {overview.topPlayers.length ? (
            <div className="grid gap-px overflow-hidden bg-stone-950/10 md:grid-cols-2 lg:grid-cols-5">
              {overview.topPlayers.slice(0, 5).map((player, index) => (
                <article key={player.element} className="bg-[#f7f6f0] p-5 transition duration-200 hover:bg-white">
                  <div className="flex items-baseline justify-between">
                    <span className="font-mono text-xs text-stone-500">0{index + 1}</span>
                    <span className="font-mono text-3xl font-semibold">{player.total_points}</span>
                  </div>
                  <h3 className="mt-8 truncate text-lg font-semibold">{player.web_name}</h3>
                  <p className="mt-1 text-xs text-stone-500">{player.short_name} · {player.minutes} mins · {player.bonus} bonus</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="panel rounded-[0.75rem] p-8 text-sm text-stone-600">Player scores will appear as GW{gw} fixtures update.</div>
          )}
          <Link href="/players" className="mt-7 inline-flex items-center gap-2 text-sm font-semibold text-[#1f6b4d] hover:gap-3">
            Open player watch <ArrowRight size={16} />
          </Link>
        </section>

        <section className="border-y border-stone-950/10 bg-[#eeece3]">
          <div className="mx-auto max-w-[1500px] px-5 py-20 md:px-8">
            <div className="mb-10 flex items-center gap-3 text-sm font-semibold"><Database size={20} className="text-[#1f6b4d]" /> One pipeline, four useful surfaces</div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {navCards.map((card, index) => {
                const Icon = card.icon;
                return (
                  <Link href={card.href} key={card.label} className={`group min-h-48 p-5 transition duration-200 hover:-translate-y-1 ${index === 0 ? "bg-stone-950 text-[#fffdf7]" : "bg-[#fffdf7]"}`}>
                    <Icon size={24} className={index === 0 ? "text-[#d3ad68]" : "text-[#1f6b4d]"} />
                    <div className="mt-16 flex items-end justify-between gap-4">
                      <span className="text-lg font-semibold">{card.label}</span>
                      <ArrowRight size={18} className="transition group-hover:translate-x-1" />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
