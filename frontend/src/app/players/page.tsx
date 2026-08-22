import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/shell";
import { getLivePlayers } from "@/lib/api";

export const metadata: Metadata = {
  title: "Player watch",
  description: "Live FPL player points, ownership, transfers, defensive contributions, and price signals for 2026/27.",
};
export const revalidate = 120;

const sorts = [
  ["points", "Live points"],
  ["transfers", "Transfers"],
  ["ownership", "Ownership"],
  ["defensive", "Defensive work"],
  ["bps", "BPS"],
] as const;

const nf = new Intl.NumberFormat("en-KE");

export default async function PlayersPage({ searchParams }: { searchParams: Promise<{ sort?: string }> }) {
  const requested = (await searchParams).sort ?? "points";
  const sort = sorts.some(([value]) => value === requested) ? requested : "points";
  const data = await getLivePlayers(sort, 100);

  return (
    <>
      <SiteHeader />
      <main id="main-content" className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <div className="max-w-5xl">
          <div className="font-mono text-xs uppercase tracking-[0.22em] text-[#1f6b4d]">2026/27 · GW{data.event}</div>
          <h1 className="mt-4 text-balance text-5xl font-semibold leading-[0.95] tracking-[-0.045em] md:text-7xl">Player watch.</h1>
          <p className="mt-6 max-w-[65ch] text-lg leading-8 text-stone-600">
            Live scoring, transfer pressure, ownership, bonus performance, and defensive contributions from the current player pool.
          </p>
        </div>

        <nav aria-label="Sort players" className="my-9 flex gap-2 overflow-x-auto pb-2">
          {sorts.map(([value, label]) => (
            <Link
              key={value}
              href={`/players?sort=${value}`}
              aria-current={sort === value ? "page" : undefined}
              className={`shrink-0 rounded-md px-4 py-2.5 text-sm font-semibold transition active:translate-y-px ${
                sort === value ? "bg-stone-950 text-[#fffdf7]" : "border border-stone-950/10 bg-[#fffdf7] hover:border-stone-950/30"
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>

        <div className="panel overflow-x-auto rounded-[0.75rem]">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="border-b border-stone-950/10 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-stone-500">
              <tr>
                <th className="px-5 py-4 font-medium">Player</th>
                <th className="px-5 py-4 font-medium">Club</th>
                <th className="px-5 py-4 text-right font-medium">Price</th>
                <th className="px-5 py-4 text-right font-medium">GW pts</th>
                <th className="px-5 py-4 text-right font-medium">Minutes</th>
                <th className="px-5 py-4 text-right font-medium">BPS</th>
                <th className="px-5 py-4 text-right font-medium">Def con</th>
                <th className="px-5 py-4 text-right font-medium">Owned</th>
                <th className="px-5 py-4 text-right font-medium">Net transfers</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-950/10">
              {data.rows.map((player) => (
                <tr key={player.element} className="transition hover:bg-white">
                  <td className="px-5 py-4">
                    <div className="font-semibold">{player.web_name}</div>
                    <div className="mt-1 text-xs text-stone-500">{player.status === "a" ? "Available" : player.status}</div>
                  </td>
                  <td className="px-5 py-4 text-stone-600">{player.short_name}</td>
                  <td className="px-5 py-4 text-right font-mono">£{(player.now_cost / 10).toFixed(1)}</td>
                  <td className="px-5 py-4 text-right font-mono text-base font-semibold">{player.live_points ?? player.event_points}</td>
                  <td className="px-5 py-4 text-right font-mono">{player.minutes ?? 0}</td>
                  <td className="px-5 py-4 text-right font-mono">{player.bps ?? 0}</td>
                  <td className="px-5 py-4 text-right font-mono">{player.live_defensive_contribution ?? player.defensive_contribution ?? 0}</td>
                  <td className="px-5 py-4 text-right font-mono">{player.selected_by_percent}%</td>
                  <td className="px-5 py-4 text-right font-mono">
                    {nf.format((player.transfers_in_event ?? 0) - (player.transfers_out_event ?? 0))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-5 max-w-3xl text-xs leading-5 text-stone-500">
          Live bonus and player totals can change during matches and remain subject to the official post-gameweek review.
        </p>
      </main>
      <SiteFooter />
    </>
  );
}
