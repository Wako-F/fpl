const API_BASE =
  process.env.FPLKE_API_BASE ?? "http://38.242.228.254/fplke-data";
export const DATA_REVALIDATE_SECONDS = 86_400;
export const LIVE_REVALIDATE_SECONDS = 120;

export type LiveOverview = {
  season: {
    id: string;
    label: string;
    is_active: boolean;
  };
  event: null | {
    event: number;
    name: string;
    deadline_time: string;
    finished: boolean;
    data_checked: boolean;
    average_entry_score: number | null;
    highest_score: number | null;
  };
  snapshot: null | {
    id: number;
    captured_at: string;
    is_complete: boolean;
    pages_collected: number;
    managers_collected: number;
  };
  summary: null | {
    managers: number;
    min_points: number;
    max_points: number;
    avg_points: string;
    median_points: string;
    p90_points: string;
    p99_points: string;
  };
  cohort: {
    managers: number;
    avg_points: string | null;
    median_points: string | null;
    max_points: number | null;
    avg_bench_points: string | null;
    avg_transfer_cost: string | null;
  };
  leaders: LeaderboardRow[];
  topPlayers: LivePlayer[];
  fixtures: Fixture[];
};

export type LivePlayer = {
  element: number;
  web_name: string;
  short_name: string;
  total_points: number;
  minutes: number;
  goals_scored: number;
  assists: number;
  bonus: number;
  bps: number;
  defensive_contribution: number;
};

export type Fixture = {
  fixture_id: number;
  event: number;
  kickoff_time: string;
  finished: boolean;
  started: boolean;
  team_h_name: string;
  team_h_short: string;
  team_h_score: number | null;
  team_a_name: string;
  team_a_short: string;
  team_a_score: number | null;
};

export type LeaderboardSnapshot = {
  snapshot: LiveOverview["snapshot"];
  rows: LeaderboardRow[];
};

export type PlayerExplorer = {
  season: string;
  event: number;
  sort: string;
  rows: Array<{
    element: number;
    web_name: string;
    first_name: string;
    second_name: string;
    team_name: string;
    short_name: string;
    element_type: number;
    now_cost: number;
    status: string;
    selected_by_percent: string;
    total_points: number;
    event_points: number;
    form: string;
    live_points: number | null;
    minutes: number | null;
    bonus: number | null;
    bps: number | null;
    live_defensive_contribution: number | null;
    defensive_contribution: number | null;
    transfers_in_event: number;
    transfers_out_event: number;
    price_change_projection: unknown;
  }>;
};

export type WeeklyContent = {
  season: string;
  event: number;
  facts: Record<
    string,
    {
      status: "live" | "provisional" | "final";
      value: Record<string, unknown> | Array<Record<string, unknown>> | null;
      cohort: string;
      sample_size: number;
      calculated_at: string;
      methodology: string;
      source_snapshot_id: number;
    }
  >;
};

export type OpsStatus = {
  season: string;
  event: null | {
    event: number;
    name: string;
    deadline_time: string;
    finished: boolean;
    data_checked: boolean;
    average_entry_score: number | null;
    highest_score: number | null;
    ranked_count: number | null;
    updated_at: string;
  };
  published_snapshot: null | {
    id: number;
    event: number;
    captured_at: string;
    is_complete: boolean;
    pages_collected: number;
    managers_collected: number;
    crawl_mode: "bounded" | "full";
    crawl_status: "running" | "finished" | "failed";
    expected_pages: number | null;
    expected_rows: number | null;
    rows_fetched: number;
    duplicate_rows: number;
  };
  full_crawl: null | {
    id: number;
    event: number;
    crawl_mode: "full";
    crawl_status: "running" | "finished" | "failed";
    started_at: string;
    finished_at: string | null;
    last_heartbeat_at: string | null;
    expected_pages: number | null;
    expected_rows: number | null;
    pages_collected: number;
    managers_collected: number;
    rows_fetched: number;
    duplicate_rows: number;
    is_complete: boolean;
    progress: null | {
      scheduled_pages: number;
      finished_pages: number;
      running_pages: number;
      failed_pages: number;
      rows_fetched: number;
      avg_page_ms: number | null;
      latest_page_at: string | null;
    };
  };
  freshness: {
    live_players: string | null;
    bootstrap: string | null;
    fixtures: string | null;
    standings: string | null;
  };
  quality: Array<{
    check_name: string;
    status: "pass" | "warn" | "fail";
    observed_value: string | null;
    expected_value: string | null;
    checked_at: string;
  }>;
  runs: Array<{
    id: number;
    job_name: string;
    status: "running" | "finished" | "failed";
    started_at: string;
    finished_at: string | null;
    duration_seconds: number;
    has_error: boolean;
  }>;
  content_packs: Array<{
    event: number;
    calculated_at: string;
    facts: number;
    status: "live" | "provisional" | "final";
    source_snapshot_id: number;
    largest_sample: number;
    artifacts: Array<{
      key: "article" | "analysis" | "social" | "engineering" | "brief" | "manifest" | "decision-dashboard" | "score-distribution" | "captaincy" | "top-players" | "rank-movers";
      filename: string;
      bytes: number;
      modified_at: string;
    }>;
  }>;
  content_coverage: Array<{
    event: number;
    finished: boolean;
    data_checked: boolean;
    selected_managers: number;
    history_managers: number;
    picks_managers: number;
    facts: number;
    content_updated_at: string | null;
    has_final_content: boolean;
    ready: boolean;
    artifacts: Array<{
      key: string;
      filename: string;
      bytes: number;
      modified_at: string;
    }>;
  }>;
};

