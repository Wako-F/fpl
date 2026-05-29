const API_BASE = process.env.FPLKE_API_BASE ?? "http://127.0.0.1:8010";

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
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${path}`);
  }
  return response.json() as Promise<T>;
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
