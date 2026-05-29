import { CompactManagerTable } from "@/components/insight-tables";
import { SiteHeader, StatBlock } from "@/components/shell";
import { getStories } from "@/lib/api";
import { managerIdentity, primaryManagerName, secondaryManagerName } from "@/lib/display";

export const dynamic = "force-dynamic";

const nf = new Intl.NumberFormat("en-US");

function StoryCounts({ rows }: { rows: Array<Record<string, string | number>> }) {
  return (
    <div className="panel rounded-lg p-5">
      <div className="mb-4 text-sm font-semibold">Season arc taxonomy</div>
      <div className="divide-y divide-stone-950/10">
        {rows.map((row) => (
          <div key={String(row.story_type)} className="grid grid-cols-[1fr_auto] gap-4 py-3">
            <div>
              <div className="font-semibold">{row.story_type}</div>
              <div className="text-xs text-stone-500">
                avg total {row.avg_total}, avg range {row.avg_journey_range}
              </div>
            </div>
            <div className="mono-num text-right font-semibold">{nf.format(Number(row.managers))}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SwingTable({
  title,
  rows,
}: {
  title: string;
  rows: Array<Record<string, string | number>>;
}) {
  return (
    <div className="panel rounded-lg">
      <div className="border-b border-stone-950/10 p-5">
        <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
      </div>
      <div className="divide-y divide-stone-950/10">
        {rows.slice(0, 12).map((row) => (
          <div key={`${row.entry}-${row.event}`} className="grid grid-cols-[4rem_1fr_auto] gap-3 px-5 py-3 text-sm">
            <span className="mono-num text-stone-500">GW{row.event}</span>
            <span className="min-w-0">
              <span className="block truncate font-semibold">{primaryManagerName(row)}</span>
              <span className="block text-xs text-stone-500">
                {secondaryManagerName(row)} · #{nf.format(Number(row.previous_kenya_rank))} to #
                {nf.format(Number(row.kenya_rank))}
              </span>
            </span>
            <span className="mono-num text-right font-semibold">
              {Number(row.rank_gain) > 0 ? "+" : ""}
              {nf.format(Number(row.rank_gain))}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default async function StoriesPage() {
  const stories = await getStories();
  const biggestComeback = stories.comeback[0];
  const biggestCollapse = stories.collapses[0];
  const biggestJump = stories.swingsUp[0];

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <div className="mb-10 max-w-5xl">
          <div className="mono-num mb-3 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">
            Derived from weekly Kenya ranks
          </div>
          <h1 className="text-4xl font-semibold leading-none tracking-tight sm:text-5xl md:text-7xl">
            Season movement across 445,629 managers.
          </h1>
        </div>

        <section className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <StatBlock
            label="Biggest GW20 comeback"
            value={nf.format(Number(biggestComeback?.comeback_after_gw20 ?? 0))}
            detail={managerIdentity(biggestComeback)}
          />
          <StatBlock
            label="Biggest post-GW10 collapse"
            value={nf.format(Number(biggestCollapse?.collapse_after_gw10 ?? 0))}
            detail={managerIdentity(biggestCollapse)}
          />
          <StatBlock
            label="Largest one-week climb"
            value={nf.format(Number(biggestJump?.rank_gain ?? 0))}
            detail={`GW${biggestJump?.event ?? "-"}`}
          />
        </section>

        <section className="mt-16 grid grid-cols-1 gap-5 lg:grid-cols-[0.4fr_0.6fr]">
          <StoryCounts rows={stories.counts} />
          <div className="grid grid-cols-1 gap-5">
            <SwingTable title="Biggest one-week climbs" rows={stories.swingsUp} />
            <SwingTable title="Biggest one-week drops" rows={stories.swingsDown} />
          </div>
        </section>

        <section className="mt-16 grid grid-cols-1 gap-5 lg:grid-cols-3">
          <CompactManagerTable title="Comeback Kings" rows={stories.comeback} metricLabel="gain" metricKey="comeback_after_gw20" />
          <CompactManagerTable title="Late Chargers" rows={stories.lateChargers} metricLabel="run-in" metricKey="run_in_gain" />
          <CompactManagerTable title="Early Collapses" rows={stories.collapses} metricLabel="drop" metricKey="collapse_after_gw10" />
        </section>
      </main>
    </>
  );
}