export type ContentArtifact = {
  season: string;
  event: number;
  artifact: string;
  filename: string;
  bytes: number;
  modified_at: string;
  content: string;
};

export type LiveManagerDetail = {
  season: string;
  manager: LeaderboardRow & {
    player_region_name: string | null;
    summary_overall_rank: number | null;
    summary_overall_points: number | null;
    favourite_team: number | null;
  };
  metrics: null | {
    gameweeks: number;
    avg_points: string;
    volatility: string | null;
    best_week: number;
    worst_week: number;
    bench_points: number;
    transfer_cost: number;
    avg_team_value: string;
  };
  history: ManagerDetail["history"];
  chips: Array<{ chip_name: string; event: number }>;
};

export type Overview = {
  summary: {
    managers: number;
    min_points: number;
    max_points: number;
    avg_points: string;
    median_points: string;
    p90_points: string;
    p99_points: string;
  };
  distribution: Array<{
    bucket: number;
    min_points: number;
    max_points: number;
    managers: number;
  }>;
  gameweeks: GameweekSummary[];
  rankBands: RankBand[];
};

export type GameweekSummary = {
  event: number;
  managers: number;
  avg_points: string;
  median_points: string;
  max_points: number;
  min_points?: number;
  volatility: string;
  avg_bench_points: string;
  avg_transfer_cost: string;
  p90_points: string;
  p10_points: string;
};

export type RankBand = {
  band: string;
  managers: number;
  avg_total: string;
  median_total: string;
  avg_weekly_points: string;
  avg_bench_points: string;
  avg_transfer_cost: string;
  avg_team_value: string;
};

export type LeaderboardRow = {
  entry: number;
  entry_name: string;
  player_name: string;
  rank: number;
  last_rank: number;
  total: number;
  event_total: number;
  rank_gain?: number;
};

export type ManagerDetail = {
  manager: null | {
    entry: number;
    entry_name: string;
    player_name: string;
    rank: number;
    last_rank: number;
    total: number;
    event_total: number;
    player_region_name: string;
    summary_overall_rank: number;
    summary_overall_points: number;
  };
  stats: null | {
    avg_points: string;
    volatility: string;
    best_week: number;
    worst_week: number;
    bench_points: number;
    transfer_cost: number;
    avg_team_value: string;
  };
  metrics: null | {
    archetype: string;
    avg_points: string;
    volatility: string;
    bench_points: number;
    avg_bench_points: string;
    transfer_cost: number;
    avg_team_value: string;
    max_team_value: string;
    consistency_ratio: string;
    points_per_million: string;
  };
  similar: Array<{
    entry: number;
    entry_name: string;
    player_name: string;
    rank: number;
    total: number;
    archetype: string;
    avg_points: string;
    volatility: string;
    bench_points: number;
    distance: string;
  }>;
  history: Array<{
    event: number;
    points: number;
    total_points: number;
    overall_rank: number;
    bank: number;
    value: number;
    event_transfers: number;
    event_transfers_cost: number;
    points_on_bench: number;
  }>;
};

export type Lab = {
  benchPain: Array<Record<string, string | number>>;
  explosions: Array<Record<string, string | number>>;
  scatter: Array<Record<string, string | number>>;
  race: Array<{
    entry: number;
    entry_name: string;
    player_name: string;
    final_rank: number;
    event: number;
    total_points: number;
    points: number;
  }>;
};

