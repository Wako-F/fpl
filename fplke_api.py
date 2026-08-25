import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from redis.asyncio import Redis


DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CONTENT_ROOT = Path(os.environ.get("FPLKE_CONTENT_DIR", "content/generated"))

db_pool: asyncpg.Pool | None = None
redis_client: Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=12, command_timeout=60)
    redis_client = Redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield
    finally:
        await db_pool.close()
        await redis_client.aclose()


app = FastAPI(title="FPL Kenya Data API", lifespan=lifespan)


def pool() -> asyncpg.Pool:
    if db_pool is None:
        raise RuntimeError("database pool is not initialized")
    return db_pool


def redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("redis client is not initialized")
    return redis_client


async def cached(key: str, ttl: int, loader):
    client = redis()
    try:
        cached_value = await client.get(key)
        if cached_value:
            return json.loads(cached_value)
    except Exception:
        # The database remains authoritative; Redis is an acceleration layer.
        cached_value = None
    value = await loader()
    try:
        await client.setex(key, ttl, json.dumps(jsonable_encoder(value), separators=(",", ":")))
    except Exception:
        pass
    return value


async def fetchrow(query: str, *args):
    async with pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def resolve_season(season: str | None) -> str:
    if season and season != "active":
        value = await pool().fetchval("SELECT id FROM seasons WHERE id=$1", season)
    else:
        value = await pool().fetchval("SELECT id FROM seasons WHERE is_active LIMIT 1")
    if not value:
        raise HTTPException(status_code=404, detail="Season not found")
    return value


@app.get("/health")
async def health():
    row = await fetchrow("SELECT now() AS now")
    return {"ok": True, "database_time": row["now"].isoformat()}


@app.get("/status")
async def status():
    row = await fetchrow(
        """
        SELECT
            (SELECT count(*) FROM kenya_standings) AS kenya_standings_rows,
            (SELECT count(*) FROM managers) AS managers_rows,
            (SELECT count(*) FROM manager_history) AS manager_history_rows,
            (SELECT count(*) FROM manager_transfers) AS manager_transfers_rows,
            (SELECT count(*) FROM manager_picks) AS manager_picks_rows,
            (SELECT count(*) FROM event_live) AS event_live_rows,
            (SELECT count(*) FROM element_summaries) AS element_summaries_rows,
            (SELECT max(fetched_at) FROM raw_api_responses) AS last_raw_fetch
        """
    )
    return dict(row)


@app.get("/overview")
async def overview():
    async def load():
        async with pool().acquire() as conn:
            summary = await conn.fetchrow(
                """
                SELECT
                    count(*)::integer AS managers,
                    min(total)::integer AS min_points,
                    max(total)::integer AS max_points,
                    round(avg(total), 2) AS avg_points,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS median_points,
                    percentile_cont(0.9) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS p90_points,
                    percentile_cont(0.99) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS p99_points
                FROM kenya_standings
                WHERE league_id = 131
                """
            )
            distribution = await conn.fetch(
                """
                SELECT bucket, min_points, max_points, managers
                FROM mv_points_distribution
                ORDER BY bucket
                """
            )
            gameweeks = await conn.fetch(
                """
                SELECT event, managers, avg_points, median_points, max_points, volatility,
                       avg_bench_points, avg_transfer_cost, p90_points, p10_points
                FROM mv_gameweek_summary
                ORDER BY event
                """
            )
            bands = await conn.fetch(
                """
                SELECT band, managers, avg_total, median_total, avg_weekly_points,
                       avg_bench_points, avg_transfer_cost, avg_team_value
                FROM mv_rank_band_summary
                ORDER BY CASE band
                    WHEN 'Top 100' THEN 1
                    WHEN 'Top 1K' THEN 2
                    WHEN 'Top 1%' THEN 3
                    WHEN 'Top 5%' THEN 4
                    WHEN 'Top 10%' THEN 5
                    WHEN 'Median' THEN 6
                    ELSE 99
                END
                """
            )
            return {
                "summary": dict(summary),
                "distribution": [dict(row) for row in distribution],
                "gameweeks": [dict(row) for row in gameweeks],
                "rankBands": [dict(row) for row in bands],
            }

    return await cached("overview:v1", 21600, load)


