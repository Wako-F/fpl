"""Generate a deterministic weekly editorial pack from verified database facts."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import asyncpg

from fplke_settings import settings


def serialise(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot serialise {type(value).__name__}")


def manager_label(row: dict[str, Any] | None) -> str:
    if not row:
        return "Not available"
    return row.get("entry_name") or row.get("player_name") or f"Entry {row.get('entry')}"


async def build_pack(conn: asyncpg.Connection, event: int | None = None) -> dict[str, Any]:
    season = await conn.fetchrow("SELECT * FROM seasons WHERE id=$1", settings.season_id)
    if not season:
        raise RuntimeError(f"Season {settings.season_id} is not configured")
    if event is None:
        event = await conn.fetchval(
            """
            SELECT event FROM fpl_events WHERE season_id=$1
            ORDER BY is_current DESC, is_previous DESC, event DESC LIMIT 1
            """,
            settings.season_id,
        )
    if event is None:
        raise RuntimeError("No event is available")

    event_row = await conn.fetchrow(
        "SELECT * FROM fpl_events WHERE season_id=$1 AND event=$2", settings.season_id, event
    )
    status = "final" if event_row and event_row["finished"] and event_row["data_checked"] else "live"
    if event_row and event_row["finished"] and not event_row["data_checked"]:
        status = "provisional"

    snapshot = await conn.fetchrow(
        """
        SELECT * FROM standings_snapshots
        WHERE season_id=$1 AND (event=$2 OR event IS NULL)
        ORDER BY captured_at DESC LIMIT 1
        """,
        settings.season_id,
        event,
    )
    if not snapshot:
        raise RuntimeError(f"No standings snapshot is available for GW{event}")

    overview = await conn.fetchrow(
        """
        SELECT count(*)::integer AS managers, round(avg(total),2) AS avg_total,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS median_total,
               max(total)::integer AS leader_total,
               percentile_cont(0.9) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS p90_total
        FROM standings_snapshot_rows WHERE snapshot_id=$1
        """,
        snapshot["id"],
    )
    leader = await conn.fetchrow(
        """
        SELECT entry,entry_name,player_name,rank,total,event_total
        FROM standings_snapshot_rows WHERE snapshot_id=$1
        ORDER BY rank NULLS LAST LIMIT 1
        """,
        snapshot["id"],
    )
    cohort = await conn.fetchrow(
        """
        SELECT count(*)::integer AS managers, round(avg(points),2) AS avg_points,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY points)::numeric(10,2) AS median_points,
               max(points)::integer AS max_points, round(avg(points_on_bench),2) AS avg_bench_points,
               round(avg(event_transfers_cost),2) AS avg_transfer_cost
        FROM manager_event_history_v2 WHERE season_id=$1 AND event=$2
        """,
        settings.season_id,
        event,
    )
    weekly_leader = await conn.fetchrow(
        """
        SELECT h.entry,s.entry_name,s.player_name,h.points,h.points_on_bench,h.total_points
        FROM manager_event_history_v2 h
        LEFT JOIN standings_snapshot_rows s ON s.snapshot_id=$3 AND s.entry=h.entry
        WHERE h.season_id=$1 AND h.event=$2
        ORDER BY h.points DESC,h.total_points DESC LIMIT 1
        """,
        settings.season_id,
        event,
        snapshot["id"],
    )
    bench_pain = await conn.fetchrow(
        """
        SELECT h.entry,s.entry_name,s.player_name,h.points,h.points_on_bench
        FROM manager_event_history_v2 h
        LEFT JOIN standings_snapshot_rows s ON s.snapshot_id=$3 AND s.entry=h.entry
        WHERE h.season_id=$1 AND h.event=$2
        ORDER BY h.points_on_bench DESC NULLS LAST,h.points DESC LIMIT 1
        """,
        settings.season_id,
        event,
        snapshot["id"],
    )
    captains = await conn.fetch(
        """
        SELECT p.element,fp.web_name,t.short_name,count(*)::integer AS managers,
               round(100.0*count(*)/NULLIF(sum(count(*)) OVER (),0),2) AS share_pct
        FROM manager_picks_v2 p
        JOIN fpl_players fp ON fp.season_id=p.season_id AND fp.element=p.element
        JOIN fpl_teams t ON t.season_id=fp.season_id AND t.team_id=fp.team_id
        WHERE p.season_id=$1 AND p.event=$2 AND p.is_captain
        GROUP BY p.element,fp.web_name,t.short_name ORDER BY managers DESC LIMIT 5
        """,
        settings.season_id,
        event,
    )
    players = await conn.fetch(
        """
        SELECT l.element,p.web_name,t.short_name,l.total_points,l.minutes,l.goals_scored,
               l.assists,l.bonus,l.bps,l.defensive_contribution
        FROM player_event_live_v2 l
        JOIN fpl_players p ON p.season_id=l.season_id AND p.element=l.element
        JOIN fpl_teams t ON t.season_id=p.season_id AND t.team_id=p.team_id
        WHERE l.season_id=$1 AND l.event=$2
        ORDER BY l.total_points DESC,l.bps DESC LIMIT 10
        """,
        settings.season_id,
        event,
    )
    price_watch = await conn.fetch(
        """
        SELECT p.element,p.web_name,t.short_name,p.now_cost,p.selected_by_percent,
               (p.raw->>'transfers_in_event')::integer AS transfers_in_event,
               (p.raw->>'transfers_out_event')::integer AS transfers_out_event,
               p.price_change_projection
        FROM fpl_players p
        JOIN fpl_teams t ON t.season_id=p.season_id AND t.team_id=p.team_id
        WHERE p.season_id=$1
        ORDER BY ((p.raw->>'transfers_in_event')::integer -
                  (p.raw->>'transfers_out_event')::integer) DESC NULLS LAST LIMIT 10
        """,
        settings.season_id,
    )

    previous_ids = await conn.fetch(
        """
        SELECT id FROM standings_snapshots WHERE season_id=$1
        ORDER BY captured_at DESC LIMIT 2
        """,
        settings.season_id,
    )
    movers: list[asyncpg.Record] = []
    if len(previous_ids) == 2:
        movers = await conn.fetch(
            """
            SELECT now.entry,now.entry_name,now.player_name,prev.rank AS previous_rank,
                   now.rank,(prev.rank-now.rank)::integer AS rank_gain,now.total
            FROM standings_snapshot_rows now
            JOIN standings_snapshot_rows prev ON prev.snapshot_id=$2 AND prev.entry=now.entry
            WHERE now.snapshot_id=$1
            ORDER BY rank_gain DESC LIMIT 10
            """,
            previous_ids[0]["id"],
            previous_ids[1]["id"],
        )

    quality = await conn.fetch(
        """
        SELECT check_name,status,observed_value,expected_value,checked_at
        FROM data_quality_results WHERE season_id=$1 AND (event=$2 OR event IS NULL)
        ORDER BY checked_at DESC,check_name LIMIT 20
        """,
        settings.season_id,
        event,
    )
    latest_run = await conn.fetchrow(
        """
        SELECT job_name,status,started_at,finished_at,stats,error
        FROM pipeline_runs WHERE season_id=$1 ORDER BY started_at DESC LIMIT 1
        """,
        settings.season_id,
    )

    pack = {
        "schemaVersion": 1,
        "season": dict(season),
        "event": event,
        "status": status,
        "generatedAt": datetime.now(timezone.utc),
        "snapshot": dict(snapshot),
        "overview": dict(overview),
        "leader": dict(leader) if leader else None,
        "cohort": dict(cohort),
        "weeklyLeader": dict(weekly_leader) if weekly_leader else None,
        "benchPain": dict(bench_pain) if bench_pain else None,
        "captains": [dict(row) for row in captains],
        "topPlayers": [dict(row) for row in players],
        "priceWatch": [dict(row) for row in price_watch],
        "movers": [dict(row) for row in movers],
        "quality": [dict(row) for row in quality],
        "pipeline": dict(latest_run) if latest_run else None,
        "methodology": {
            "standings": "Latest official Kenya country-league snapshot.",
            "managerCohort": "Top-ranked bounded deep cohort; sample size is shown for behavioural metrics.",
            "labels": "Live figures can change; provisional figures await FPL data checks; final figures are locked.",
        },
    }

    facts = {
        "kenya_overview": pack["overview"],
        "kenya_leader": pack["leader"],
        "cohort_scoring": pack["cohort"],
        "weekly_leader": pack["weeklyLeader"],
        "bench_pain": pack["benchPain"],
        "captaincy": pack["captains"],
        "top_players": pack["topPlayers"],
        "price_watch": pack["priceWatch"],
        "rank_movers": pack["movers"],
    }
    for key, value in facts.items():
        await conn.execute(
            """
            INSERT INTO content_facts
                (season_id,event,fact_key,status,value,cohort,sample_size,methodology,source_snapshot_id)
            VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9)
            ON CONFLICT (season_id,event,fact_key,status) DO UPDATE SET
                value=EXCLUDED.value,cohort=EXCLUDED.cohort,sample_size=EXCLUDED.sample_size,
                calculated_at=now(),methodology=EXCLUDED.methodology,
                source_snapshot_id=EXCLUDED.source_snapshot_id
            """,
            settings.season_id,
            event,
            key,
            status,
            json.dumps(value, default=serialise),
            "national standings" if key in {"kenya_overview", "kenya_leader", "rank_movers"} else "deep manager cohort",
            overview["managers"] if key in {"kenya_overview", "kenya_leader", "rank_movers"} else cohort["managers"],
            pack["methodology"]["labels"],
            snapshot["id"],
        )
    return pack


def render_article(pack: dict[str, Any]) -> str:
    event = pack["event"]
    overview = pack["overview"]
    cohort = pack["cohort"]
    leader = pack["leader"]
    weekly = pack["weeklyLeader"]
    bench = pack["benchPain"]
    status = pack["status"].capitalize()
    return f"""---
