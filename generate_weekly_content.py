"""Generate complete, deterministic weekly editorial packs from verified facts."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import asyncpg

from fplke_settings import settings


def serialise(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot serialise {type(value).__name__}")


def plain(value: Any) -> Any:
    return json.loads(json.dumps(value, default=serialise))


def manager_label(row: dict[str, Any] | None) -> str:
    if not row:
        return "Not available"
    return row.get("entry_name") or row.get("player_name") or f"Entry {row.get('entry')}"


def number(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    numeric = float(value)
    return f"{numeric:,.{digits}f}" if numeric % 1 else f"{int(numeric):,}"


def pct(value: Any) -> str:
    return "—" if value is None else f"{float(value):.1f}%"


def svg_document(title: str, subtitle: str, body: str, height: int = 675) -> str:
    title_xml = html.escape(title)
    subtitle_xml = html.escape(subtitle)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">
<title id="title">{title_xml}</title><desc id="desc">{subtitle_xml}</desc>
<rect width="1200" height="{height}" fill="#f7f6f0"/><rect width="18" height="{height}" fill="#1f6b4d"/>
<text x="64" y="70" fill="#1f1d18" font-family="Arial,sans-serif" font-size="34" font-weight="700">{title_xml}</text>
<text x="64" y="108" fill="#69655d" font-family="Arial,sans-serif" font-size="18">{subtitle_xml}</text>
{body}
<text x="64" y="{height - 28}" fill="#69655d" font-family="Arial,sans-serif" font-size="15">FPL Kenya · official standings + declared cohort · {settings.season_label}</text>
</svg>\n"""


def horizontal_bar_svg(
    title: str,
    subtitle: str,
    rows: Iterable[dict[str, Any]],
    label_key: str,
    value_key: str,
    suffix: str = "",
    limit: int = 8,
) -> str:
    values = list(rows)[:limit]
    maximum = max((float(row.get(value_key) or 0) for row in values), default=1) or 1
    parts = []
    for index, row in enumerate(values):
        y = 150 + index * 58
        value = float(row.get(value_key) or 0)
        width = max(0, 700 * value / maximum)
        label = html.escape(str(row.get(label_key) or "Unknown")[:34])
        shown = html.escape(number(value, 1) + suffix)
        parts.append(f'<text x="64" y="{y + 22}" fill="#1f1d18" font-family="Arial,sans-serif" font-size="18" font-weight="600">{label}</text>')
        parts.append(f'<rect x="350" y="{y}" width="700" height="30" rx="4" fill="#e2dfd5"/>')
        parts.append(f'<rect x="350" y="{y}" width="{width:.1f}" height="30" rx="4" fill="#1f6b4d"/>')
        parts.append(f'<text x="1070" y="{y + 22}" fill="#1f1d18" font-family="Arial,sans-serif" font-size="17" font-weight="700">{shown}</text>')
    if not values:
        parts.append('<text x="64" y="190" fill="#69655d" font-family="Arial,sans-serif" font-size="22">No qualifying data.</text>')
    return svg_document(title, subtitle, "\n".join(parts))


def histogram_svg(pack: dict[str, Any]) -> str:
    rows = pack["scoreDistribution"]
    maximum = max((int(row["managers"]) for row in rows), default=1) or 1
    chart_x, chart_y, chart_width, chart_height = 70, 155, 1060, 380
    gap = 8
    bar_width = max(12, (chart_width - gap * max(0, len(rows) - 1)) / max(1, len(rows)))
    parts = [f'<line x1="{chart_x}" y1="{chart_y + chart_height}" x2="{chart_x + chart_width}" y2="{chart_y + chart_height}" stroke="#a8a399"/>']
    for index, row in enumerate(rows):
        value = int(row["managers"])
        height = chart_height * value / maximum
        x = chart_x + index * (bar_width + gap)
        y = chart_y + chart_height - height
        label = f"{row['bucket_start']}–{row['bucket_start'] + 9}"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{height:.1f}" rx="3" fill="#1f6b4d"/>')
        parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" fill="#1f1d18" font-family="Arial,sans-serif" font-size="13">{value}</text>')
        parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{chart_y + chart_height + 24}" text-anchor="middle" fill="#69655d" font-family="Arial,sans-serif" font-size="12">{label}</text>')
    return svg_document(
        f"GW{pack['event']} score distribution",
        f"Every ten-point band in the event-specific cohort; n={pack['samples']['cohortManagers']:,}",
        "\n".join(parts),
    )