@app.get("/leaderboard")
async def leaderboard(limit: int = 50):
    limit = max(1, min(limit, 500))
    async def load():
        async with pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, rank, last_rank, total, event_total
                FROM kenya_standings
                WHERE league_id = 131
                ORDER BY rank NULLS LAST
                LIMIT $1
                """,
                limit,
            )
            return [dict(row) for row in rows]

    return await cached(f"leaderboard:{limit}:v1", 3600, load)


@app.get("/leaderboard/search")
async def leaderboard_search(q: str = "", limit: int = 50):
    limit = max(1, min(limit, 500))
    q = q.strip()
    async def load():
        async with pool().acquire() as conn:
            if q:
                rows = await conn.fetch(
                    """
                    SELECT entry, entry_name, player_name, rank, last_rank, total, event_total
                    FROM kenya_standings
                    WHERE league_id = 131
                      AND (entry_name ILIKE '%' || $1 || '%' OR player_name ILIKE '%' || $1 || '%' OR entry::text = $1)
                    ORDER BY rank NULLS LAST
                    LIMIT $2
                    """,
                    q,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT entry, entry_name, player_name, rank, last_rank, total, event_total
                    FROM kenya_standings
                    WHERE league_id = 131
                    ORDER BY rank NULLS LAST
                    LIMIT $1
                    """,
                    limit,
                )
            return [dict(row) for row in rows]

    return await cached(f"leaderboard-search:{q}:{limit}:v1", 600, load)


@app.get("/managers/{entry}")
async def manager_detail(entry: int):
    async def load():
        async with pool().acquire() as conn:
            manager = await conn.fetchrow(
                """
                SELECT ks.entry, ks.entry_name, ks.player_name, ks.rank, ks.last_rank, ks.total, ks.event_total,
                       m.player_region_name, m.summary_overall_rank, m.summary_overall_points
                FROM kenya_standings ks
                LEFT JOIN managers m ON m.entry = ks.entry
                WHERE ks.league_id = 131 AND ks.entry = $1
                """,
                entry,
            )
            if not manager:
                return {"manager": None, "history": []}
            history = await conn.fetch(
                """
                SELECT event, points, total_points, overall_rank, bank, value,
                       event_transfers, event_transfers_cost, points_on_bench
                FROM manager_gw_history
                WHERE entry = $1
                ORDER BY event
                """,
                entry,
            )
            stats = await conn.fetchrow(
                """
                SELECT
                    round(avg(points), 2) AS avg_points,
                    round(stddev_pop(points), 2) AS volatility,
                    max(points)::integer AS best_week,
                    min(points)::integer AS worst_week,
                    sum(points_on_bench)::integer AS bench_points,
                    sum(event_transfers_cost)::integer AS transfer_cost,
                    round(avg(value) / 10.0, 2) AS avg_team_value
                FROM manager_gw_history
                WHERE entry = $1
                """,
                entry,
            )
            metrics = await conn.fetchrow(
                """
                SELECT archetype, avg_points, volatility, bench_points, avg_bench_points,
                       transfer_cost, avg_team_value, max_team_value, consistency_ratio,
                       points_per_million
                FROM mv_manager_metrics
                WHERE entry = $1
                """,
                entry,
            )
            similar = await conn.fetch(
                """
                WITH target AS (
                    SELECT total, avg_points, volatility, bench_points, transfer_cost, avg_team_value
                    FROM mv_manager_metrics
                    WHERE entry = $1
                )
                SELECT mm.entry, mm.entry_name, mm.player_name, mm.rank, mm.total,
                       mm.archetype, mm.avg_points, mm.volatility, mm.bench_points,
                       round(
                           abs(mm.total - target.total) / 50.0
                         + abs(mm.avg_points - target.avg_points)
                         + abs(mm.volatility - target.volatility)
                         + abs(mm.bench_points - target.bench_points) / 30.0
                         + abs(mm.transfer_cost - target.transfer_cost) / 8.0
                         + abs(mm.avg_team_value - target.avg_team_value),
                         2
                       ) AS distance
                FROM mv_manager_metrics mm
                CROSS JOIN target
                WHERE mm.entry <> $1
                ORDER BY distance ASC, mm.rank ASC
                LIMIT 8
                """,
                entry,
            )
            return {
                "manager": dict(manager),
                "stats": dict(stats),
                "metrics": dict(metrics) if metrics else None,
                "similar": [dict(row) for row in similar],
                "history": [dict(row) for row in history],
            }

    return await cached(f"manager:{entry}:v1", 86400, load)