export type ClubDetail = {
  club: null | {
    team_id: number;
    team_name: string;
    short_name: string;
    managers: number;
    share_pct: string;
    avg_total: string;
    median_total: string;
    best_rank: number;
    avg_weekly_points: string;
    avg_volatility: string;
    avg_bench_points: string;
    avg_transfer_cost: string;
  };
  gameweeks: GameweekSummary[];
  leaders: LeaderboardRow[];
};

export type Stories = {
  counts: Array<Record<string, string | number>>;
  comeback: Array<Record<string, string | number>>;
  lateChargers: Array<Record<string, string | number>>;
  collapses: Array<Record<string, string | number>>;
  swingsUp: Array<Record<string, string | number>>;
  swingsDown: Array<Record<string, string | number>>;
};

export type Insights = {
  archetypes: Array<{
    archetype: string;
    managers: number;
    avg_total: string;
    avg_weekly_points: string;
    avg_volatility: string;
    avg_bench_points: string;
  }>;
  consistency: Array<{
    entry: number;
    entry_name: string;
    player_name: string;
    rank: number;
    total: number;
    avg_points: string;
    volatility: string;
    consistency_ratio: string;
    bench_points: number;
  }>;
  efficiency: Array<{
    entry: number;
    entry_name: string;
    player_name: string;
    rank: number;
    total: number;
    points_per_million: string;
    avg_team_value: string;
    transfer_cost: number;
  }>;
  percentiles: Array<{
    label: string;
    percentile: string;
    points: number;
  }>;
  extremes: Array<{
    event: number;
    top_scores: Array<{
      entry: number;
      entry_name: string;
      player_name: string;
      final_rank: number;
      points: number;
    }>;
    bench_pain: Array<{
      entry: number;
      entry_name: string;
      player_name: string;
      final_rank: number;
      points_on_bench: number;
    }>;
  }>;
  rankBandGameweeks: Array<{
    band: string;
    event: number;
    managers: number;
    avg_points: string;
    avg_bench_points: string;
    avg_transfer_cost: string;
    avg_team_value: string;
  }>;
  favoriteTeams: Array<{
    team_id: number;
    team_name: string;
    short_name: string;
    managers: number;
    share_pct: string;
    avg_total: string;
    median_total: string;
    best_rank: number;
    avg_weekly_points: string;
    avg_volatility: string;
    avg_bench_points: string;
    avg_transfer_cost: string;
  }>;
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: DATA_REVALIDATE_SECONDS },
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${path}`);
  }
  return response.json() as Promise<T>;
}

async function getLiveJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: LIVE_REVALIDATE_SECONDS },
  });
  if (!response.ok) {
    throw new Error(`Live API request failed: ${response.status} ${path}`);
  }
  return response.json() as Promise<T>;
}

export function getLiveOverview() {
  return getLiveJson<LiveOverview>("/v2/overview");
}

export function getLiveLeaderboard(limit = 100, q = "") {
  const params = new URLSearchParams({ limit: String(limit) });
  if (q) params.set("q", q);
  return getLiveJson<LeaderboardSnapshot>(`/v2/leaderboard?${params}`);
}

export function getLivePlayers(sort = "points", limit = 100) {
  return getLiveJson<PlayerExplorer>(`/v2/players?sort=${encodeURIComponent(sort)}&limit=${limit}`);
}

export function getLiveManager(entry: string) {
  return getLiveJson<LiveManagerDetail>(`/v2/managers/${entry}`);
}

export function getWeeklyContent(event: number) {
  return getLiveJson<WeeklyContent>(`/v2/gameweeks/${event}/content`);
}

export function getOpsStatus() {
  return getLiveJson<OpsStatus>("/v2/ops");
}

export function getContentArtifact(event: number, artifact: string) {
  return getLiveJson<ContentArtifact>(
    `/v2/content-packs/${event}/${encodeURIComponent(artifact)}`,
  );
}

export function getOverview() {
  return getJson<Overview>("/overview");
}

export function getLeaderboard(limit = 100) {
  return getJson<LeaderboardRow[]>(`/leaderboard?limit=${limit}`);
}

export function getManager(entry: string) {
  return getJson<ManagerDetail>(`/managers/${entry}`);
}

export function getInsights() {
  return getJson<Insights>("/insights");
}

export function getLab() {
  return getJson<Lab>("/lab");
}

export function getClub(teamId: string) {
  return getJson<ClubDetail>(`/clubs/${teamId}`);
}

export function getArchetype(slug: string) {
  return getJson<Array<Record<string, string | number>>>(`/archetypes/${slug}`);
}

export function getStories() {
  return getJson<Stories>("/stories");
}

export const apiBase = API_BASE;
