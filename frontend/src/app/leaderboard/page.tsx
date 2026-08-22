import { SiteFooter, SiteHeader } from "@/components/shell";
import { LeaderboardSearch } from "@/components/leaderboard-search";
import { getLiveLeaderboard, getLiveOverview } from "@/lib/api";

export const revalidate = 120;

export default async function LeaderboardPage() {
  const [leaderboard, overview] = await Promise.all([getLiveLeaderboard(100), getLiveOverview()]);
  const gw = overview.event?.event ?? 1;

  return (
    <>
      <SiteHeader />
      <main id="main-content" className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <div className="mb-8 max-w-4xl">
          <div className="mono-num mb-3 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">
            2026/27 · Gameweek {gw} · {leaderboard.snapshot?.is_complete ? "complete snapshot" : "bounded snapshot"}
          </div>
          <h1 className="text-4xl font-semibold leading-none tracking-tight md:text-6xl">
            Find your place in the latest Kenya table.
          </h1>
        </div>
        <p className="mb-8 max-w-2xl text-base leading-7 text-stone-600">
          Search the captured standings by team name, manager name, or FPL entry ID. Live rankings can move until the gameweek is final.
        </p>
        <LeaderboardSearch initialRows={leaderboard.rows} event={gw} />
      </main>
      <SiteFooter />
    </>
  );
}