@app.get("/gameweeks")
async def gameweeks():
    async def load():
        async with pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event, managers, avg_points, median_points, max_points, min_points,
                       volatility, avg_bench_points, avg_transfer_cost, p90_points, p10_points
                FROM mv_gameweek_summary
                ORDER BY event
                """
            )
            return [dict(row) for row in rows]

    return await cached("gameweeks:v1", 21600, load)


@app.get("/insights")
async def insights():
    async def load():
        async with pool().acquire() as conn:
            archetypes = await conn.fetch(
                """
                SELECT archetype, count(*)::integer AS managers,
                       round(avg(total), 2) AS avg_total,
                       round(avg(avg_points), 2) AS avg_weekly_points,
                       round(avg(volatility), 2) AS avg_volatility,
                       round(avg(bench_points), 2) AS avg_bench_points
                FROM mv_manager_metrics
                GROUP BY archetype
                ORDER BY managers DESC
                """
            )
            consistency = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, rank, total, avg_points, volatility,
                       consistency_ratio, bench_points
                FROM mv_manager_metrics
                WHERE weeks >= 30
                ORDER BY consistency_ratio DESC NULLS LAST, rank ASC
                LIMIT 25
                """
            )
            efficiency = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, rank, total, points_per_million,
                       avg_team_value, transfer_cost
                FROM mv_manager_metrics
                WHERE weeks >= 30 AND avg_team_value > 0
                ORDER BY points_per_million DESC NULLS LAST, rank ASC
                LIMIT 25
                """
            )
            percentiles = await conn.fetch(
                """
                SELECT label, percentile, points
                FROM mv_percentile_ladder
                ORDER BY percentile DESC
                """
            )
            extremes = await conn.fetch(
                """
                SELECT event, top_scores, bench_pain
                FROM mv_gameweek_extremes
                ORDER BY event
                """
            )
            rank_band_gameweeks = await conn.fetch(
                """
                SELECT band, event, managers, avg_points, avg_bench_points,
                       avg_transfer_cost, avg_team_value
                FROM mv_rank_band_gameweeks
                ORDER BY CASE band
                    WHEN 'Top 100' THEN 1
                    WHEN 'Top 1K' THEN 2
                    WHEN 'Top 1%' THEN 3
                    WHEN 'Top 5%' THEN 4
                    WHEN 'Top 10%' THEN 5
                    WHEN 'Median' THEN 6
                    ELSE 99
                END, event
                """
            )
            favorite_teams = await conn.fetch(
                """
                SELECT team_id, team_name, short_name, managers, share_pct,
                       avg_total, median_total, best_rank, avg_weekly_points,
                       avg_volatility, avg_bench_points, avg_transfer_cost
                FROM mv_favorite_team_summary
                ORDER BY managers DESC
                """
            )
            return {
                "archetypes": [dict(row) for row in archetypes],
                "consistency": [dict(row) for row in consistency],
                "efficiency": [dict(row) for row in efficiency],
                "percentiles": [dict(row) for row in percentiles],
                "extremes": [dict(row) for row in extremes],
                "rankBandGameweeks": [dict(row) for row in rank_band_gameweeks],
                "favoriteTeams": [dict(row) for row in favorite_teams],
            }

    return await cached("insights:v1", 21600, load)


@app.get("/lab")
async def lab():
    async def load():
        async with pool().acquire() as conn:
            bench = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, rank, total, bench_points,
                       avg_bench_points, avg_points, volatility, transfer_cost, archetype
                FROM mv_bench_pain_hall
                ORDER BY bench_points DESC, rank ASC
                LIMIT 100
                """
            )
            explosions = await conn.fetch(
                """
                SELECT event, entry, entry_name, player_name, final_rank, total,
                       points, points_on_bench, event_transfers_cost, team_value
                FROM mv_weekly_explosions
                ORDER BY points DESC, final_rank ASC
                LIMIT 100
                """
            )
            scatter = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, rank, total, avg_points,
                       volatility, bench_points, transfer_cost, avg_team_value,
                       max_team_value, consistency_ratio, points_per_million, archetype
                FROM mv_scatter_lab_sample
                ORDER BY rank ASC
                """
            )
            race = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, final_rank, event, total_points, points
                FROM mv_rank_race_top50
                ORDER BY final_rank, event
                """
            )
            return {
                "benchPain": [dict(row) for row in bench],
                "explosions": [dict(row) for row in explosions],
                "scatter": [dict(row) for row in scatter],
                "race": [dict(row) for row in race],
            }

    return await cached("lab:v1", 21600, load)


