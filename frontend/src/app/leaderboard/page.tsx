import { SiteHeader } from "@/components/shell";
import { LeaderboardSearch } from "@/components/leaderboard-search";
import { getLeaderboard } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function LeaderboardPage() {
  const rows = await getLeaderboard(100);

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <div className="mb-8 max-w-4xl">
          <div className="mono-num mb-3 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">
            All 445,629 managers indexed
          </div>
          <h1 className="text-4xl font-semibold leading-none tracking-tight md:text-6xl">
            Search the Kenya leaderboard by team, manager, or FPL ID.
          </h1>
        </div>
        <LeaderboardSearch initialRows={rows} />
      </main>
    </>
  );
}
