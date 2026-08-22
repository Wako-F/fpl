import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, BracketsCurly, Database, GitBranch, Notebook } from "@phosphor-icons/react/dist/ssr";
import { SiteFooter, SiteHeader } from "@/components/shell";

export const metadata: Metadata = { title: "Data lab", description: "The data science and engineering work behind FPL Kenya." };

const work = [
  { icon: Database, title: "Season-aware warehouse", body: "Immutable raw snapshots feed canonical event facts, standings snapshots, and a versioned editorial layer." },
  { icon: BracketsCurly, title: "Reproducible content", body: "One JSON brief drives the article, social copy, engineering note, and visual assets for each gameweek." },
  { icon: GitBranch, title: "Models with baselines", body: "Expected-points and differential models will ship with cutoffs, backtests, calibration, and leakage checks." },
  { icon: Notebook, title: "Weekly build notes", body: "Each report exposes one technical decision: data quality, dimensional modelling, API design, caching, or evaluation." },
];

export default function LabPage() {
  return (
    <>
      <SiteHeader />
      <main id="main-content" className="mx-auto max-w-[1500px] px-5 py-12 md:px-8 md:py-20">
        <div className="font-mono text-xs uppercase tracking-[0.22em] text-[#1f6b4d]">Data science · engineering</div>
        <h1 className="mt-5 max-w-6xl text-balance text-5xl font-semibold leading-[0.93] tracking-[-0.05em] sm:text-6xl md:text-8xl">The work behind the weekly numbers.</h1>
        <p className="mt-7 max-w-[65ch] text-lg leading-8 text-stone-600">A public build log for the pipeline, metrics, models, and editorial tooling that power FPL Kenya.</p>

        <section className="mt-16 grid gap-px overflow-hidden bg-stone-950/10 md:grid-cols-2">
          {work.map((item, index) => {
            const Icon = item.icon;
            return <article key={item.title} className={`min-h-64 p-6 md:p-8 ${index === 0 ? "bg-stone-950 text-[#fffdf7]" : "bg-[#fffdf7]"}`}><Icon size={26} className={index === 0 ? "text-[#d3ad68]" : "text-[#1f6b4d]"} /><h2 className="mt-16 text-2xl font-semibold tracking-tight">{item.title}</h2><p className={`mt-3 max-w-[55ch] text-sm leading-6 ${index === 0 ? "text-stone-400" : "text-stone-600"}`}>{item.body}</p></article>;
          })}
        </section>

        <section className="mt-16 grid gap-8 border-t border-stone-950/10 pt-10 md:grid-cols-[0.65fr_0.35fr]">
          <div><div className="font-mono text-xs uppercase tracking-[0.2em] text-[#1f6b4d]">Current notebook</div><h2 className="mt-3 text-3xl font-semibold">Why content facts carry their own lineage.</h2><p className="mt-4 max-w-[65ch] leading-7 text-stone-600">A gameweek number is useful only when we know whether it was live or final, which managers it represents, when it was calculated, and which snapshot can reproduce it.</p></div>
          <Link href="/stories" className="group flex min-h-44 flex-col justify-between bg-[#e9eee8] p-6 md:rounded-[0.75rem]"><span className="text-sm font-semibold">See it in the weekly report</span><ArrowRight size={22} className="text-[#1f6b4d] transition group-hover:translate-x-1" /></Link>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