@app.get("/clubs/{team_id}")
async def club_detail(team_id: int):
    async def load():
        async with pool().acquire() as conn:
            club = await conn.fetchrow(
                """
                SELECT team_id, team_name, short_name, managers, share_pct,
                       avg_total, median_total, best_rank, avg_weekly_points,
                       avg_volatility, avg_bench_points, avg_transfer_cost
                FROM mv_favorite_team_summary
                WHERE team_id = $1
                """,
                team_id,
            )
            gameweeks = await conn.fetch(
                """
                SELECT team_id, team_name, short_name, event, managers, avg_points,
                       avg_bench_points, avg_transfer_cost
                FROM mv_club_gameweek_profile
                WHERE team_id = $1
                ORDER BY event
                """,
                team_id,
            )
            leaders = await conn.fetch(
                """
                SELECT ks.entry, ks.entry_name, ks.player_name, ks.rank, ks.total, ks.event_total
                FROM managers m
                JOIN kenya_standings ks ON ks.entry = m.entry AND ks.league_id = 131
                WHERE COALESCE(NULLIF(m.raw->>'favourite_team', '')::integer, 0) = $1
                ORDER BY ks.rank ASC
                LIMIT 50
                """,
                team_id,
            )
            return {
                "club": dict(club) if club else None,
                "gameweeks": [dict(row) for row in gameweeks],
                "leaders": [dict(row) for row in leaders],
            }

    return await cached(f"club:{team_id}:v1", 21600, load)


@app.get("/archetypes/{archetype}")
async def archetype_detail(archetype: str):
    async def load():
        async with pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, rank, total, avg_points,
                       volatility, bench_points, transfer_cost, avg_team_value,
                       consistency_ratio, points_per_million, archetype
                FROM mv_manager_metrics
                WHERE lower(replace(archetype, ' ', '-')) = lower($1)
                ORDER BY rank ASC
                LIMIT 500
                """,
                archetype,
            )
            return [dict(row) for row in rows]

    return await cached(f"archetype:{archetype}:v1", 21600, load)


@app.get("/stories")
async def stories():
    async def load():
        async with pool().acquire() as conn:
            counts = await conn.fetch(
                """
                SELECT story_type, count(*)::integer AS managers,
                       round(avg(total), 2) AS avg_total,
                       round(avg(run_in_gain), 2) AS avg_run_in_gain,
                       round(avg(journey_range), 2) AS avg_journey_range
                FROM mv_season_stories
                GROUP BY story_type
                ORDER BY managers DESC
                """
            )
            comeback = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, final_rank AS rank, total,
                       rank_gw20, comeback_after_gw20, story_type
                FROM mv_season_stories
                WHERE rank_gw20 IS NOT NULL
                ORDER BY comeback_after_gw20 DESC NULLS LAST
                LIMIT 100
                """
            )
            late = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, final_rank AS rank, total,
                       rank_gw30, run_in_gain, run_in_avg, story_type
                FROM mv_season_stories
                WHERE rank_gw30 IS NOT NULL
                ORDER BY run_in_gain DESC NULLS LAST
                LIMIT 100
                """
            )
            collapse = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, final_rank AS rank, total,
                       rank_gw10, collapse_after_gw10, story_type
                FROM mv_season_stories
                WHERE rank_gw10 IS NOT NULL
                ORDER BY collapse_after_gw10 DESC NULLS LAST
                LIMIT 100
                """
            )
            swings_up = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, final_rank AS rank, event,
                       previous_kenya_rank, kenya_rank, rank_gain, points, total_points
                FROM mv_weekly_rank_swings
                ORDER BY rank_gain DESC
                LIMIT 100
                """
            )
            swings_down = await conn.fetch(
                """
                SELECT entry, entry_name, player_name, final_rank AS rank, event,
                       previous_kenya_rank, kenya_rank, rank_gain, points, total_points
                FROM mv_weekly_rank_swings
                ORDER BY rank_gain ASC
                LIMIT 100
                """
            )
            return {
                "counts": [dict(row) for row in counts],
                "comeback": [dict(row) for row in comeback],
                "lateChargers": [dict(row) for row in late],
                "collapses": [dict(row) for row in collapse],
                "swingsUp": [dict(row) for row in swings_up],
                "swingsDown": [dict(row) for row in swings_down],
            }

    return await cached("stories:v1", 21600, load)


# Season-aware 2026/27 API. Legacy routes above remain available for the
# 2025/26 archive while the frontend migrates to this contract.


@app.get("/v2/seasons")
async def seasons_v2():
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.id,s.label,s.starts_year,s.ends_year,s.is_active,s.country_league_id,
                   count(DISTINCT e.event)::integer AS events_loaded,
                   max(ss.captured_at) AS latest_standings_at
            FROM seasons s
            LEFT JOIN fpl_events e ON e.season_id=s.id
            LEFT JOIN standings_snapshots ss ON ss.season_id=s.id
            GROUP BY s.id ORDER BY s.starts_year DESC
            """
        )
        return [dict(row) for row in rows]