season: {settings.season_id}
gameweek: {event}
status: {pack['status']}
generated_at: {pack['generatedAt'].isoformat()}
---

# Kenya Gameweek {event} in numbers

**{status} data.** Figures may change until Fantasy Premier League marks the gameweek as checked.

{manager_label(leader)} leads the latest captured Kenya standings on {leader.get('total', '—') if leader else '—'} points. The standings snapshot contains {overview.get('managers', 0):,} managers and is {'complete' if pack['snapshot']['is_complete'] else 'a bounded sample'}.

## The scoring picture

Our deep cohort currently contains {cohort.get('managers', 0):,} managers. Their GW{event} average is {cohort.get('avg_points') or '—'} and the median is {cohort.get('median_points') or '—'}.

{manager_label(weekly)} has the cohort's highest captured score at {weekly.get('points', '—') if weekly else '—'} points. {manager_label(bench)} currently carries the biggest bench total at {bench.get('points_on_bench', '—') if bench else '—'}.

## Players setting the pace

""" + "\n".join(
        f"- {row['web_name']} ({row['short_name']}): {row['total_points']} points, {row['minutes']} minutes"
        for row in pack["topPlayers"][:5]
    ) + f"""

## Read this correctly

National rank and points come from the latest Kenya country-league snapshot. Captaincy, bench and manager-behaviour figures use the declared deep cohort, with the sample size shown above. Live and provisional figures are not final.
"""


def render_social(pack: dict[str, Any]) -> str:
    event = pack["event"]
    leader = pack["leader"]
    cohort = pack["cohort"]
    top_player = pack["topPlayers"][0] if pack["topPlayers"] else None
    return f"""# Social pack — GW{event}

