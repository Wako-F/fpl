import json
import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis


DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

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
    cached_value = await client.get(key)
    if cached_value:
        return json.loads(cached_value)
    value = await loader()
    await client.setex(key, ttl, json.dumps(jsonable_encoder(value), separators=(",", ":")))
    return value


async def fetchrow(query: str, *args):
    async with pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


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