def dashboard_svg(pack: dict[str, Any]) -> str:
    cards = [
        ("Cohort average", pack["cohort"].get("avg_points"), "points"),
        ("Global average", pack["eventDetails"].get("average_entry_score"), "points"),
        ("Managers taking hits", pack["transferBehaviour"].get("hit_managers_pct"), "%"),
        ("Average bench", pack["benchBehaviour"].get("avg_bench_points"), "points"),
    ]
    parts = []
    for index, (label, value, suffix) in enumerate(cards):
        x, y = 64 + (index % 2) * 540, 160 + (index // 2) * 210
        parts.append(f'<rect x="{x}" y="{y}" width="500" height="165" rx="12" fill="#fffdf7" stroke="#d8d4c9"/>')
        parts.append(f'<text x="{x + 28}" y="{y + 47}" fill="#69655d" font-family="Arial,sans-serif" font-size="18">{html.escape(label)}</text>')
        parts.append(f'<text x="{x + 28}" y="{y + 112}" fill="#1f1d18" font-family="Arial,sans-serif" font-size="48" font-weight="700">{number(value)}</text>')
        parts.append(f'<text x="{x + 190}" y="{y + 112}" fill="#1f6b4d" font-family="Arial,sans-serif" font-size="18" font-weight="700">{suffix}</text>')
    return svg_document(
        f"GW{pack['event']} decision dashboard",
        f"Cohort n={pack['samples']['cohortManagers']:,}; status: {pack['status']}",
        "\n".join(parts),
    )


def build_analysis(pack: dict[str, Any]) -> list[dict[str, str]]:
    cohort = pack["cohort"]
    event = pack["eventDetails"]
    transfer = pack["transferBehaviour"]
    bench = pack["benchBehaviour"]
    difference = float(cohort.get("avg_points") or 0) - float(event.get("average_entry_score") or 0)
    insights = [
        {
            "title": "Cohort versus the game",
            "finding": f"The cohort averaged {abs(difference):.1f} points {'above' if difference >= 0 else 'below'} the global FPL average.",
            "evidence": f"Cohort {number(cohort.get('avg_points'))}; global {number(event.get('average_entry_score'))}; n={cohort['managers']:,}.",
            "caveat": "The cohort is selected by Kenya rank for this event and is not a random national sample.",
        },
        {
            "title": "Transfer risk",
            "finding": f"{pct(transfer.get('hit_managers_pct'))} took a points hit, costing {number(transfer.get('total_hit_points'), 0)} points in total.",
            "evidence": f"Average transfer cost {number(transfer.get('avg_transfer_cost'), 2)} across {transfer.get('managers', 0):,} managers.",
            "caveat": "Transfer cost comes from official manager history.",
        },
        {
            "title": "Bench efficiency",
            "finding": f"The cohort left {number(bench.get('total_bench_points'), 0)} points on benches, averaging {number(bench.get('avg_bench_points'), 2)}.",
            "evidence": f"{pct(bench.get('double_digit_bench_pct'))} recorded at least ten bench points.",
            "caveat": "Bench points do not imply every benched player could legally have started.",
        },
    ]
    if pack["captains"]:
        captain = pack["captains"][0]
        insights.insert(
            1,
            {
                "title": "Captaincy concentration",
                "finding": f"{captain['web_name']} was the leading captain at {pct(captain['share_pct'])}.",
                "evidence": f"{captain['managers']:,} selections from {pack['samples']['picksManagers']:,} captured pick sets.",
                "caveat": "Shares describe the event-specific cohort, not every Kenyan manager.",
            },
        )
    if pack["topPlayers"]:
        player = pack["topPlayers"][0]
        insights.append(
            {
                "title": "Player of the week",
                "finding": f"{player['web_name']} ({player['short_name']}) led with {player['total_points']} points.",
                "evidence": f"{player['minutes']} minutes, {player['goals_scored']} goals, {player['assists']} assists and {player['bonus']} bonus.",
                "caveat": "Player totals come from the official event-live endpoint.",
            }
        )
    if pack["movers"]:
        mover = pack["movers"][0]
        insights.append(
            {
                "title": "Largest national climb",
                "finding": f"{manager_label(mover)} gained {mover['rank_gain']:,} Kenya places.",
                "evidence": f"Rank {mover['previous_rank']:,} to {mover['rank']:,} between selected completed snapshots.",
                "caveat": "Movement requires the manager to appear in both snapshots.",
            }
        )
    return insights


async def completed_events(conn: asyncpg.Connection) -> list[int]:
    rows = await conn.fetch(
        """SELECT e.event FROM fpl_events e WHERE e.season_id=$1 AND e.finished
        AND EXISTS (SELECT 1 FROM standings_snapshots s WHERE s.season_id=e.season_id
          AND s.event=e.event AND COALESCE(s.crawl_status,'finished')='finished') ORDER BY e.event""",
        settings.season_id,
    )
    return [row["event"] for row in rows]


async def build_pack(
    conn: asyncpg.Connection, event: int | None = None, min_cohort_size: int = 0
) -> dict[str, Any]:
    season = await conn.fetchrow("SELECT * FROM seasons WHERE id=$1", settings.season_id)
    if not season:
        raise RuntimeError(f"Season {settings.season_id} is not configured")
    if event is None:
        event = await conn.fetchval(
            "SELECT event FROM fpl_events WHERE season_id=$1 ORDER BY is_current DESC,is_previous DESC,event DESC LIMIT 1",
            settings.season_id,
        )
    if event is None:
        raise RuntimeError("No event is available")
    event_row = await conn.fetchrow(
        "SELECT * FROM fpl_events WHERE season_id=$1 AND event=$2", settings.season_id, event
    )
    if not event_row:
        raise RuntimeError(f"GW{event} is not configured")
    status = "final" if event_row["finished"] and event_row["data_checked"] else "live"
    if event_row["finished"] and not event_row["data_checked"]:
        status = "provisional"
    snapshot = await conn.fetchrow(
        """SELECT * FROM standings_snapshots WHERE season_id=$1 AND event=$2
        AND COALESCE(crawl_status,'finished')='finished'
        ORDER BY is_complete DESC,captured_at DESC LIMIT 1""",
        settings.season_id,
        event,
    )
    if not snapshot:
        raise RuntimeError(f"No standings snapshot is available for GW{event}")
    overview = await conn.fetchrow(
        """SELECT count(*)::integer AS managers,round(avg(total),2) AS avg_total,
        percentile_cont(.5) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS median_total,
        max(total)::integer AS leader_total,
        percentile_cont(.9) WITHIN GROUP (ORDER BY total)::numeric(10,2) AS p90_total
        FROM standings_snapshot_rows WHERE snapshot_id=$1""",
        snapshot["id"],
    )
    leader = await conn.fetchrow(
        """SELECT entry,entry_name,player_name,rank,total,event_total FROM standings_snapshot_rows
        WHERE snapshot_id=$1 ORDER BY rank NULLS LAST LIMIT 1""",
        snapshot["id"],
    )
    cohort = await conn.fetchrow(
        """SELECT count(*)::integer AS managers,round(avg(h.points),2) AS avg_points,
        percentile_cont(.5) WITHIN GROUP (ORDER BY h.points)::numeric(10,2) AS median_points,
        percentile_cont(.9) WITHIN GROUP (ORDER BY h.points)::numeric(10,2) AS p90_points,
        max(h.points)::integer AS max_points,min(h.points)::integer AS min_points,
        round(stddev_pop(h.points),2) AS volatility,round(avg(h.points_on_bench),2) AS avg_bench_points,
        round(avg(h.event_transfers_cost),2) AS avg_transfer_cost
        FROM cohort_memberships c JOIN manager_event_history_v2 h
        ON h.season_id=c.season_id AND h.event=c.event AND h.entry=c.entry
        WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank'""",
        settings.season_id,
        event,
    )
    picks_size = int(
        await conn.fetchval(
            """SELECT count(DISTINCT p.entry) FROM cohort_memberships c JOIN manager_picks_v2 p
            ON p.season_id=c.season_id AND p.event=c.event AND p.entry=c.entry
            WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank'""",
            settings.season_id,
            event,
        )
        or 0
    )
    cohort_size = int(cohort["managers"] or 0)
    if min_cohort_size and cohort_size < min_cohort_size:
        raise RuntimeError(f"GW{event} cohort has {cohort_size} histories; {min_cohort_size} required")
    if min_cohort_size and picks_size < min_cohort_size:
        raise RuntimeError(f"GW{event} cohort has {picks_size} pick sets; {min_cohort_size} required")

    async def one(sql: str, *args: Any) -> asyncpg.Record | None:
        return await conn.fetchrow(sql, *args)

    weekly_leader = await one(
        """SELECT h.entry,s.entry_name,s.player_name,h.points,h.points_on_bench,h.total_points
        FROM cohort_memberships c JOIN manager_event_history_v2 h
        ON h.season_id=c.season_id AND h.event=c.event AND h.entry=c.entry
        LEFT JOIN standings_snapshot_rows s ON s.snapshot_id=$3 AND s.entry=h.entry
        WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank'
        ORDER BY h.points DESC,h.total_points DESC LIMIT 1""",
        settings.season_id,
        event,
        snapshot["id"],
    )
    bench_pain = await one(
        """SELECT h.entry,s.entry_name,s.player_name,h.points,h.points_on_bench
        FROM cohort_memberships c JOIN manager_event_history_v2 h
        ON h.season_id=c.season_id AND h.event=c.event AND h.entry=c.entry
        LEFT JOIN standings_snapshot_rows s ON s.snapshot_id=$3 AND s.entry=h.entry
        WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank'
        ORDER BY h.points_on_bench DESC NULLS LAST,h.points DESC LIMIT 1""",
        settings.season_id,
        event,
        snapshot["id"],
    )
    distribution = await conn.fetch(
        """SELECT (floor(h.points/10.0)*10)::integer AS bucket_start,count(*)::integer AS managers
        FROM cohort_memberships c JOIN manager_event_history_v2 h
        ON h.season_id=c.season_id AND h.event=c.event AND h.entry=c.entry
        WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank'
        GROUP BY bucket_start ORDER BY bucket_start""",
        settings.season_id,
        event,
    )
    captains = await conn.fetch(
        """SELECT p.element,fp.web_name,t.short_name,count(*)::integer AS managers,
        round(100.0*count(*)/NULLIF(sum(count(*)) OVER (),0),2) AS share_pct
        FROM cohort_memberships c JOIN manager_picks_v2 p
        ON p.season_id=c.season_id AND p.event=c.event AND p.entry=c.entry
        JOIN fpl_players fp ON fp.season_id=p.season_id AND fp.element=p.element
        JOIN fpl_teams t ON t.season_id=fp.season_id AND t.team_id=fp.team_id
        WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank' AND p.is_captain
        GROUP BY p.element,fp.web_name,t.short_name ORDER BY managers DESC LIMIT 10""",
        settings.season_id,
        event,
    )
    chips = await conn.fetch(
        """SELECT h.chip_name,count(*)::integer AS managers,round(100.0*count(*)/$3,2) AS share_pct
        FROM cohort_memberships c JOIN manager_chips_v2 h
        ON h.season_id=c.season_id AND h.event=c.event AND h.entry=c.entry
        WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank'
        GROUP BY h.chip_name ORDER BY managers DESC""",
        settings.season_id,
        event,
        max(cohort_size, 1),
    )
    transfer = await one(
        """SELECT count(*)::integer AS managers,round(avg(h.event_transfers),2) AS avg_transfers,
        round(avg(h.event_transfers_cost),2) AS avg_transfer_cost,
        count(*) FILTER (WHERE h.event_transfers_cost>0)::integer AS hit_managers,
        round(100.0*count(*) FILTER (WHERE h.event_transfers_cost>0)/NULLIF(count(*),0),2) AS hit_managers_pct,
        coalesce(sum(h.event_transfers_cost),0)::integer AS total_hit_points
        FROM cohort_memberships c JOIN manager_event_history_v2 h
        ON h.season_id=c.season_id AND h.event=c.event AND h.entry=c.entry
        WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank'""",
        settings.season_id,
        event,
    )
    bench = await one(
        """SELECT round(avg(h.points_on_bench),2) AS avg_bench_points,
        percentile_cont(.5) WITHIN GROUP (ORDER BY h.points_on_bench)::numeric(10,2) AS median_bench_points,
        coalesce(sum(h.points_on_bench),0)::integer AS total_bench_points,
        max(h.points_on_bench)::integer AS max_bench_points,
        round(100.0*count(*) FILTER (WHERE h.points_on_bench>=10)/NULLIF(count(*),0),2) AS double_digit_bench_pct
        FROM cohort_memberships c JOIN manager_event_history_v2 h
        ON h.season_id=c.season_id AND h.event=c.event AND h.entry=c.entry
        WHERE c.season_id=$1 AND c.event=$2 AND c.cohort_name='top_national_rank'""",
        settings.season_id,
        event,
    )
    players = await conn.fetch(
        """SELECT l.element,p.web_name,t.short_name,p.element_type,l.total_points,l.minutes,
        l.goals_scored,l.assists,l.clean_sheets,l.saves,l.bonus,l.bps,l.defensive_contribution
        FROM player_event_live_v2 l JOIN fpl_players p ON p.season_id=l.season_id AND p.element=l.element
        JOIN fpl_teams t ON t.season_id=p.season_id AND t.team_id=p.team_id
        WHERE l.season_id=$1 AND l.event=$2 ORDER BY l.total_points DESC,l.bps DESC LIMIT 15""",
        settings.season_id,
        event,
    )
    player_elements = int(
        await conn.fetchval(
            "SELECT count(*) FROM player_event_live_v2 WHERE season_id=$1 AND event=$2",
            settings.season_id,
            event,
        )
        or 0
    )
    positions = await conn.fetch(
        """SELECT DISTINCT ON (p.element_type) p.element_type,l.element,p.web_name,t.short_name,l.total_points,l.minutes
        FROM player_event_live_v2 l JOIN fpl_players p ON p.season_id=l.season_id AND p.element=l.element
        JOIN fpl_teams t ON t.season_id=p.season_id AND t.team_id=p.team_id
        WHERE l.season_id=$1 AND l.event=$2 ORDER BY p.element_type,l.total_points DESC,l.bps DESC""",
        settings.season_id,
        event,
    )
    prices = await conn.fetch(
        """WITH event_bounds AS (
            SELECT e.deadline_time,
                   coalesce(n.deadline_time,now()) AS next_deadline
            FROM fpl_events e LEFT JOIN fpl_events n
              ON n.season_id=e.season_id AND n.event=e.event+1
            WHERE e.season_id=$1 AND e.event=$2
        ), latest AS (
            SELECT DISTINCT ON (s.element) s.*
            FROM price_snapshots s,event_bounds b
            WHERE s.season_id=$1 AND s.captured_at>=b.deadline_time
              AND s.captured_at<b.next_deadline
            ORDER BY s.element,s.captured_at DESC
        )
        SELECT p.element,p.web_name,t.short_name,l.now_cost,l.selected_by_percent,
               l.transfers_in_event,l.transfers_out_event,
               (l.transfers_in_event-l.transfers_out_event) AS net_transfers,l.projection
        FROM latest l JOIN fpl_players p ON p.season_id=l.season_id AND p.element=l.element
        JOIN fpl_teams t ON t.season_id=p.season_id AND t.team_id=p.team_id
        ORDER BY net_transfers DESC NULLS LAST LIMIT 10""",
        settings.season_id,
        event,
    )
    previous = await conn.fetch(
        """WITH per_event AS (SELECT DISTINCT ON (event) id,event FROM standings_snapshots
        WHERE season_id=$1 AND event<=$2 AND COALESCE(crawl_status,'finished')='finished'
        ORDER BY event,is_complete DESC,captured_at DESC)
        SELECT id,event FROM per_event ORDER BY event DESC LIMIT 2""",
        settings.season_id,
        event,
    )
    movers = []
    if len(previous) == 2:
        movers = await conn.fetch(
            """SELECT now.entry,now.entry_name,now.player_name,prev.rank AS previous_rank,now.rank,
            (prev.rank-now.rank)::integer AS rank_gain,now.total FROM standings_snapshot_rows now
            JOIN standings_snapshot_rows prev ON prev.snapshot_id=$2 AND prev.entry=now.entry
            WHERE now.snapshot_id=$1 AND prev.rank IS NOT NULL AND now.rank IS NOT NULL
            ORDER BY rank_gain DESC LIMIT 10""",
            previous[0]["id"],
            previous[1]["id"],
        )
    quality = await conn.fetch(
        """SELECT DISTINCT ON (check_name) check_name,status,observed_value,expected_value,checked_at
        FROM data_quality_results WHERE season_id=$1 AND (event=$2 OR event IS NULL)
        ORDER BY check_name,checked_at DESC""",
        settings.season_id,
        event,
    )
    latest_run = await conn.fetchrow(
        "SELECT job_name,status,started_at,finished_at,stats,error FROM pipeline_runs WHERE season_id=$1 ORDER BY started_at DESC LIMIT 1",
        settings.season_id,
    )
    pack = plain(
        {
            "schemaVersion": 2,
            "season": dict(season),
            "event": event,
            "status": status,
            "generatedAt": datetime.now(timezone.utc),
            "eventDetails": dict(event_row),
            "snapshot": dict(snapshot),
            "samples": {
                "nationalManagers": overview["managers"],
                "cohortManagers": cohort_size,
                "picksManagers": picks_size,
                "playerElements": player_elements,
                "cohortDefinition": "Top managers by Kenya rank in the selected gameweek snapshot.",
            },
            "overview": dict(overview),
            "leader": dict(leader) if leader else None,
            "cohort": dict(cohort),
            "weeklyLeader": dict(weekly_leader) if weekly_leader else None,
            "benchPain": dict(bench_pain) if bench_pain else None,
            "scoreDistribution": [dict(row) for row in distribution],
            "captains": [dict(row) for row in captains],
            "chipUsage": [dict(row) for row in chips],
            "transferBehaviour": dict(transfer),
            "benchBehaviour": dict(bench),
            "topPlayers": [dict(row) for row in players],
            "positionLeaders": [dict(row) for row in positions],
            "priceWatch": [dict(row) for row in prices],
            "movers": [dict(row) for row in movers],
            "quality": [dict(row) for row in quality],
            "pipeline": dict(latest_run) if latest_run else None,
            "methodology": {
                "standings": "Best completed official Kenya country-league snapshot for this event.",
                "managerCohort": "Event-specific top-ranked Kenya cohort with membership and source-snapshot lineage.",
                "players": "Official FPL event-live totals for the selected gameweek.",
                "labels": "Live figures can change; provisional figures await FPL data checks; final figures are locked.",
            },
        }
    )
    pack["analysis"] = build_analysis(pack)
    pack["visualizations"] = [
        {"key": "decision-dashboard", "filename": "visualizations/decision-dashboard.svg"},
        {"key": "score-distribution", "filename": "visualizations/score-distribution.svg"},
        {"key": "captaincy", "filename": "visualizations/captaincy.svg"},
        {"key": "top-players", "filename": "visualizations/top-players.svg"},
    ]
    if movers:
        pack["visualizations"].append({"key": "rank-movers", "filename": "visualizations/rank-movers.svg"})
    facts = {
        "kenya_overview": pack["overview"], "kenya_leader": pack["leader"],
        "cohort_scoring": pack["cohort"], "score_distribution": pack["scoreDistribution"],
        "weekly_leader": pack["weeklyLeader"], "bench_pain": pack["benchPain"],
        "bench_behaviour": pack["benchBehaviour"], "captaincy": pack["captains"],
        "chip_usage": pack["chipUsage"], "transfer_behaviour": pack["transferBehaviour"],
        "top_players": pack["topPlayers"], "position_leaders": pack["positionLeaders"],
        "price_watch": pack["priceWatch"], "rank_movers": pack["movers"],
        "editorial_analysis": pack["analysis"],
    }
    for key, value in facts.items():
        national = key in {"kenya_overview", "kenya_leader", "rank_movers"}
        player_data = key in {"top_players", "position_leaders", "price_watch"}
        cohort_label = (
            "national standings"
            if national
            else "official player data"
            if player_data
            else "event-specific top-ranked manager cohort"
        )
        sample_size = (
            overview["managers"]
            if national
            else player_elements
            if player_data and key != "price_watch"
            else len(prices)
            if key == "price_watch"
            else cohort_size
        )
        await conn.execute(
            """INSERT INTO content_facts
            (season_id,event,fact_key,status,value,cohort,sample_size,methodology,source_snapshot_id)
            VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9)
            ON CONFLICT (season_id,event,fact_key,status) DO UPDATE SET value=EXCLUDED.value,
            cohort=EXCLUDED.cohort,sample_size=EXCLUDED.sample_size,calculated_at=now(),
            methodology=EXCLUDED.methodology,source_snapshot_id=EXCLUDED.source_snapshot_id""",
            settings.season_id,
            event,
            key,
            status,
            json.dumps(value, default=serialise),
            cohort_label,
            sample_size,
            pack["methodology"]["labels"],
            snapshot["id"],
        )
    return pack


def render_analysis(pack: dict[str, Any]) -> str:
    sections = []
    for insight in pack["analysis"]:
        sections.append(f"## {insight['title']}\n\n{insight['finding']}\n\n**Evidence:** {insight['evidence']}\n\n**Interpretation note:** {insight['caveat']}")
    return f"""# FPL Kenya GW{pack['event']} analysis

Status: **{pack['status']}**

National snapshot: **{pack['samples']['nationalManagers']:,} managers**

Decision cohort: **{pack['samples']['cohortManagers']:,} managers**

Picks coverage: **{pack['samples']['picksManagers']:,} managers**

{chr(10).join(chr(10) + item for item in sections)}

## Methodology

{pack['methodology']['managerCohort']} National standings and cohort behaviour are never presented as the same population.
"""


def render_article(pack: dict[str, Any]) -> str:
    leader, cohort, weekly = pack["leader"], pack["cohort"], pack["weeklyLeader"]
    insights = "\n\n".join(f"### {x['title']}\n\n{x['finding']} {x['evidence']}" for x in pack["analysis"])
    players = "\n".join(f"- {x['web_name']} ({x['short_name']}): {x['total_points']} points, {x['minutes']} minutes" for x in pack["topPlayers"][:5])
    return f"""---
season: {settings.season_id}
gameweek: {pack['event']}
status: {pack['status']}
generated_at: {pack['generatedAt']}
national_sample: {pack['samples']['nationalManagers']}
cohort_sample: {pack['samples']['cohortManagers']}
---

# Kenya Gameweek {pack['event']} in numbers

**{pack['status'].capitalize()} data.** {manager_label(leader)} leads the Kenya standings on {leader.get('total', '—') if leader else '—'} points. The source snapshot contains {pack['overview']['managers']:,} managers and is {'complete' if pack['snapshot']['is_complete'] else 'bounded'}.

![GW{pack['event']} decision dashboard](visualizations/decision-dashboard.svg)

## The scoring picture

The event-specific cohort contains {cohort['managers']:,} managers. Its average was {number(cohort.get('avg_points'))}, median {number(cohort.get('median_points'))}, and 90th percentile {number(cohort.get('p90_points'))}. {manager_label(weekly)} recorded its highest score at {weekly.get('points', '—') if weekly else '—'} points.

![GW{pack['event']} score distribution](visualizations/score-distribution.svg)

## What stood out

{insights}

## Players setting the pace

{players}

![GW{pack['event']} top players](visualizations/top-players.svg)

## Read this correctly

National statistics use the selected country-league snapshot. Captaincy, chips, transfers, benches and manager scores use the recorded event cohort. Picks coverage is {pack['samples']['picksManagers']:,}; history coverage is {pack['samples']['cohortManagers']:,}.
"""


def render_social(pack: dict[str, Any]) -> str:
    leader, cohort = pack["leader"], pack["cohort"]
    player = pack["topPlayers"][0] if pack["topPlayers"] else None
    captain = pack["captains"][0] if pack["captains"] else None
    return f"""# Social pack — GW{pack['event']}

## Short post

GW{pack['event']}, through a Kenyan lens 🇰🇪

• Kenya leader: {manager_label(leader)} — {leader.get('total', '—') if leader else '—'} pts
• Cohort average / median: {number(cohort.get('avg_points'))} / {number(cohort.get('median_points'))}
• Leading captain: {captain.get('web_name', '—') if captain else '—'} — {pct(captain.get('share_pct')) if captain else '—'}
• Top player: {player.get('web_name', '—') if player else '—'} — {player.get('total_points', '—') if player else '—'} pts

Status: {pack['status']}. National n={pack['samples']['nationalManagers']:,}; cohort n={pack['samples']['cohortManagers']:,}; picks n={pack['samples']['picksManagers']:,}.

## Carousel plan

1. Headline — `visualizations/decision-dashboard.svg`
2. Scoring — `visualizations/score-distribution.svg`
3. Captaincy — `visualizations/captaincy.svg`
4. Transfer and bench analysis
5. Players — `visualizations/top-players.svg`
6. Rank movement — `visualizations/rank-movers.svg` when available
7. Methodology, status and sample sizes

## Alt text

A data-led FPL Kenya recap for GW{pack['event']}, distinguishing the national snapshot from the event-specific decision cohort.
"""


def render_engineering(pack: dict[str, Any]) -> str:
    return f"""# Behind the pipeline — GW{pack['event']}

- Schema version: `2`
- Season key: `{settings.season_id}`
- Standings snapshot: `{pack['snapshot']['id']}`
- Captured managers: `{pack['snapshot']['managers_collected']:,}`
- Snapshot complete: `{pack['snapshot']['is_complete']}`
- Cohort history rows: `{pack['samples']['cohortManagers']:,}`
- Cohort pick sets: `{pack['samples']['picksManagers']:,}`
- Editorial status: `{pack['status']}`
- Visualizations: `{len(pack['visualizations'])}`

Every cohort metric joins through `cohort_memberships`, tying event, manager and source snapshot together. The manifest records every artifact's SHA-256 digest and byte size.
"""


def write_pack(pack: dict[str, Any], output_dir: str) -> Path:
    target = Path(output_dir) / settings.season_id / f"gw-{pack['event']:02d}"
    (target / "visualizations").mkdir(parents=True, exist_ok=True)
    files = {
        "article.md": render_article(pack),
        "analysis.md": render_analysis(pack),
        "social.md": render_social(pack),
        "engineering.md": render_engineering(pack),
        "brief.json": json.dumps(pack, indent=2, ensure_ascii=False) + "\n",
        "visualizations/decision-dashboard.svg": dashboard_svg(pack),
        "visualizations/score-distribution.svg": histogram_svg(pack),
        "visualizations/captaincy.svg": horizontal_bar_svg(
            f"GW{pack['event']} captaincy", f"Captured picks; n={pack['samples']['picksManagers']:,}", pack["captains"], "web_name", "share_pct", "%"),
        "visualizations/top-players.svg": horizontal_bar_svg(
            f"GW{pack['event']} top players", "Official event-live points", pack["topPlayers"], "web_name", "total_points", " pts"),
    }
    if pack["movers"]:
        files["visualizations/rank-movers.svg"] = horizontal_bar_svg(
            f"GW{pack['event']} Kenya rank climbers", "Places gained between completed snapshots", pack["movers"], "entry_name", "rank_gain", " places")
    for filename, content in files.items():
        (target / filename).write_text(content, encoding="utf-8")
    manifest = {
        "schemaVersion": 1, "season": settings.season_id, "event": pack["event"],
        "status": pack["status"], "generatedAt": pack["generatedAt"],
        "files": [{"path": name, "bytes": len(data.encode()), "sha256": hashlib.sha256(data.encode()).hexdigest()} for name, data in sorted(files.items())],
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


async def main(args: argparse.Namespace) -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    targets = []
    job_name = "content_backfill" if args.all_completed else "content"
    run_id = await conn.fetchval(
        """INSERT INTO pipeline_runs (season_id,job_name,event)
        VALUES ($1,$2,$3) RETURNING id""",
        settings.season_id,
        job_name,
        args.event,
    )
    try:
        events = await completed_events(conn) if args.all_completed else [args.event]
        for event in events:
            targets.append(write_pack(await build_pack(conn, event, args.min_cohort_size), args.output_dir))
        await conn.execute(
            """UPDATE pipeline_runs SET status='finished',finished_at=now(),stats=$2::jsonb
            WHERE id=$1""",
            run_id,
            json.dumps({"events": events, "packs": [str(target) for target in targets]}),
        )
    except Exception as exc:
        await conn.execute(
            """UPDATE pipeline_runs SET status='failed',finished_at=now(),error=$2,
            stats=$3::jsonb WHERE id=$1""",
            run_id,
            repr(exc),
            json.dumps({"packs_written": [str(target) for target in targets]}),
        )
        raise
    finally:
        await conn.close()
    for target in targets:
        print(target.resolve())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate complete FPL Kenya weekly content packs")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--event", type=int)
    target.add_argument("--all-completed", action="store_true")
    parser.add_argument("--output-dir", default="content/generated")
    parser.add_argument("--min-cohort-size", type=int, default=settings.content_min_cohort_size)
    args = parser.parse_args()
    if args.min_cohort_size < 1:
        parser.error("--min-cohort-size must be positive")
    return args


if __name__ == "__main__":
    arguments = parse_args()
    if "DATABASE_URL" not in os.environ:
        raise SystemExit("DATABASE_URL is required")
    asyncio.run(main(arguments))