## Short post

GW{event}, through a Kenyan lens 🇰🇪

• Latest leader: {manager_label(leader)} — {leader.get('total', '—') if leader else '—'} pts
• Cohort average: {cohort.get('avg_points') or '—'}
• Cohort median: {cohort.get('median_points') or '—'}
• Top player so far: {top_player.get('web_name', '—') if top_player else '—'} — {top_player.get('total_points', '—') if top_player else '—'} pts

Status: {pack['status']}. Sample and methodology: /methodology

## Carousel

1. Kenya GW{event} in numbers
2. Latest national leader
3. Average versus median in our deep cohort
4. Players setting the pace
5. Captaincy split
6. Bench pain
7. Rank movers
8. Methodology and data status

## Alt text

An eight-slide FPL Kenya data recap for Gameweek {event}, labelled {pack['status']}, with national standings and clearly identified deep-cohort statistics.
"""


def render_engineering(pack: dict[str, Any]) -> str:
    snapshot = pack["snapshot"]
    cohort = pack["cohort"]
    return f"""# Behind the pipeline — GW{pack['event']}

This week's reproducible unit is the content fact: a metric, its event, status, cohort, sample size, source snapshot and methodology travel together.

- Season key: `{settings.season_id}`
- Standings snapshot: `{snapshot['id']}`
- Captured managers: `{snapshot['managers_collected']:,}`
- Snapshot complete: `{snapshot['is_complete']}`
- Deep cohort rows for GW{pack['event']}: `{cohort.get('managers', 0):,}`
- Editorial status: `{pack['status']}`

The design prevents a live number from silently becoming a final claim and prevents 2025/26 rows from mixing with 2026/27. The accompanying `brief.json` is the machine-readable source for every chart and caption in this pack.
"""


async def main(args: argparse.Namespace) -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        pack = await build_pack(conn, args.event)
    finally:
        await conn.close()

    target = Path(args.output_dir) / settings.season_id / f"gw-{pack['event']:02d}"
    target.mkdir(parents=True, exist_ok=True)
    (target / "brief.json").write_text(
        json.dumps(pack, indent=2, ensure_ascii=False, default=serialise) + "\n", encoding="utf-8"
    )
    (target / "article.md").write_text(render_article(pack), encoding="utf-8")
    (target / "social.md").write_text(render_social(pack), encoding="utf-8")
    (target / "engineering.md").write_text(render_engineering(pack), encoding="utf-8")
    print(target.resolve())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the FPL Kenya weekly content pack")
    parser.add_argument("--event", type=int)
    parser.add_argument("--output-dir", default="content/generated")
    return parser.parse_args()


if __name__ == "__main__":
    if "DATABASE_URL" not in os.environ:
        raise SystemExit("DATABASE_URL is required")
    asyncio.run(main(parse_args()))
