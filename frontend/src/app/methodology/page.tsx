import { Database, GitBranch, HardDrives, ShieldCheck } from "@phosphor-icons/react/dist/ssr";
import { SiteHeader, StatBlock } from "@/components/shell";

export const dynamic = "force-dynamic";

const endpoints = [
  {
    label: "Static game data",
    path: "/api/bootstrap-static/",
    detail: "Players, teams, events, positions, prices, ownership, and season metadata.",
  },
  {
    label: "Fixtures",
    path: "/api/fixtures/",
    detail: "Fixture list and metadata used alongside player and gameweek context.",
  },
  {
    label: "Event live data",
    path: "/api/event/{event}/live/",
    detail: "Live player scores for every gameweek from GW1 to GW38.",
  },
  {
    label: "Player summaries",
    path: "/api/element-summary/{element}/",
    detail: "Per-player fixtures, current-season history, and past-season history.",
  },
  {
    label: "Kenya standings",
    path: "/api/leagues-classic/131/standings/?page_standings={page}",
    detail: "Paged country-league standings. This is the source of the 445,629 Kenyan manager entries.",
  },
  {
    label: "Manager profile",
    path: "/api/entry/{entry}/",
    detail: "Public manager metadata, region, favourite team, overall rank, and summary points.",
  },
  {
    label: "Manager history",
    path: "/api/entry/{entry}/history/",
    detail: "Public gameweek-by-gameweek manager performance, including points, total points, value, transfers, and bench points.",
  },
];

const storedTables = [
  "raw_api_responses",
  "fpl_bootstrap_snapshots",
  "fixtures_snapshots",
  "event_live",
  "element_summaries",
  "kenya_standings",
  "managers",
  "manager_history",
  "manager_gw_history",
];

const derivedViews = [
  "mv_gameweek_summary",
  "mv_points_distribution",
  "mv_rank_band_summary",
  "mv_manager_metrics",
  "mv_gameweek_extremes",
  "mv_rank_band_gameweeks",
  "mv_percentile_ladder",
  "mv_favorite_team_summary",
  "mv_bench_pain_hall",
  "mv_weekly_explosions",
  "mv_rank_race_top50",
  "mv_scatter_lab_sample",
  "mv_club_gameweek_profile",
  "mv_weekly_kenya_ranks",
  "mv_weekly_rank_swings",
  "mv_manager_phase_splits",
  "mv_season_stories",
];

function MethodBlock({
  title,
  body,
  icon: Icon,
}: {
  title: string;
  body: string;
  icon: typeof Database;
}) {
  return (
    <section className="border-t border-stone-950/12 pt-5">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <Icon size={18} className="text-[#1f6b4d]" />
        {title}
      </div>
      <p className="max-w-3xl text-sm leading-7 text-stone-600">{body}</p>
    </section>
  );
}

export default function MethodologyPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <div className="mb-12 max-w-5xl">
          <div className="mono-num mb-3 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">
            Data collection
          </div>
          <h1 className="text-4xl font-semibold leading-none tracking-tight sm:text-5xl md:text-7xl">
            How the FPL Kenya dataset was collected and processed.
          </h1>
          <p className="mt-6 max-w-3xl text-lg leading-8 text-stone-600">
            This page documents the public Fantasy Premier League API sources, the collection jobs,
            the database model, and the derived analytics used in the dashboard.
          </p>
        </div>

        <section className="grid grid-cols-1 gap-5 md:grid-cols-4">
          <StatBlock label="Kenyan managers" value="445,629" detail="country league 131" />
          <StatBlock label="Manager gameweek rows" value="15,543,473" detail="from public season histories" />
          <StatBlock label="Player summaries" value="841" detail="all bootstrap elements" />
          <StatBlock label="FPL events" value="38" detail="event live snapshots" />
        </section>

        <section className="mt-16 grid grid-cols-1 gap-10 lg:grid-cols-[0.42fr_0.58fr]">
          <div className="space-y-10">
            <MethodBlock
              icon={Database}
              title="Source"
              body="All data comes from public Fantasy Premier League endpoints. No private user authentication, team picks, private leagues, or transfer histories are required for the current dashboard."
            />
            <MethodBlock
              icon={GitBranch}
              title="Collection strategy"
              body="The collector first loads static FPL metadata, then pages through the Kenya country league standings. Each manager entry is used to fetch the public manager profile and season history. Requests are asynchronous, rate-limited, retried on transient failures, and stored with the raw response payload."
            />
            <MethodBlock
              icon={HardDrives}
              title="Storage"
              body="Postgres stores both normalized analysis columns and the original JSONB payloads. This keeps the project reproducible: derived tables can be rebuilt without asking the FPL API again."
            />
            <MethodBlock
              icon={ShieldCheck}
              title="Limitations"
              body="The dataset reflects public FPL data available at collection time. FPL may reset public team names, hide private data, or change public endpoint behavior. Names such as Restored are treated as FPL-side reset placeholders in the interface."
            />
          </div>

          <div className="space-y-5">
            <section className="panel rounded-lg">
              <div className="border-b border-stone-950/10 p-5">
                <h2 className="text-xl font-semibold tracking-tight">Public API endpoints used</h2>
              </div>
              <div className="divide-y divide-stone-950/10">
                {endpoints.map((endpoint) => (
                  <div key={endpoint.path} className="grid gap-2 p-5 md:grid-cols-[13rem_1fr]">
                    <div>
                      <div className="text-sm font-semibold">{endpoint.label}</div>
                      <div className="mono-num mt-1 break-all text-xs text-[#1f6b4d]">{endpoint.path}</div>
                    </div>
                    <p className="text-sm leading-6 text-stone-600">{endpoint.detail}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div className="panel rounded-lg p-5">
                <h2 className="mb-4 text-lg font-semibold tracking-tight">Stored tables</h2>
                <div className="flex flex-wrap gap-2">
                  {storedTables.map((table) => (
                    <span key={table} className="mono-num rounded-md border border-stone-950/10 px-2.5 py-1 text-xs text-stone-600">
                      {table}
                    </span>
                  ))}
                </div>
              </div>
              <div className="panel rounded-lg p-5">
                <h2 className="mb-4 text-lg font-semibold tracking-tight">Derived views</h2>
                <div className="flex flex-wrap gap-2">
                  {derivedViews.map((view) => (
                    <span key={view} className="mono-num rounded-md border border-stone-950/10 px-2.5 py-1 text-xs text-stone-600">
                      {view}
                    </span>
                  ))}
                </div>
              </div>
            </section>
          </div>
        </section>
      </main>
    </>
  );
}
