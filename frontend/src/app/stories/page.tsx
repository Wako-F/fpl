import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, CheckCircle, WarningCircle } from "@phosphor-icons/react/dist/ssr";
import { DataStatus, SiteFooter, SiteHeader, StatBlock } from "@/components/shell";
import { getLiveOverview, getWeeklyContent, type WeeklyContent } from "@/lib/api";

export const metadata: Metadata = {
  title: "Weekly report",
  description: "The current FPL gameweek in Kenya: leaders, scoring, captaincy, bench pain, player performance, and methodology.",
};
export const revalidate = 120;

function factObject(content: WeeklyContent | null, key: string): Record<string, unknown> {
  const value = content?.facts[key]?.value;
  return value && !Array.isArray(value) ? value : {};
}

function number(value: unknown, fallback = 0) {
  return typeof value === "number" || typeof value === "string" ? String(value) : String(fallback);
}

export default async function StoriesPage() {
  const overview = await getLiveOverview();
  const event = overview.event?.event ?? 1;
  let content: WeeklyContent | null = null;
  try {
    content = await getWeeklyContent(event);
  } catch {
    content = null;
  }
  const status = content ? Object.values(content.facts)[0]?.status ?? "live" : "live";
  const cohort = factObject(content, "cohort_scoring");
  const bench = factObject(content, "bench_pain");
  const weeklyLeader = factObject(content, "weekly_leader");

  return (
    <>
      <SiteHeader />
      <main id="main-content">
        <article>
          <header className="border-b border-stone-950/10">
            <div className="mx-auto max-w-[1500px] px-5 py-12 md:px-8 md:py-20">
              <div className="flex flex-wrap items-center gap-4"><DataStatus status={status} /><span className="font-mono text-xs text-stone-500">GW{event} report</span></div>
              <h1 className="mt-6 max-w-6xl text-balance text-5xl font-semibold leading-[0.93] tracking-[-0.05em] sm:text-6xl md:text-8xl">
                Kenya&apos;s gameweek, in numbers and decisions.
              </h1>
              <p className="mt-7 max-w-[65ch] text-lg leading-8 text-stone-600">
                A repeatable post-lock report built from the latest national table, a declared manager cohort, and the live player feed.
              </p>
            </div>
          </header>

          <section className="mx-auto max-w-[1500px] px-5 py-16 md:px-8">
            <div className="grid grid-cols-2 gap-x-6 gap-y-8 lg:grid-cols-4">
              <StatBlock label="Cohort average" value={number(cohort.avg_points ?? overview.cohort.avg_points, 0)} detail={`${number(cohort.managers ?? overview.cohort.managers)} managers`} />
              <StatBlock label="Cohort median" value={number(cohort.median_points ?? overview.cohort.median_points, 0)} />
              <StatBlock label="Highest captured" value={number(weeklyLeader.points ?? overview.cohort.max_points, 0)} detail={String(weeklyLeader.entry_name ?? "deep cohort")} />
              <StatBlock label="Bench pain" value={number(bench.points_on_bench, 0)} detail={String(bench.entry_name ?? "awaiting cohort refresh")} />
            </div>
          </section>

          <section className="bg-stone-950 text-[#fffdf7]">
            <div className="mx-auto grid max-w-[1500px] gap-10 px-5 py-16 md:grid-cols-[0.4fr_0.6fr] md:px-8 md:py-20">
              <div>
                <div className="font-mono text-xs uppercase tracking-[0.2em] text-[#d3ad68]">The player story</div>
                <h2 className="mt-4 text-4xl font-semibold leading-none tracking-[-0.04em] md:text-6xl">The players shaping GW{event}.</h2>
              </div>
              <ol className="divide-y divide-white/10 border-t border-white/10">
                {overview.topPlayers.slice(0, 8).map((player, index) => (
                  <li key={player.element} className="grid grid-cols-[2rem_1fr_auto] items-center gap-4 py-4">
                    <span className="font-mono text-xs text-stone-500">{String(index + 1).padStart(2, "0")}</span>
                    <span><span className="font-semibold">{player.web_name}</span><span className="ml-2 text-xs text-stone-400">{player.short_name} · {player.minutes} mins</span></span>
                    <span className="font-mono text-xl font-semibold">{player.total_points}</span>
                  </li>
                ))}
              </ol>
            </div>
          </section>

          <section className="mx-auto grid max-w-[1500px] gap-6 px-5 py-16 md:grid-cols-[0.65fr_0.35fr] md:px-8 md:py-20">
            <div className="panel rounded-[0.75rem] p-6 md:p-8">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-[#1f6b4d]">Editorial state</div>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight">{content ? "The weekly fact pack is ready." : "The live report is assembling."}</h2>
              <p className="mt-4 max-w-[65ch] leading-7 text-stone-600">
                {content
                  ? "The machine-readable brief, article draft, social outline, and engineering note share the same verified facts and source snapshot."
                  : "The page can already show live scores. Captaincy, bench pain, rank movement, and publishable copy appear after the deep cohort and content jobs finish."}
              </p>
              <div className="mt-6 flex items-center gap-2 text-sm font-semibold text-[#1f6b4d]">
                {content ? <CheckCircle size={20} weight="fill" /> : <WarningCircle size={20} />}
                {content ? `Snapshot ${Object.values(content.facts)[0]?.source_snapshot_id}` : "Awaiting generated content facts"}
              </div>
            </div>
            <aside className="bg-[#e9eee8] p-6 md:rounded-[0.75rem]">
              <h2 className="text-xl font-semibold">How to read this report</h2>
              <p className="mt-3 text-sm leading-6 text-stone-600">National standings and behavioural cohort statistics are different populations. The label, sample size, calculation time, and status travel with each fact.</p>
              <Link href="/methodology" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[#1f6b4d] hover:gap-3">Read the methodology <ArrowRight size={16} /></Link>
            </aside>
          </section>
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