@app.get("/v2/status")
async def status_v2(season: str | None = None):
    season_id = await resolve_season(season)
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                $1::text AS season_id,
                (SELECT event FROM fpl_events WHERE season_id=$1 AND is_current LIMIT 1) AS current_event,
                (SELECT count(*) FROM fpl_players WHERE season_id=$1)::integer AS players,
                (SELECT count(*) FROM fpl_teams WHERE season_id=$1)::integer AS teams,
                (SELECT count(*) FROM vw_latest_standings WHERE season_id=$1)::integer AS standings_rows,
                (SELECT captured_at FROM vw_latest_standings_snapshot WHERE season_id=$1) AS standings_updated_at,
                (SELECT max(updated_at) FROM player_event_live_v2 WHERE season_id=$1) AS live_updated_at,
                (SELECT status FROM pipeline_runs WHERE season_id=$1 ORDER BY started_at DESC LIMIT 1) AS pipeline_status,
                (SELECT started_at FROM pipeline_runs WHERE season_id=$1 ORDER BY started_at DESC LIMIT 1) AS pipeline_started_at
            """,
            season_id,
        )
        quality = await conn.fetch(
            """
            SELECT DISTINCT ON (check_name) check_name,status,observed_value,expected_value,checked_at
            FROM data_quality_results WHERE season_id=$1
            ORDER BY check_name,checked_at DESC
            """,
            season_id,
        )
        return {**dict(row), "quality": [dict(item) for item in quality]}


@app.get("/v2/overview")
async def overview_v2(season: str | None = None):
    season_id = await resolve_season(season)

    async def load():
        async with pool().acquire() as conn:
            season_row = await conn.fetchrow("SELECT * FROM seasons WHERE id=$1", season_id)
            event = await conn.fetchrow(
                """
                SELECT * FROM fpl_events WHERE season_id=$1
                ORDER BY is_current DESC,is_previous DESC,event DESC LIMIT 1
                """,
                season_id,
            )
            snapshot = await conn.fetchrow(
                "SELECT * FROM vw_latest_standings_snapshot WHERE season_id=$1", season_id
            )
            summary = None
            leaders = []
            if snapshot:
                summary = await conn.fetchrow(
                    """
                    SELECT count(*)::integer AS managers,min(total)::integer AS min_points,
                           max(total)::integer AS max_points,round(avg(total),2) AS avg_points,
                           percentile_cont(0.5) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS median_points,
                           percentile_cont(0.9) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS p90_points,
                           percentile_cont(0.99) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS p99_points
                    FROM standings_snapshot_rows WHERE snapshot_id=$1
                    """,
                    snapshot["id"],
                )
                leaders = await conn.fetch(
                    """
                    SELECT entry,entry_name,player_name,rank,last_rank,total,event_total
                    FROM standings_snapshot_rows WHERE snapshot_id=$1
                    ORDER BY rank NULLS LAST LIMIT 10
                    """,
                    snapshot["id"],
                )
            cohort = await conn.fetchrow(
                """
                SELECT count(*)::integer AS managers,round(avg(points),2) AS avg_points,
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY points)::numeric(10,2) AS median_points,
                       max(points)::integer AS max_points,round(avg(points_on_bench),2) AS avg_bench_points,
                       round(avg(event_transfers_cost),2) AS avg_transfer_cost
                FROM manager_event_history_v2 WHERE season_id=$1 AND event=$2
                """,
                season_id,
                event["event"] if event else 0,
            )
            top_players = await conn.fetch(
                """
                SELECT l.element,p.web_name,t.short_name,l.total_points,l.minutes,l.goals_scored,
                       l.assists,l.bonus,l.bps,l.defensive_contribution
                FROM player_event_live_v2 l
                JOIN fpl_players p ON p.season_id=l.season_id AND p.element=l.element
                JOIN fpl_teams t ON t.season_id=p.season_id AND t.team_id=p.team_id
                WHERE l.season_id=$1 AND l.event=$2
                ORDER BY l.total_points DESC,l.bps DESC LIMIT 10
                """,
                season_id,
                event["event"] if event else 0,
            )
            fixtures = await conn.fetch(
                """
                SELECT f.fixture_id,f.event,f.kickoff_time,f.finished,f.started,
                       h.name AS team_h_name,h.short_name AS team_h_short,f.team_h_score,
                       a.name AS team_a_name,a.short_name AS team_a_short,f.team_a_score
                FROM fpl_fixtures f
                JOIN fpl_teams h ON h.season_id=f.season_id AND h.team_id=f.team_h
                JOIN fpl_teams a ON a.season_id=f.season_id AND a.team_id=f.team_a
                WHERE f.season_id=$1 AND f.event=$2 ORDER BY f.kickoff_time
                """,
                season_id,
                event["event"] if event else 0,
            )
            return {
                "season": dict(season_row),
                "event": dict(event) if event else None,
                "snapshot": dict(snapshot) if snapshot else None,
                "summary": dict(summary) if summary else None,
                "cohort": dict(cohort),
                "leaders": [dict(row) for row in leaders],
                "topPlayers": [dict(row) for row in top_players],
                "fixtures": [dict(row) for row in fixtures],
            }

    return await cached(f"v2:overview:{season_id}:v1", 120, load)


@app.get("/v2/leaderboard")
async def leaderboard_v2(
    season: str | None = None,
    q: str = "",
    limit: int = Query(default=50, ge=1, le=500),
):
    season_id = await resolve_season(season)
    q = q.strip()
    async with pool().acquire() as conn:
        snapshot_id = await conn.fetchval(
            "SELECT id FROM vw_latest_standings_snapshot WHERE season_id=$1", season_id
        )
        if not snapshot_id:
            return {"snapshot": None, "rows": []}
        if q:
            rows = await conn.fetch(
                """
                SELECT entry,entry_name,player_name,rank,last_rank,total,event_total,
                       (last_rank-rank)::integer AS rank_gain
                FROM standings_snapshot_rows
                WHERE snapshot_id=$1 AND
                      (entry_name ILIKE '%'||$2||'%' OR player_name ILIKE '%'||$2||'%' OR entry::text=$2)
                ORDER BY rank NULLS LAST LIMIT $3
                """,
                snapshot_id,
                q,
                limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT entry,entry_name,player_name,rank,last_rank,total,event_total,
                       (last_rank-rank)::integer AS rank_gain
                FROM standings_snapshot_rows WHERE snapshot_id=$1
                ORDER BY rank NULLS LAST LIMIT $2
                """,
                snapshot_id,
                limit,
            )
        snapshot = await conn.fetchrow("SELECT * FROM standings_snapshots WHERE id=$1", snapshot_id)
        return {"snapshot": dict(snapshot), "rows": [dict(row) for row in rows]}


