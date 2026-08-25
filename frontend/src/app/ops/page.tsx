import type { Metadata } from "next";
import Link from "next/link";
import {
  Article,
  CheckCircle,
  ClockCountdown,
  Database,
  Pulse,
  WarningCircle,
} from "@phosphor-icons/react/dist/ssr";
import { SiteFooter, SiteHeader, StatBlock } from "@/components/shell";
import { getContentArtifact, getOpsStatus, type ContentArtifact } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Control room",
  description: "Live coverage, pipeline health, and weekly content packs for FPL Kenya.",
  robots: { index: false, follow: false },
};

const artifactLabels: Record<string, string> = {
  article: "Article draft",
  social: "Social pack",
  engineering: "Engineering note",
  brief: "JSON brief",
};

function kenyaTime(value?: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-KE", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Africa/Nairobi",
  }).format(new Date(value));
}

function age(value?: string | null) {
  if (!value) return "not collected";
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function duration(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return minutes < 60 ? `${minutes}m ${seconds % 60}s` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

function statusTone(status: string) {
  if (status === "finished" || status === "pass" || status === "final") {
    return "bg-[#e2eee7] text-[#15583e]";
  }
  if (status === "failed" || status === "fail") return "bg-red-100 text-red-800";
  return "bg-amber-100 text-amber-800";
}

export default async function OpsPage({
  searchParams,
}: {
  searchParams: Promise<{ event?: string; artifact?: string }>;
}) {
  const query = await searchParams;
  const ops = await getOpsStatus();
  const selectedEvent = Number(query.event) || ops.content_packs[0]?.event || ops.event?.event || 1;
  const selectedArtifact = artifactLabels[query.artifact ?? ""] ? query.artifact! : "article";
  let artifact: ContentArtifact | null = null;
  try {
    artifact = await getContentArtifact(selectedEvent, selectedArtifact);
  } catch {
    artifact = null;
  }

  const snapshot = ops.published_snapshot;
  const crawl = ops.full_crawl;
  const progress = crawl?.progress;
  const expectedPages = crawl?.expected_pages ?? progress?.scheduled_pages ?? 0;
  const finishedPages = progress?.finished_pages ?? crawl?.pages_collected ?? 0;
  const coveragePercent = expectedPages ? Math.min(100, (finishedPages / expectedPages) * 100) : 0;
  const allQualityPass = ops.quality.every((check) => check.status === "pass");

  return (
    <>
      <SiteHeader />
      <main id="main-content" className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <section className="grid gap-10 border-b border-stone-950/10 pb-12 lg:grid-cols-[0.62fr_0.38fr] lg:items-end">
          <div>
            <div className="font-mono text-xs uppercase tracking-[0.22em] text-[#1f6b4d]">
              VPS control room · {ops.season}
            </div>
            <h1 className="mt-5 max-w-5xl text-balance text-5xl font-semibold leading-[0.93] tracking-[-0.05em] sm:text-6xl md:text-8xl">
              The whole project, at a glance.
            </h1>
            <p className="mt-7 max-w-[65ch] text-lg leading-8 text-stone-600">
              National coverage, pipeline freshness, quality checks, and every generated content pack—read directly from the production system.
            </p>
          </div>
          <aside className="rounded-[0.8rem] bg-stone-950 p-6 text-[#fffdf7] md:p-8">
            <div className="flex items-center justify-between gap-4">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-stone-400">Current signal</span>
              {allQualityPass ? <CheckCircle size={24} weight="fill" className="text-[#d3ad68]" /> : <WarningCircle size={24} className="text-amber-400" />}
            </div>
            <div className="mt-10 text-3xl font-semibold tracking-tight">
              {allQualityPass ? "Production is healthy." : "A quality check needs attention."}
            </div>
            <p className="mt-3 text-sm leading-6 text-stone-400">
              GW{ops.event?.event ?? "—"} is {ops.event?.data_checked ? "officially checked" : "still awaiting FPL's final check"}. Latest live player refresh: {age(ops.freshness.live_players)}.
            </p>
          </aside>
        </section>

        <section className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <StatBlock label="Published managers" value={(snapshot?.managers_collected ?? 0).toLocaleString("en-KE")} detail={snapshot?.is_complete ? "complete Kenya table" : "fast live slice"} />
          <StatBlock label="Pages published" value={(snapshot?.pages_collected ?? 0).toLocaleString("en-KE")} detail={snapshot?.crawl_mode ?? "awaiting crawl"} />
          <StatBlock label="Quality checks" value={`${ops.quality.filter((item) => item.status === "pass").length}/${ops.quality.length}`} detail={allQualityPass ? "all passing" : "review required"} />
          <StatBlock label="Content packs" value={ops.content_packs.length.toLocaleString("en-KE")} detail={ops.content_packs[0] ? `latest: GW${ops.content_packs[0].event} · ${ops.content_packs[0].status}` : "none generated"} />
        </section>

        <section className="mt-16 grid gap-8 lg:grid-cols-[0.64fr_0.36fr]">
          <article className="panel rounded-[0.8rem] p-6 md:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="font-mono text-xs uppercase tracking-[0.2em] text-[#1f6b4d]">Full-country coverage</div>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight">Every manager crawl</h2>
              </div>
              <span className={`rounded-md px-3 py-1.5 font-mono text-xs uppercase tracking-[0.14em] ${statusTone(crawl?.crawl_status ?? "pending")}`}>
                {crawl?.crawl_status ?? "not started"}
              </span>
            </div>
            <div className="mt-10 flex items-end justify-between gap-6">
              <div>
                <div className="mono-num text-5xl font-semibold tracking-[-0.05em]">{coveragePercent.toFixed(1)}%</div>
                <div className="mt-2 text-sm text-stone-500">{finishedPages.toLocaleString("en-KE")} of {expectedPages.toLocaleString("en-KE")} pages</div>
              </div>
              <div className="text-right text-sm leading-6 text-stone-600">
                <div>{(progress?.rows_fetched ?? crawl?.rows_fetched ?? 0).toLocaleString("en-KE")} rows fetched</div>
                <div>{progress?.failed_pages ?? 0} failed pages</div>
              </div>
            </div>
            <progress aria-label="Full-country crawl progress" value={coveragePercent} max="100" className="mt-7 h-3 w-full overflow-hidden rounded-none accent-[#1f6b4d]" />
            <dl className="mt-8 grid gap-px overflow-hidden bg-stone-950/10 text-sm sm:grid-cols-3">
              <div className="bg-[#fffdf7] p-4"><dt className="text-stone-500">Expected managers</dt><dd className="mono-num mt-2 font-semibold">{(crawl?.expected_rows ?? 0).toLocaleString("en-KE")}</dd></div>
              <div className="bg-[#fffdf7] p-4"><dt className="text-stone-500">Average page</dt><dd className="mono-num mt-2 font-semibold">{progress?.avg_page_ms ? `${progress.avg_page_ms} ms` : "—"}</dd></div>
              <div className="bg-[#fffdf7] p-4"><dt className="text-stone-500">Heartbeat</dt><dd className="mono-num mt-2 font-semibold">{age(crawl?.last_heartbeat_at)}</dd></div>
            </dl>
          </article>

          <aside className="bg-[#e9eee8] p-6 md:rounded-[0.8rem] md:p-8">
            <div className="flex items-center gap-3"><Pulse size={22} className="text-[#1f6b4d]" /><h2 className="text-xl font-semibold">Data freshness</h2></div>
            <dl className="mt-8 divide-y divide-stone-950/10">
              {[
                ["Live players", ops.freshness.live_players],
                ["Standings", ops.freshness.standings],
                ["Fixtures", ops.freshness.fixtures],
                ["Bootstrap", ops.freshness.bootstrap],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-4 py-4 first:pt-0">
                  <dt className="text-sm text-stone-600">{label}</dt>
                  <dd className="mono-num text-sm font-medium" title={kenyaTime(value)}>{age(value)}</dd>
                </div>
              ))}
            </dl>
          </aside>
        </section>

        <section className="mt-16 grid gap-10 lg:grid-cols-[0.38fr_0.62fr]">
          <div>
            <div className="font-mono text-xs uppercase tracking-[0.2em] text-[#1f6b4d]">Editorial output</div>
            <h2 className="mt-3 text-4xl font-semibold tracking-[-0.04em]">Content packs</h2>
            <p className="mt-4 max-w-[48ch] leading-7 text-stone-600">Choose a gameweek and artifact. The preview comes from the files currently stored on the VPS.</p>
            <div className="mt-8 grid gap-3">
              {ops.content_packs.map((pack) => (
                <div key={pack.event} className="border-t border-stone-950/10 pt-4">
                  <div className="flex items-center justify-between gap-4">
                    <div><div className="font-semibold">Gameweek {pack.event}</div><div className="mt-1 text-xs text-stone-500">{pack.facts} facts · sample up to {pack.largest_sample?.toLocaleString("en-KE")}</div></div>
                    <span className={`rounded px-2 py-1 font-mono text-[0.65rem] uppercase tracking-[0.12em] ${statusTone(pack.status)}`}>{pack.status}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {pack.artifacts.map((item) => (
                      <Link key={item.key} href={`/ops?event=${pack.event}&artifact=${item.key}`} className={`rounded-md px-3 py-2 text-xs font-medium transition active:translate-y-px ${selectedEvent === pack.event && selectedArtifact === item.key ? "bg-stone-950 text-[#fffdf7]" : "bg-stone-950/5 hover:bg-stone-950/10"}`}>
                        {artifactLabels[item.key]}
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <article className="min-w-0 overflow-hidden rounded-[0.8rem] bg-stone-950 text-[#fffdf7]">
            <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 px-5 py-4 md:px-7">
              <div className="flex items-center gap-3"><Article size={20} className="text-[#d3ad68]" /><div><div className="text-sm font-semibold">GW{selectedEvent} · {artifactLabels[selectedArtifact]}</div><div className="mt-0.5 font-mono text-[0.65rem] uppercase tracking-[0.15em] text-stone-500">{artifact?.filename ?? "not generated"}</div></div></div>
              <div className="font-mono text-xs text-stone-500">{artifact ? `${artifact.bytes.toLocaleString("en-KE")} bytes · ${kenyaTime(artifact.modified_at)}` : "Awaiting file"}</div>
            </header>
            {artifact ? <pre className="max-h-[52rem] overflow-auto whitespace-pre-wrap break-words p-5 font-mono text-xs leading-6 text-stone-300 md:p-7">{artifact.content}</pre> : <div className="grid min-h-72 place-items-center p-8 text-center text-sm text-stone-400">This artifact has not been generated for the selected gameweek.</div>}
          </article>
        </section>

        <section className="mt-16 grid gap-8 lg:grid-cols-2">
          <article>
            <div className="flex items-center gap-3"><Database size={22} className="text-[#1f6b4d]" /><h2 className="text-2xl font-semibold">Quality checks</h2></div>
            <div className="mt-6 divide-y divide-stone-950/10 border-y border-stone-950/10">
              {ops.quality.map((check) => <div key={check.check_name} className="grid grid-cols-[1fr_auto_auto] items-center gap-4 py-4 text-sm"><span className="font-medium">{check.check_name.replaceAll("_", " ")}</span><span className="mono-num text-stone-500">{check.observed_value ?? "—"}</span><span className={`rounded px-2 py-1 font-mono text-[0.65rem] uppercase ${statusTone(check.status)}`}>{check.status}</span></div>)}
            </div>
          </article>
          <article>
            <div className="flex items-center gap-3"><ClockCountdown size={22} className="text-[#1f6b4d]" /><h2 className="text-2xl font-semibold">Recent pipeline runs</h2></div>
            <div className="mt-6 divide-y divide-stone-950/10 border-y border-stone-950/10">
              {ops.runs.slice(0, 10).map((run) => <div key={run.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-4 py-4 text-sm"><div><div className="font-medium">{run.job_name}</div><div className="mt-1 text-xs text-stone-500">{kenyaTime(run.started_at)}</div></div><span className="mono-num text-xs text-stone-500">{duration(run.duration_seconds)}</span><span className={`rounded px-2 py-1 font-mono text-[0.65rem] uppercase ${statusTone(run.status)}`}>{run.status}</span></div>)}
            </div>
          </article>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
