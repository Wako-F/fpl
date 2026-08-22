import type { Metadata } from "next";
import { Database, Pulse, ShieldCheck, UsersThree } from "@phosphor-icons/react/dist/ssr";
import { SiteFooter, SiteHeader } from "@/components/shell";

export const metadata: Metadata = { title: "Methodology", description: "How FPL Kenya collects, tests, labels, and publishes 2026/27 data." };

const layers = [
  { title: "Raw snapshots", body: "Official public FPL responses are stored with season, event, request URL, capture time, status, and a content hash." },
  { title: "Canonical facts", body: "Players, fixtures, standings snapshots, manager histories, picks, chips, and live scores use explicit season and event keys." },
  { title: "Editorial facts", body: "Every publishable number carries a status, cohort, sample size, calculation time, methodology, and source snapshot." },
];

const endpoints = ["bootstrap-static", "fixtures", "event/{gw}/live", "leagues-classic/131/standings", "entry/{id}", "entry/{id}/history", "entry/{id}/event/{gw}/picks"];

export default function MethodologyPage() {
  return (
    <>
      <SiteHeader />
      <main id="main-content">
        <header className="mx-auto max-w-[1500px] px-5 py-12 md:px-8 md:py-20">
          <div className="font-mono text-xs uppercase tracking-[0.22em] text-[#1f6b4d]">Open methodology · v1</div>
          <h1 className="mt-5 max-w-6xl text-balance text-5xl font-semibold leading-[0.93] tracking-[-0.05em] sm:text-6xl md:text-8xl">Every number should be traceable.</h1>
          <p className="mt-7 max-w-[65ch] text-lg leading-8 text-stone-600">How the 2026/27 data desk separates national standings, manager-cohort behaviour, live scores, and final published claims.</p>
        </header>

        <section className="border-y border-stone-950/10 bg-[#eeece3]">
          <div className="mx-auto grid max-w-[1500px] gap-px bg-stone-950/10 md:grid-cols-3">
            {layers.map((layer, index) => (
              <article key={layer.title} className="bg-[#eeece3] px-5 py-10 md:px-8">
                <span className="font-mono text-xs text-[#1f6b4d]">0{index + 1}</span>
                <h2 className="mt-8 text-2xl font-semibold tracking-tight">{layer.title}</h2>
                <p className="mt-3 max-w-[55ch] text-sm leading-6 text-stone-600">{layer.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto grid max-w-[1500px] gap-10 px-5 py-16 md:grid-cols-[0.42fr_0.58fr] md:px-8 md:py-20">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold"><UsersThree size={20} className="text-[#1f6b4d]" /> Two populations</div>
            <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">National table ≠ deep cohort.</h2>
          </div>
          <div className="grid gap-6 text-sm leading-7 text-stone-600">
            <p><strong className="text-stone-950">National standings</strong> come from captured pages of country league 131. A snapshot is explicitly labelled complete or bounded.</p>
            <p><strong className="text-stone-950">Manager behaviour</strong>—captaincy, chips, bench points, and transfer hits—uses the declared deep cohort. Those figures always show the collected sample size.</p>
            <p>We do not silently generalise cohort behaviour to every Kenyan manager. Manager names are displayed only where they already appear in public standings; aggregate downloads omit names.</p>
          </div>
        </section>

        <section className="mx-auto max-w-[1500px] px-5 py-12 md:px-8">
          <div className="grid gap-5 md:grid-cols-3">
            <div className="bg-stone-950 p-6 text-[#fffdf7] md:rounded-[0.75rem]"><Pulse size={24} className="text-[#d3ad68]" /><h2 className="mt-10 text-xl font-semibold">Live</h2><p className="mt-2 text-sm leading-6 text-stone-400">Updates during matches. Scores, bonus, and ranks can move.</p></div>
            <div className="bg-[#fffdf7] p-6 md:rounded-[0.75rem]"><Database size={24} className="text-[#1f6b4d]" /><h2 className="mt-10 text-xl font-semibold">Provisional</h2><p className="mt-2 text-sm leading-6 text-stone-600">Matches are complete, but official review has not finished.</p></div>
            <div className="bg-[#e9eee8] p-6 md:rounded-[0.75rem]"><ShieldCheck size={24} className="text-[#1f6b4d]" /><h2 className="mt-10 text-xl font-semibold">Final</h2><p className="mt-2 text-sm leading-6 text-stone-600">FPL has marked the event finished and data-checked.</p></div>
          </div>
        </section>

        <section className="mx-auto grid max-w-[1500px] gap-8 px-5 py-16 md:grid-cols-2 md:px-8 md:py-20">
          <div>
            <h2 className="text-2xl font-semibold">Public sources used</h2>
            <ul className="mt-5 divide-y divide-stone-950/10 border-y border-stone-950/10 font-mono text-xs text-stone-600">
              {endpoints.map((endpoint) => <li key={endpoint} className="py-3">/api/{endpoint}/</li>)}
            </ul>
          </div>
          <div>
            <h2 className="text-2xl font-semibold">Quality gates</h2>
            <ul className="mt-5 grid gap-3 text-sm leading-6 text-stone-600">
              <li>Exactly one active season.</li><li>38 events and 20 teams.</li><li>A plausible player count and a non-empty standings snapshot.</li><li>Explicit pipeline run status and freshness timestamps.</li><li>Content facts linked to their source snapshot.</li>
            </ul>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