@app.get("/v2/players")
async def players_v2(
    season: str | None = None,
    event: int | None = None,
    sort: str = Query(default="points", pattern="^(points|ownership|transfers|defensive|bps)$"),
    limit: int = Query(default=50, ge=1, le=200),
):
    season_id = await resolve_season(season)
    if event is None:
        event = await pool().fetchval(
            "SELECT event FROM fpl_events WHERE season_id=$1 AND is_current LIMIT 1", season_id
        )
    order = {
        "points": "COALESCE(l.total_points,p.event_points) DESC",
        "ownership": "p.selected_by_percent DESC NULLS LAST",
        "transfers": "((p.raw->>'transfers_in_event')::integer-(p.raw->>'transfers_out_event')::integer) DESC NULLS LAST",
        "defensive": "COALESCE(l.defensive_contribution,p.defensive_contribution) DESC NULLS LAST",
        "bps": "l.bps DESC NULLS LAST",
    }[sort]
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT p.element,p.web_name,p.first_name,p.second_name,t.name AS team_name,t.short_name,
                   p.element_type,p.now_cost,p.status,p.selected_by_percent,p.total_points,
                   p.event_points,p.form,p.points_per_game,p.expected_goals,p.expected_assists,
                   p.expected_goal_involvements,p.defensive_contribution,p.price_change_projection,
                   l.total_points AS live_points,l.minutes,l.goals_scored,l.assists,l.bonus,l.bps,
                   l.defensive_contribution AS live_defensive_contribution,
                   (p.raw->>'transfers_in_event')::integer AS transfers_in_event,
                   (p.raw->>'transfers_out_event')::integer AS transfers_out_event
            FROM fpl_players p
            JOIN fpl_teams t ON t.season_id=p.season_id AND t.team_id=p.team_id
            LEFT JOIN player_event_live_v2 l ON l.season_id=p.season_id AND l.element=p.element AND l.event=$2
            WHERE p.season_id=$1 ORDER BY {order},p.web_name LIMIT $3
            """,
            season_id,
            event,
            limit,
        )
        return {"season": season_id, "event": event, "sort": sort, "rows": [dict(row) for row in rows]}


@app.get("/v2/managers/{entry}")
async def manager_v2(entry: int, season: str | None = None):
    season_id = await resolve_season(season)
    async with pool().acquire() as conn:
        snapshot_id = await conn.fetchval(
            "SELECT id FROM vw_latest_standings_snapshot WHERE season_id=$1", season_id
        )
        manager = await conn.fetchrow(
            """
            SELECT s.entry,s.entry_name,s.player_name,s.rank,s.last_rank,s.total,s.event_total,
                   p.player_region_name,p.summary_overall_rank,p.summary_overall_points,p.favourite_team
            FROM standings_snapshot_rows s
            LEFT JOIN manager_profiles_v2 p ON p.season_id=s.season_id AND p.entry=s.entry
            WHERE s.snapshot_id=$1 AND s.entry=$2
            """,
            snapshot_id,
            entry,
        ) if snapshot_id else None
        if not manager:
            raise HTTPException(status_code=404, detail="Manager is not present in the latest captured cohort")
        history = await conn.fetch(
            """
            SELECT event,points,total_points,overall_rank,bank,team_value AS value,
                   event_transfers,event_transfers_cost,points_on_bench
            FROM manager_event_history_v2 WHERE season_id=$1 AND entry=$2 ORDER BY event
            """,
            season_id,
            entry,
        )
        metrics = await conn.fetchrow(
            "SELECT * FROM vw_manager_event_metrics WHERE season_id=$1 AND entry=$2",
            season_id,
            entry,
        )
        chips = await conn.fetch(
            "SELECT chip_name,event FROM manager_chips_v2 WHERE season_id=$1 AND entry=$2 ORDER BY event",
            season_id,
            entry,
        )
        return {
            "season": season_id,
            "manager": dict(manager),
            "metrics": dict(metrics) if metrics else None,
            "history": [dict(row) for row in history],
            "chips": [dict(row) for row in chips],
        }


@app.get("/v2/gameweeks/{event}/content")
async def content_v2(event: int, season: str | None = None):
    season_id = await resolve_season(season)
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (fact_key) fact_key,status,value,cohort,sample_size,
                   calculated_at,methodology,source_snapshot_id
            FROM content_facts WHERE season_id=$1 AND event=$2
            ORDER BY fact_key,calculated_at DESC
            """,
            season_id,
            event,
        )
        if not rows:
            raise HTTPException(status_code=404, detail="The weekly content pack has not been generated")
        return {
            "season": season_id,
            "event": event,
            "facts": {row["fact_key"]: dict(row) for row in rows},
        }


@app.get("/v2/gameweeks/{event}/fixtures")
async def fixtures_v2(event: int, season: str | None = None):
    season_id = await resolve_season(season)
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT f.fixture_id,f.kickoff_time,f.finished,f.started,
                   h.name AS team_h_name,h.short_name AS team_h_short,f.team_h_score,
                   a.name AS team_a_name,a.short_name AS team_a_short,f.team_a_score,
                   f.difficulty_h,f.difficulty_a
            FROM fpl_fixtures f
            JOIN fpl_teams h ON h.season_id=f.season_id AND h.team_id=f.team_h
            JOIN fpl_teams a ON a.season_id=f.season_id AND a.team_id=f.team_a
            WHERE f.season_id=$1 AND f.event=$2 ORDER BY f.kickoff_time
            """,
            season_id,
            event,
        )
        return [dict(row) for row in rows]


def artifact_inventory(season_id: str, event: int) -> list[dict[str, object]]:
    directory = CONTENT_ROOT / season_id / f"gw-{event:02d}"
    artifacts = {
        "article": "article.md",
        "social": "social.md",
        "engineering": "engineering.md",
        "brief": "brief.json",
    }
    inventory: list[dict[str, object]] = []
    for key, filename in artifacts.items():
        path = directory / filename
        if not path.is_file():
            continue
        stat = path.stat()
        inventory.append(
            {
                "key": key,
                "filename": filename,
                "bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
            }
        )
    return inventory


@app.get("/v2/ops")
async def ops_v2(season: str | None = None):
    """Publication-safe operational state for the VPS project cockpit."""
    season_id = await resolve_season(season)
    async with pool().acquire() as conn:
        event = await conn.fetchrow(
            """
            SELECT event,name,deadline_time,finished,data_checked,average_entry_score,
                   highest_score,ranked_count,updated_at
            FROM fpl_events WHERE season_id=$1
            ORDER BY is_current DESC,is_previous DESC,event DESC LIMIT 1
            """,
            season_id,
        )
        published = await conn.fetchrow(
            "SELECT * FROM vw_latest_standings_snapshot WHERE season_id=$1", season_id
        )
        crawl = await conn.fetchrow(
            """
            SELECT id,event,captured_at,crawl_mode,crawl_status,started_at,finished_at,
                   last_heartbeat_at,expected_pages,expected_rows,pages_collected,
                   managers_collected,rows_fetched,duplicate_rows,is_complete,
                   official_data_checked
            FROM standings_snapshots
            WHERE season_id=$1 AND crawl_mode='full'
            ORDER BY started_at DESC LIMIT 1
            """,
            season_id,
        )
        crawl_progress = None
        if crawl:
            crawl_progress = await conn.fetchrow(
                """
                SELECT count(*)::integer AS scheduled_pages,
                       count(*) FILTER (WHERE status='finished')::integer AS finished_pages,
                       count(*) FILTER (WHERE status='running')::integer AS running_pages,
                       count(*) FILTER (WHERE status='failed')::integer AS failed_pages,
                       COALESCE(sum(row_count) FILTER (WHERE status='finished'),0)::integer AS rows_fetched,
                       round(avg(duration_ms) FILTER (WHERE status='finished'))::integer AS avg_page_ms,
                       max(fetched_at) AS latest_page_at
                FROM standings_crawl_pages WHERE snapshot_id=$1
                """,
                crawl["id"],
            )
        runs = await conn.fetch(
            """
            SELECT id,job_name,status,started_at,finished_at,
                   round(extract(epoch FROM (COALESCE(finished_at,now())-started_at)))::integer
                       AS duration_seconds,
                   (error IS NOT NULL) AS has_error
            FROM pipeline_runs WHERE season_id=$1
            ORDER BY started_at DESC LIMIT 16
            """,
            season_id,
        )
        freshness = await conn.fetchrow(
            """
            SELECT
                (SELECT max(updated_at) FROM player_event_live_v2 WHERE season_id=$1) AS live_players,
                (SELECT max(updated_at) FROM fpl_players WHERE season_id=$1) AS bootstrap,
                (SELECT max(updated_at) FROM fpl_fixtures WHERE season_id=$1) AS fixtures,
                (SELECT max(captured_at) FROM standings_snapshots
                    WHERE season_id=$1 AND crawl_status='finished') AS standings
            """,
            season_id,
        )
        quality = await conn.fetch(
            """
            SELECT DISTINCT ON (check_name) check_name,status,observed_value,
                   expected_value,checked_at
            FROM data_quality_results WHERE season_id=$1
            ORDER BY check_name,checked_at DESC
            """,
            season_id,
        )
        pack_rows = await conn.fetch(
            """
            SELECT event,max(calculated_at) AS calculated_at,
                   count(DISTINCT fact_key)::integer AS facts,
                   (array_agg(status ORDER BY calculated_at DESC))[1] AS status,
                   max(source_snapshot_id) AS source_snapshot_id,
                   max(sample_size)::integer AS largest_sample
            FROM content_facts WHERE season_id=$1
            GROUP BY event ORDER BY event DESC
            """,
            season_id,
        )
        packs = []
        for row in pack_rows:
            item = dict(row)
            item["artifacts"] = artifact_inventory(season_id, row["event"])
            packs.append(item)
        return {
            "season": season_id,
            "event": dict(event) if event else None,
            "published_snapshot": dict(published) if published else None,
            "full_crawl": {
                **(dict(crawl) if crawl else {}),
                "progress": dict(crawl_progress) if crawl_progress else None,
            }
            if crawl
            else None,
            "freshness": dict(freshness),
            "quality": [dict(row) for row in quality],
            "runs": [dict(row) for row in runs],
            "content_packs": packs,
        }


@app.get("/v2/content-packs/{event}/{artifact}")
async def content_pack_artifact_v2(
    event: int,
    artifact: str,
    season: str | None = None,
):
    season_id = await resolve_season(season)
    filenames = {
        "article": "article.md",
        "social": "social.md",
        "engineering": "engineering.md",
        "brief": "brief.json",
    }
    filename = filenames.get(artifact)
    if filename is None or not 1 <= event <= 38:
        raise HTTPException(status_code=404, detail="Content artifact not found")
    path = CONTENT_ROOT / season_id / f"gw-{event:02d}" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Content artifact not found")
    stat = path.stat()
    return JSONResponse(
        {
            "season": season_id,
            "event": event,
            "artifact": artifact,
            "filename": filename,
            "bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "content": path.read_text(encoding="utf-8"),
        },
        headers={"Cache-Control": "no-store"},
    )
