"""Season-aware FPL Kenya ingestion pipeline.

This collector intentionally defaults to a bounded deep cohort. Use
``--max-pages 0`` only after confirming the operational and data-use policy for
a complete country-league crawl.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Awaitable, Callable, Iterable

import asyncpg
import httpx

from fplke_settings import settings


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def datetime_or_none(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Expected ISO timestamp, got {type(value).__name__}")


@dataclass
class FetchResult:
    url: str
    status_code: int
    payload: Any


class SeasonPipeline:
    def __init__(self, db: asyncpg.Pool, concurrency: int, pause: float):
        self.db = db
        self.concurrency = concurrency
        self.sem = asyncio.Semaphore(concurrency)
        self.pause = pause
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(45),
            follow_redirects=True,
            headers={"Accept": "application/json", "User-Agent": settings.user_agent},
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def fetch(self, path: str, attempts: int = 5) -> FetchResult:
        url = path if path.startswith("http") else f"{settings.base_url}{path}"
        for attempt in range(1, attempts + 1):
            try:
                async with self.sem:
                    response = await self.client.get(url)
            except httpx.HTTPError:
                if attempt == attempts:
                    raise
                await asyncio.sleep(min(60, 2**attempt + random.random()))
                continue

            if response.status_code == 200:
                if self.pause:
                    await asyncio.sleep(self.pause)
                return FetchResult(url, response.status_code, response.json())
            if response.status_code in {403, 404}:
                return FetchResult(url, response.status_code, {"detail": response.text[:500]})
            if attempt == attempts:
                response.raise_for_status()
            await asyncio.sleep(min(60, 2**attempt + random.random()))
        raise RuntimeError(f"Unable to fetch {url}")

    async def store_raw(
        self,
        result: FetchResult,
        resource_type: str,
        resource_id: str | int,
        *,
        event: int | None = None,
        page: int | None = None,
    ) -> None:
        encoded = json_dumps(result.payload)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        await self.db.execute(
            """
            INSERT INTO raw_snapshots
                (season_id, resource_type, resource_id, event, page, url,
                 status_code, payload_sha256, payload)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
            """,
            settings.season_id,
            resource_type,
            str(resource_id),
            event,
            page,
            result.url,
            result.status_code,
            digest,
            encoded,
        )

    async def sync_bootstrap(self) -> dict[str, Any]:
        result = await self.fetch("/bootstrap-static/")
        await self.store_raw(result, "bootstrap", "latest")
        bootstrap = result.payload

        async with self.db.acquire() as conn:
            async with conn.transaction():
                for event in bootstrap.get("events", []):
                    await conn.execute(
                        """
                        INSERT INTO fpl_events
                            (season_id,event,name,deadline_time,is_previous,is_current,is_next,
                             finished,data_checked,average_entry_score,highest_score,ranked_count,
                             chip_plays,raw,updated_at)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,$14::jsonb,now())
                        ON CONFLICT (season_id,event) DO UPDATE SET
                            name=EXCLUDED.name, deadline_time=EXCLUDED.deadline_time,
                            is_previous=EXCLUDED.is_previous, is_current=EXCLUDED.is_current,
                            is_next=EXCLUDED.is_next, finished=EXCLUDED.finished,
                            data_checked=EXCLUDED.data_checked,
                            average_entry_score=EXCLUDED.average_entry_score,
                            highest_score=EXCLUDED.highest_score, ranked_count=EXCLUDED.ranked_count,
                            chip_plays=EXCLUDED.chip_plays, raw=EXCLUDED.raw, updated_at=now()
                        """,
                        settings.season_id,
                        event["id"],
                        event["name"],
                        datetime_or_none(event["deadline_time"]),
                        event.get("is_previous", False),
                        event.get("is_current", False),
                        event.get("is_next", False),
                        event.get("finished", False),
                        event.get("data_checked", False),
                        event.get("average_entry_score"),
                        event.get("highest_score"),
                        event.get("ranked_count"),
                        json_dumps(event.get("chip_plays", [])),
                        json_dumps(event),
                    )

                for team in bootstrap.get("teams", []):
                    await conn.execute(
                        """
                        INSERT INTO fpl_teams
                            (season_id,team_id,name,short_name,code,strength,raw,updated_at)
                        VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,now())
                        ON CONFLICT (season_id,team_id) DO UPDATE SET
                            name=EXCLUDED.name, short_name=EXCLUDED.short_name,
                            code=EXCLUDED.code, strength=EXCLUDED.strength,
                            raw=EXCLUDED.raw, updated_at=now()
                        """,
                        settings.season_id,
                        team["id"],
                        team["name"],
                        team["short_name"],
                        team.get("code"),
                        team.get("strength"),
                        json_dumps(team),
                    )

                for player in bootstrap.get("elements", []):
                    projection = player.get("price_change_projections")
                    await conn.execute(
                        """
                        INSERT INTO fpl_players
                            (season_id,element,team_id,element_type,web_name,first_name,second_name,
                             now_cost,status,selected_by_percent,total_points,event_points,form,
                             points_per_game,expected_goals,expected_assists,
                             expected_goal_involvements,expected_goals_conceded,
                             defensive_contribution,price_change_projection,raw,updated_at)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,
                                $18,$19,$20::jsonb,$21::jsonb,now())
                        ON CONFLICT (season_id,element) DO UPDATE SET
                            team_id=EXCLUDED.team_id, element_type=EXCLUDED.element_type,
                            web_name=EXCLUDED.web_name, first_name=EXCLUDED.first_name,
                            second_name=EXCLUDED.second_name, now_cost=EXCLUDED.now_cost,
                            status=EXCLUDED.status, selected_by_percent=EXCLUDED.selected_by_percent,
                            total_points=EXCLUDED.total_points, event_points=EXCLUDED.event_points,
                            form=EXCLUDED.form, points_per_game=EXCLUDED.points_per_game,
                            expected_goals=EXCLUDED.expected_goals,
                            expected_assists=EXCLUDED.expected_assists,
                            expected_goal_involvements=EXCLUDED.expected_goal_involvements,
                            expected_goals_conceded=EXCLUDED.expected_goals_conceded,
                            defensive_contribution=EXCLUDED.defensive_contribution,
                            price_change_projection=EXCLUDED.price_change_projection,
                            raw=EXCLUDED.raw, updated_at=now()
                        """,
                        settings.season_id,
                        player["id"],
                        player["team"],
                        player["element_type"],
                        player["web_name"],
                        player.get("first_name"),
                        player.get("second_name"),
                        player["now_cost"],
                        player.get("status"),
                        decimal_or_none(player.get("selected_by_percent")),
                        player.get("total_points", 0),
                        player.get("event_points", 0),
                        decimal_or_none(player.get("form")),
                        decimal_or_none(player.get("points_per_game")),
                        decimal_or_none(player.get("expected_goals")),
                        decimal_or_none(player.get("expected_assists")),
                        decimal_or_none(player.get("expected_goal_involvements")),
                        decimal_or_none(player.get("expected_goals_conceded")),
                        player.get("defensive_contribution"),
                        json_dumps(projection) if projection is not None else None,
                        json_dumps(player),
                    )
                    await conn.execute(
                        """
                        INSERT INTO price_snapshots
                            (season_id,element,now_cost,transfers_in_event,transfers_out_event,
                             selected_by_percent,projection)
                        VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)
                        """,
                        settings.season_id,
                        player["id"],
                        player["now_cost"],
                        player.get("transfers_in_event", 0),
                        player.get("transfers_out_event", 0),
                        decimal_or_none(player.get("selected_by_percent")),
                        json_dumps(projection) if projection is not None else None,
                    )

        fixtures_result = await self.fetch("/fixtures/")
        await self.store_raw(fixtures_result, "fixtures", "latest")
        async with self.db.acquire() as conn:
            async with conn.transaction():
                for fixture in fixtures_result.payload:
                    await conn.execute(
                        """
                        INSERT INTO fpl_fixtures
                            (season_id,fixture_id,event,kickoff_time,team_h,team_a,team_h_score,
                             team_a_score,finished,started,difficulty_h,difficulty_a,raw,updated_at)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,now())
                        ON CONFLICT (season_id,fixture_id) DO UPDATE SET
                            event=EXCLUDED.event,kickoff_time=EXCLUDED.kickoff_time,
                            team_h_score=EXCLUDED.team_h_score,team_a_score=EXCLUDED.team_a_score,
                            finished=EXCLUDED.finished,started=EXCLUDED.started,
                            difficulty_h=EXCLUDED.difficulty_h,difficulty_a=EXCLUDED.difficulty_a,
                            raw=EXCLUDED.raw,updated_at=now()
                        """,
                        settings.season_id,
                        fixture["id"],
                        fixture.get("event"),
                        datetime_or_none(fixture.get("kickoff_time")),
                        fixture["team_h"],
                        fixture["team_a"],
                        fixture.get("team_h_score"),
                        fixture.get("team_a_score"),
                        fixture.get("finished", False),
                        fixture.get("started", False),
                        fixture.get("team_h_difficulty"),
                        fixture.get("team_a_difficulty"),
                        json_dumps(fixture),
                    )

        return {
            "events": len(bootstrap.get("events", [])),
            "teams": len(bootstrap.get("teams", [])),
            "players": len(bootstrap.get("elements", [])),
            "fixtures": len(fixtures_result.payload),
            "current_event": next(
                (row["id"] for row in bootstrap.get("events", []) if row.get("is_current")), None
            ),
        }

    async def current_event(self) -> int | None:
        return await self.db.fetchval(
            "SELECT event FROM fpl_events WHERE season_id=$1 AND is_current ORDER BY event DESC LIMIT 1",
            settings.season_id,
        )

    async def sync_event_live(self, event: int) -> dict[str, int]:
        result = await self.fetch(f"/event/{event}/live/")
        await self.store_raw(result, "event_live", event, event=event)
        if result.status_code != 200:
            return {"event": event, "players": 0}
        async with self.db.acquire() as conn:
            async with conn.transaction():
                for row in result.payload.get("elements", []):
                    stats = row.get("stats", {})
                    await conn.execute(
                        """
                        INSERT INTO player_event_live_v2
                            (season_id,event,element,total_points,minutes,goals_scored,assists,
                             clean_sheets,saves,bonus,bps,defensive_contribution,
                             expected_goals,expected_assists,raw,updated_at)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15::jsonb,now())
                        ON CONFLICT (season_id,event,element) DO UPDATE SET
                            total_points=EXCLUDED.total_points,minutes=EXCLUDED.minutes,
                            goals_scored=EXCLUDED.goals_scored,assists=EXCLUDED.assists,
                            clean_sheets=EXCLUDED.clean_sheets,saves=EXCLUDED.saves,
                            bonus=EXCLUDED.bonus,bps=EXCLUDED.bps,
                            defensive_contribution=EXCLUDED.defensive_contribution,
                            expected_goals=EXCLUDED.expected_goals,
                            expected_assists=EXCLUDED.expected_assists,
                            raw=EXCLUDED.raw,updated_at=now()
                        """,
                        settings.season_id,
                        event,
                        row["id"],
                        stats.get("total_points", 0),
                        stats.get("minutes", 0),
                        stats.get("goals_scored", 0),
                        stats.get("assists", 0),
                        stats.get("clean_sheets", 0),
                        stats.get("saves", 0),
                        stats.get("bonus", 0),
                        stats.get("bps", 0),
                        stats.get("defensive_contribution", 0),
                        decimal_or_none(stats.get("expected_goals")),
                        decimal_or_none(stats.get("expected_assists")),
                        json_dumps(row),
                    )
        return {"event": event, "players": len(result.payload.get("elements", []))}

    async def _standings_page(self, page: int) -> FetchResult:
        return await self.fetch(
            f"/leagues-classic/{settings.league_id}/standings/?page_standings={page}"
        )

    async def _discover_last_standings_page(self) -> tuple[int, dict[int, FetchResult]]:
        """Find the terminal page in O(log n) requests and retain probe responses."""
        probes: dict[int, FetchResult] = {}

        async def probe(page: int) -> tuple[int, bool]:
            if page not in probes:
                result = await self._standings_page(page)
                if result.status_code != 200:
                    raise RuntimeError(
                        f"Standings boundary probe {page} returned {result.status_code}"
                    )
                probes[page] = result
            standings = probes[page].payload.get("standings", {})
            return len(standings.get("results", [])), bool(standings.get("has_next"))

        rows, has_next = await probe(1)
        if not rows:
            raise RuntimeError("The Kenya standings league returned no managers")
        if not has_next:
            return 1, probes

        low = 1
        high = 2
        while True:
            _, high_has_next = await probe(high)
            if not high_has_next:
                break
            low = high
            high *= 2

        while high - low > 1:
            middle = (low + high) // 2
            _, middle_has_next = await probe(middle)
            if middle_has_next:
                low = middle
            else:
                high = middle

        terminal_rows, terminal_has_next = await probe(high)
        if not terminal_rows or terminal_has_next:
            raise RuntimeError(f"Unable to verify terminal standings page {high}")
        return high, probes

    async def _write_standings_page(
        self,
        snapshot_id: int,
        event: int | None,
        page: int,
        result: FetchResult,
        duration_ms: int,
        *,
        preserve_existing: bool = False,
    ) -> int:
        await self.store_raw(result, "kenya_standings", page, event=event, page=page)
        if result.status_code != 200:
            raise RuntimeError(f"Standings page {page} returned {result.status_code}")
        standings = result.payload.get("standings", {})
        rows = standings.get("results", [])
        async with self.db.acquire() as conn:
            async with conn.transaction():
                if not preserve_existing:
                    await conn.execute(
                        "DELETE FROM standings_snapshot_rows WHERE snapshot_id=$1 AND page=$2",
                        snapshot_id,
                        page,
                    )
                await conn.executemany(
                    """
                    INSERT INTO standings_snapshot_rows
                        (snapshot_id,season_id,event,page,entry,entry_name,player_name,rank,
                         last_rank,total,event_total,has_played,raw)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb)
                    ON CONFLICT (snapshot_id,entry) DO UPDATE SET
                        page=EXCLUDED.page,entry_name=EXCLUDED.entry_name,
                        player_name=EXCLUDED.player_name,rank=EXCLUDED.rank,
                        last_rank=EXCLUDED.last_rank,total=EXCLUDED.total,
                        event_total=EXCLUDED.event_total,has_played=EXCLUDED.has_played,
                        raw=EXCLUDED.raw
                    """,
                    [
                        (
                            snapshot_id,
                            settings.season_id,
                            event,
                            page,
                            row["entry"],
                            row.get("entry_name"),
                            row.get("player_name"),
                            row.get("rank"),
                            row.get("last_rank"),
                            row.get("total"),
                            row.get("event_total"),
                            row.get("has_played"),
                            json_dumps(row),
                        )
                        for row in rows
                    ],
                )
                await conn.execute(
                    """
                    INSERT INTO standings_crawl_pages
                        (snapshot_id,page,status,attempts,row_count,has_next,started_at,
                         fetched_at,duration_ms,error_summary)
                    VALUES ($1,$2,'finished',1,$3,$4,now(),now(),$5,NULL)
                    ON CONFLICT (snapshot_id,page) DO UPDATE SET
                        status='finished',attempts=standings_crawl_pages.attempts+1,
                        row_count=EXCLUDED.row_count,has_next=EXCLUDED.has_next,
                        fetched_at=now(),duration_ms=EXCLUDED.duration_ms,error_summary=NULL
                    """,
                    snapshot_id,
                    page,
                    len(rows),
                    bool(standings.get("has_next")),
                    duration_ms,
                )
        return len(rows)

    async def sync_full_standings(
        self,
        *,
        resume: bool,
        require_data_checked: bool,
        if_needed: bool,
        repair_passes: int,
    ) -> dict[str, Any]:
        event = await self.current_event()
        if event is None:
            raise RuntimeError("No current event; run bootstrap first")
        data_checked = bool(
            await self.db.fetchval(
                "SELECT data_checked FROM fpl_events WHERE season_id=$1 AND event=$2",
                settings.season_id,
                event,
            )
        )
        if require_data_checked and not data_checked:
            return {
                "event": event,
                "skipped": True,
                "reason": "official FPL data is not checked yet",
            }
        if if_needed:
            existing = await self.db.fetchrow(
                """
                SELECT id,managers_collected,pages_collected FROM standings_snapshots
                WHERE season_id=$1 AND event=$2 AND crawl_mode='full'
                  AND crawl_status='finished' AND is_complete
                  AND ($3::boolean = false OR official_data_checked)
                ORDER BY captured_at DESC LIMIT 1
                """,
                settings.season_id,
                event,
                require_data_checked,
            )
            if existing:
                return {
                    "event": event,
                    "snapshot_id": existing["id"],
                    "pages": existing["pages_collected"],
                    "managers": existing["managers_collected"],
                    "is_complete": True,
                    "skipped": True,
                    "reason": "a complete full-country snapshot already exists",
                }

        last_page, probes = await self._discover_last_standings_page()
        terminal_rows = len(probes[last_page].payload.get("standings", {}).get("results", []))
        expected_rows = (last_page - 1) * 50 + terminal_rows

        snapshot = None
        if resume:
            snapshot = await self.db.fetchrow(
                """
                SELECT id,duplicate_rows FROM standings_snapshots
                WHERE season_id=$1 AND event=$2 AND crawl_mode='full'
                  AND crawl_status IN ('running','failed')
                  AND started_at > now() - interval '12 hours'
                ORDER BY started_at DESC LIMIT 1
                """,
                settings.season_id,
                event,
            )
        if snapshot:
            snapshot_id = snapshot["id"]
            preserve_existing = True
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "DELETE FROM standings_snapshot_rows WHERE snapshot_id=$1 AND page>$2",
                        snapshot_id,
                        last_page,
                    )
                    await conn.execute(
                        "DELETE FROM standings_crawl_pages WHERE snapshot_id=$1 AND page>$2",
                        snapshot_id,
                        last_page,
                    )
            await self.db.execute(
                """
                UPDATE standings_snapshots SET crawl_status='running',error_summary=NULL,
                    last_heartbeat_at=now(),expected_pages=$2,expected_rows=$3
                WHERE id=$1
                """,
                snapshot_id,
                last_page,
                expected_rows,
            )
        else:
            preserve_existing = False
            snapshot_id = await self.db.fetchval(
                """
                INSERT INTO standings_snapshots
                    (season_id,event,source_note,crawl_mode,crawl_status,started_at,
                     last_heartbeat_at,expected_pages,expected_rows,official_data_checked)
                VALUES ($1,$2,$3,'full','running',now(),now(),$4,$5,$6) RETURNING id
                """,
                settings.season_id,
                event,
                "Official Kenya country league; resumable complete crawl",
                last_page,
                expected_rows,
                data_checked,
            )

        await self.db.execute(
            """
            INSERT INTO standings_crawl_pages (snapshot_id,page,status)
            SELECT $1,page,'pending' FROM generate_series(1,$2) AS page
            ON CONFLICT (snapshot_id,page) DO NOTHING
            """,
            snapshot_id,
            last_page,
        )
        completed_rows = await self.db.fetch(
            "SELECT page FROM standings_crawl_pages WHERE snapshot_id=$1 AND status='finished'",
            snapshot_id,
        )
        completed = {row["page"] for row in completed_rows}
        pending = [page for page in range(1, last_page + 1) if page not in completed]
        queue: asyncio.Queue[int | None] = asyncio.Queue()
        for page in pending:
            queue.put_nowait(page)
        worker_count = max(1, min(self.concurrency, len(pending))) if pending else 0
        for _ in range(worker_count):
            queue.put_nowait(None)

        errors: list[tuple[int, str]] = []
        progress_lock = asyncio.Lock()
        pages_done = len(completed)

        async def worker() -> None:
            nonlocal pages_done
            while True:
                page = await queue.get()
                try:
                    if page is None:
                        return
                    await self.db.execute(
                        """
                        UPDATE standings_crawl_pages
                        SET status='running',started_at=now(),error_summary=NULL
                        WHERE snapshot_id=$1 AND page=$2
                        """,
                        snapshot_id,
                        page,
                    )
                    started = time.perf_counter()
                    result = probes.get(page) or await self._standings_page(page)
                    duration_ms = round((time.perf_counter() - started) * 1000)
                    for write_attempt in range(3):
                        try:
                            await self._write_standings_page(
                                snapshot_id,
                                event,
                                page,
                                result,
                                duration_ms,
                                preserve_existing=preserve_existing,
                            )
                            break
                        except (
                            asyncpg.exceptions.DeadlockDetectedError,
                            asyncpg.exceptions.SerializationError,
                        ):
                            if write_attempt == 2:
                                raise
                            await asyncio.sleep(0.2 * (write_attempt + 1) + random.random() * 0.2)
                    async with progress_lock:
                        pages_done += 1
                        if pages_done % 50 == 0 or pages_done == last_page:
                            await self.db.execute(
                                """
                                UPDATE standings_snapshots SET last_heartbeat_at=now()
                                WHERE id=$1
                                """,
                                snapshot_id,
                            )
                            print(
                                f"full standings {pages_done}/{last_page} pages "
                                f"({pages_done / last_page:.1%})",
                                flush=True,
                            )
                except Exception as exc:
                    if page is not None:
                        summary = f"{type(exc).__name__}: {exc}"[:500]
                        errors.append((page, summary))
                        await self.db.execute(
                            """
                            UPDATE standings_crawl_pages
                            SET status='failed',attempts=attempts+1,fetched_at=now(),error_summary=$3
                            WHERE snapshot_id=$1 AND page=$2
                            """,
                            snapshot_id,
                            page,
                            summary,
                        )
                finally:
                    queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(worker_count)]
        if workers:
            await queue.join()
            await asyncio.gather(*workers)

        page_stats = await self.db.fetchrow(
            """
            SELECT count(*) FILTER (WHERE status='finished')::integer AS pages,
                   COALESCE(sum(row_count) FILTER (WHERE status='finished'),0)::integer AS rows_fetched,
                   count(*) FILTER (WHERE status='failed')::integer AS failed_pages,
                   bool_and(CASE WHEN page=$2 THEN has_next=false ELSE true END)
                       FILTER (WHERE status='finished') AS terminal_verified
            FROM standings_crawl_pages WHERE snapshot_id=$1
            """,
            snapshot_id,
            last_page,
        )
        unique_managers = await self.db.fetchval(
            "SELECT count(*) FROM standings_snapshot_rows WHERE snapshot_id=$1", snapshot_id
        )
        rows_fetched = page_stats["rows_fetched"]
        duplicate_rows = max(0, rows_fetched - unique_managers)
        is_complete = bool(
            page_stats["pages"] == last_page
            and page_stats["failed_pages"] == 0
            and page_stats["terminal_verified"]
            and rows_fetched == expected_rows
            and duplicate_rows == 0
        )
        crawl_status = "finished" if is_complete else "failed"
        error_summary = None
        if not is_complete:
            error_summary = (
                f"coverage validation failed: pages={page_stats['pages']}/{last_page}, "
                f"rows={rows_fetched}/{expected_rows}, duplicates={duplicate_rows}, "
                f"failed_pages={page_stats['failed_pages']}"
            )
            if errors:
                error_summary += f"; first_error={errors[0][0]} {errors[0][1]}"
        await self.db.execute(
            """
            UPDATE standings_snapshots SET crawl_status=$2,is_complete=$3,
                pages_collected=$4,managers_collected=$5,rows_fetched=$6,
                duplicate_rows=$7,finished_at=now(),last_heartbeat_at=now(),error_summary=$8,
                official_data_checked=$9
            WHERE id=$1
            """,
            snapshot_id,
            crawl_status,
            is_complete,
            page_stats["pages"],
            unique_managers,
            rows_fetched,
            duplicate_rows,
            error_summary,
            data_checked,
        )
        if (
            not is_complete
            and duplicate_rows > 0
            and page_stats["failed_pages"] == 0
            and repair_passes > 0
        ):
            await self.db.execute(
                """
                UPDATE standings_crawl_pages SET status='pending',row_count=NULL,
                    has_next=NULL,started_at=NULL,fetched_at=NULL,duration_ms=NULL,
                    error_summary=NULL
                WHERE snapshot_id=$1
                """,
                snapshot_id,
            )
            print(
                f"full standings repair pass: {duplicate_rows} entries still missing; "
                f"{repair_passes} pass(es) available",
                flush=True,
            )
            return await self.sync_full_standings(
                resume=True,
                require_data_checked=require_data_checked,
                if_needed=False,
                repair_passes=repair_passes - 1,
            )
        if not is_complete:
            raise RuntimeError(error_summary)
        return {
            "snapshot_id": snapshot_id,
            "event": event,
            "pages": last_page,
            "managers": unique_managers,
            "rows_fetched": rows_fetched,
            "is_complete": True,
            "resumed_pages": len(completed),
        }

    async def sync_standings(
        self,
        max_pages: int | None,
        *,
        resume: bool = False,
        require_data_checked: bool = False,
        if_needed: bool = False,
        repair_passes: int = 2,
    ) -> dict[str, Any]:
        if max_pages is None:
            return await self.sync_full_standings(
                resume=resume,
                require_data_checked=require_data_checked,
                if_needed=if_needed,
                repair_passes=repair_passes,
            )
        event = await self.current_event()
        snapshot_id = await self.db.fetchval(
            """
            INSERT INTO standings_snapshots
                (season_id,event,source_note,crawl_mode,crawl_status,started_at,last_heartbeat_at)
            VALUES ($1,$2,$3,'bounded','running',now(),now()) RETURNING id
            """,
            settings.season_id,
            event,
            "Official country league; bounded crawl" if max_pages else "Official country league; complete crawl",
        )
        page = 1
        rows_collected = 0
        has_next = True
        while has_next and (max_pages is None or page <= max_pages):
            result = await self.fetch(
                f"/leagues-classic/{settings.league_id}/standings/?page_standings={page}"
            )
            await self.store_raw(result, "kenya_standings", page, event=event, page=page)
            if result.status_code != 200:
                raise RuntimeError(f"Standings page {page} returned {result.status_code}")
            standings = result.payload.get("standings", {})
            rows = standings.get("results", [])
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    await conn.executemany(
                        """
                        INSERT INTO standings_snapshot_rows
                            (snapshot_id,season_id,event,page,entry,entry_name,player_name,rank,
                             last_rank,total,event_total,has_played,raw)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb)
                        ON CONFLICT (snapshot_id,entry) DO NOTHING
                        """,
                        [
                            (
                                snapshot_id,
                                settings.season_id,
                                event,
                                page,
                                row["entry"],
                                row.get("entry_name"),
                                row.get("player_name"),
                                row.get("rank"),
                                row.get("last_rank"),
                                row.get("total"),
                                row.get("event_total"),
                                row.get("has_played"),
                                json_dumps(row),
                            )
                            for row in rows
                        ],
                    )
            rows_collected += len(rows)
            has_next = bool(standings.get("has_next"))
            print(f"standings page={page} rows={len(rows)} has_next={has_next}", flush=True)
            page += 1

        is_complete = not has_next
        pages_collected = page - 1
        unique_managers = await self.db.fetchval(
            "SELECT count(*) FROM standings_snapshot_rows WHERE snapshot_id=$1", snapshot_id
        )
        await self.db.execute(
            """
            UPDATE standings_snapshots
            SET is_complete=$2,pages_collected=$3,managers_collected=$4,
                rows_fetched=$5,duplicate_rows=GREATEST(0,$5-$4),crawl_status='finished',
                finished_at=now(),last_heartbeat_at=now()
            WHERE id=$1
            """,
            snapshot_id,
            is_complete,
            pages_collected,
            unique_managers,
            rows_collected,
        )
        return {
            "snapshot_id": snapshot_id,
            "event": event,
            "pages": pages_collected,
            "managers": unique_managers,
            "rows_fetched": rows_collected,
            "is_complete": is_complete,
        }

    async def cohort_entries(self, limit: int, event: int | None = None) -> list[int]:
        if event is None:
            rows = await self.db.fetch(
                """
                SELECT entry FROM vw_latest_standings
                WHERE season_id=$1 ORDER BY rank NULLS LAST LIMIT $2
                """,
                settings.season_id,
                limit,
            )
        else:
            rows = await self.db.fetch(
                """
                WITH target AS (
                    SELECT id FROM standings_snapshots
                    WHERE season_id=$1 AND event=$2
                      AND COALESCE(crawl_status, 'finished')='finished'
                    ORDER BY is_complete DESC,captured_at DESC LIMIT 1
                )
                SELECT entry FROM standings_snapshot_rows
                WHERE snapshot_id=(SELECT id FROM target)
                ORDER BY rank NULLS LAST LIMIT $3
                """,
                settings.season_id,
                event,
                limit,
            )
        return [row["entry"] for row in rows]

    async def sync_manager(self, entry: int, event: int | None, include_picks: bool) -> None:
        profile_result, history_result = await asyncio.gather(
            self.fetch(f"/entry/{entry}/"),
            self.fetch(f"/entry/{entry}/history/"),
        )
        await self.store_raw(profile_result, "manager_profile", entry)
        await self.store_raw(history_result, "manager_history", entry)
        if profile_result.status_code != 200 or history_result.status_code != 200:
            raise RuntimeError(
                f"manager endpoints returned profile={profile_result.status_code} "
                f"history={history_result.status_code}"
            )
        if profile_result.status_code == 200:
            profile = profile_result.payload
            await self.db.execute(
                """
                INSERT INTO manager_profiles_v2
                    (season_id,entry,player_first_name,player_last_name,player_region_id,
                     player_region_name,favourite_team,summary_overall_points,
                     summary_overall_rank,summary_event_points,current_event,raw,updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,now())
                ON CONFLICT (season_id,entry) DO UPDATE SET
                    player_first_name=EXCLUDED.player_first_name,
                    player_last_name=EXCLUDED.player_last_name,
                    player_region_id=EXCLUDED.player_region_id,
                    player_region_name=EXCLUDED.player_region_name,
                    favourite_team=EXCLUDED.favourite_team,
                    summary_overall_points=EXCLUDED.summary_overall_points,
                    summary_overall_rank=EXCLUDED.summary_overall_rank,
                    summary_event_points=EXCLUDED.summary_event_points,
                    current_event=EXCLUDED.current_event,raw=EXCLUDED.raw,updated_at=now()
                """,
                settings.season_id,
                entry,
                profile.get("player_first_name"),
                profile.get("player_last_name"),
                profile.get("player_region_id"),
                profile.get("player_region_name"),
                profile.get("favourite_team"),
                profile.get("summary_overall_points"),
                profile.get("summary_overall_rank"),
                profile.get("summary_event_points"),
                profile.get("current_event"),
                json_dumps(profile),
            )

        if history_result.status_code == 200:
            history = history_result.payload
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    for row in history.get("current", []):
                        await conn.execute(
                            """
                            INSERT INTO manager_event_history_v2
                                (season_id,entry,event,points,total_points,overall_rank,
                                 percentile_rank,bank,team_value,event_transfers,
                                 event_transfers_cost,points_on_bench,raw,updated_at)
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,now())
                            ON CONFLICT (season_id,entry,event) DO UPDATE SET
                                points=EXCLUDED.points,total_points=EXCLUDED.total_points,
                                overall_rank=EXCLUDED.overall_rank,
                                percentile_rank=EXCLUDED.percentile_rank,bank=EXCLUDED.bank,
                                team_value=EXCLUDED.team_value,event_transfers=EXCLUDED.event_transfers,
                                event_transfers_cost=EXCLUDED.event_transfers_cost,
                                points_on_bench=EXCLUDED.points_on_bench,
                                raw=EXCLUDED.raw,updated_at=now()
                            """,
                            settings.season_id,
                            entry,
                            row["event"],
                            row.get("points"),
                            row.get("total_points"),
                            row.get("overall_rank"),
                            row.get("percentile_rank"),
                            row.get("bank"),
                            row.get("value"),
                            row.get("event_transfers"),
                            row.get("event_transfers_cost"),
                            row.get("points_on_bench"),
                            json_dumps(row),
                        )
                    for chip in history.get("chips", []):
                        await conn.execute(
                            """
                            INSERT INTO manager_chips_v2
                                (season_id,entry,chip_name,event,raw,updated_at)
                            VALUES ($1,$2,$3,$4,$5::jsonb,now())
                            ON CONFLICT (season_id,entry,chip_name,event) DO UPDATE SET
                                raw=EXCLUDED.raw,updated_at=now()
                            """,
                            settings.season_id,
                            entry,
                            chip["name"],
                            chip["event"],
                            json_dumps(chip),
                        )

        if include_picks and event:
            picks_result = await self.fetch(f"/entry/{entry}/event/{event}/picks/")
            await self.store_raw(picks_result, "manager_picks", f"{entry}:{event}", event=event)
            if picks_result.status_code != 200:
                raise RuntimeError(f"picks endpoint returned {picks_result.status_code}")
            if picks_result.status_code == 200:
                async with self.db.acquire() as conn:
                    async with conn.transaction():
                        for pick in picks_result.payload.get("picks", []):
                            await conn.execute(
                                """
                                INSERT INTO manager_picks_v2
                                    (season_id,entry,event,element,position,multiplier,
                                     is_captain,is_vice_captain,raw,updated_at)
                                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,now())
                                ON CONFLICT (season_id,entry,event,position) DO UPDATE SET
                                    element=EXCLUDED.element,multiplier=EXCLUDED.multiplier,
                                    is_captain=EXCLUDED.is_captain,
                                    is_vice_captain=EXCLUDED.is_vice_captain,
                                    raw=EXCLUDED.raw,updated_at=now()
                                """,
                                settings.season_id,
                                entry,
                                event,
                                pick["element"],
                                pick["position"],
                                pick["multiplier"],
                                pick.get("is_captain", False),
                                pick.get("is_vice_captain", False),
                                json_dumps(pick),
                            )

    async def map_limited(
        self, items: Iterable[int], func: Callable[[int], Awaitable[None]], label: str
    ) -> dict[str, Any]:
        values = list(items)
        attempted = 0
        succeeded = 0
        errors: list[dict[str, Any]] = []
        queue: asyncio.Queue[int] = asyncio.Queue()
        for value in values:
            queue.put_nowait(value)

        async def worker() -> None:
            nonlocal attempted, succeeded
            while True:
                try:
                    item = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    await func(item)
                    succeeded += 1
                except Exception as exc:  # finish the cohort and report exact coverage
                    if len(errors) < 25:
                        errors.append({"item": item, "error": repr(exc)})
                    print(f"{label} item={item} error={exc!r}", flush=True)
                finally:
                    attempted += 1
                    queue.task_done()
                    if attempted % 100 == 0 or attempted == len(values):
                        print(
                            f"{label} {attempted}/{len(values)} "
                            f"succeeded={succeeded} failed={attempted-succeeded}",
                            flush=True,
                        )

        workers = [
            asyncio.create_task(worker())
            for _ in range(min(max(1, self.concurrency), len(values)))
        ]
        await asyncio.gather(*workers)
        return {
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": attempted - succeeded,
            "errors": errors,
        }

    async def cohort_coverage(self, entries: list[int], event: int) -> dict[str, int]:
        if not entries:
            return {"history_managers": 0, "picks_managers": 0}
        history_managers = await self.db.fetchval(
            """
            SELECT count(DISTINCT entry) FROM manager_event_history_v2
            WHERE season_id=$1 AND event=$2 AND entry=ANY($3::integer[])
            """,
            settings.season_id,
            event,
            entries,
        )
        picks_managers = await self.db.fetchval(
            """
            SELECT count(DISTINCT entry) FROM manager_picks_v2
            WHERE season_id=$1 AND event=$2 AND entry=ANY($3::integer[])
            """,
            settings.season_id,
            event,
            entries,
        )
        return {
            "history_managers": int(history_managers or 0),
            "picks_managers": int(picks_managers or 0),
        }

    async def completed_events(self) -> list[int]:
        rows = await self.db.fetch(
            """
            SELECT event FROM fpl_events
            WHERE season_id=$1 AND finished
            ORDER BY event
            """,
            settings.season_id,
        )
        return [row["event"] for row in rows]

    async def register_cohort_memberships(self, entries: list[int], event: int) -> int:
        if not entries:
            return 0
        snapshot_id = await self.db.fetchval(
            """
            SELECT id FROM standings_snapshots
            WHERE season_id=$1 AND event=$2
              AND COALESCE(crawl_status, 'finished')='finished'
            ORDER BY is_complete DESC,captured_at DESC LIMIT 1
            """,
            settings.season_id,
            event,
        )
        if snapshot_id is None:
            raise RuntimeError(f"No standings snapshot is available for GW{event}")
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    DELETE FROM cohort_memberships
                    WHERE season_id=$1 AND event=$2 AND cohort_name='top_national_rank'
                      AND NOT (entry=ANY($3::integer[]))
                    """,
                    settings.season_id,
                    event,
                    entries,
                )
                await conn.execute(
                    """
                    INSERT INTO cohort_memberships
                        (season_id,event,cohort_name,entry,selected_rank,source_snapshot_id,selected_at)
                    SELECT $1,$2,'top_national_rank',r.entry,r.rank,$3,now()
                    FROM standings_snapshot_rows r
                    WHERE r.snapshot_id=$3 AND r.entry=ANY($4::integer[])
                    ON CONFLICT (season_id,event,cohort_name,entry) DO UPDATE SET
                        selected_rank=EXCLUDED.selected_rank,
                        source_snapshot_id=EXCLUDED.source_snapshot_id,
                        selected_at=now()
                    """,
                    settings.season_id,
                    event,
                    snapshot_id,
                    entries,
                )
        return int(snapshot_id)

    async def sync_cohort(
        self,
        limit: int,
        include_picks: bool,
        event: int | None = None,
        if_needed: bool = False,
        min_success_rate: float = 0.9,
    ) -> dict[str, Any]:
        event = event or await self.current_event()
        if event is None:
            raise RuntimeError("No event is available; run bootstrap first")
        entries = await self.cohort_entries(limit, event)
        if not entries:
            raise RuntimeError(f"No standings snapshot is available for GW{event}")
        source_snapshot_id = await self.register_cohort_memberships(entries, event)
        required = math.ceil(len(entries) * min_success_rate)
        before = await self.cohort_coverage(entries, event)
        if if_needed and before["history_managers"] >= required and (
            not include_picks or before["picks_managers"] >= required
        ):
            return {
                "event": event,
                "requested": len(entries),
                "required": required,
                "skipped": True,
                "source_snapshot_id": source_snapshot_id,
                "coverage": before,
            }

        async def one(entry: int) -> None:
            await self.sync_manager(entry, event, include_picks)

        collection = await self.map_limited(entries, one, f"deep cohort GW{event}")
        coverage = await self.cohort_coverage(entries, event)
        return {
            "event": event,
            "requested": len(entries),
            "required": required,
            "skipped": False,
            "source_snapshot_id": source_snapshot_id,
            "collection": collection,
            "coverage": coverage,
            "picks": include_picks,
        }

    async def sync_completed_cohorts(
        self,
        limit: int,
        include_picks: bool,
        if_needed: bool,
        min_success_rate: float,
    ) -> list[dict[str, Any]]:
        results = []
        for event in await self.completed_events():
            results.append(
                await self.sync_cohort(
                    limit,
                    include_picks,
                    event=event,
                    if_needed=if_needed,
                    min_success_rate=min_success_rate,
                )
            )
        return results

    async def quality_checks(
        self,
        run_id: int,
        event: int | None,
        cohort_results: list[dict[str, Any]] | None = None,
        require_picks: bool = False,
    ) -> list[dict[str, str]]:
        checks = [
            ("one_active_season", "SELECT count(*) FROM seasons WHERE is_active", 1, "fail"),
            ("event_count", "SELECT count(*) FROM fpl_events WHERE season_id=$1", 38, "fail"),
            ("team_count", "SELECT count(*) FROM fpl_teams WHERE season_id=$1", 20, "fail"),
            ("player_minimum", "SELECT count(*) FROM fpl_players WHERE season_id=$1", 400, "fail_min"),
            ("standings_present", "SELECT count(*) FROM vw_latest_standings WHERE season_id=$1", 1, "warn_min"),
        ]
        results: list[dict[str, str]] = []
        for name, sql, expected, mode in checks:
            observed = await self.db.fetchval(sql, settings.season_id) if "$1" in sql else await self.db.fetchval(sql)
            if mode == "fail":
                status = "pass" if observed == expected else "fail"
            elif mode == "fail_min":
                status = "pass" if observed >= expected else "fail"
            else:
                status = "pass" if observed >= expected else "warn"
            await self.db.execute(
                """
                INSERT INTO data_quality_results
                    (pipeline_run_id,season_id,event,check_name,status,observed_value,expected_value)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                """,
                run_id,
                settings.season_id,
                event,
                name,
                status,
                str(observed),
                str(expected),
            )
            results.append({"check": name, "status": status, "observed": str(observed)})
        for cohort in cohort_results or []:
            for metric in ("history_managers", "picks_managers"):
                if metric == "picks_managers" and not require_picks:
                    continue
                observed = cohort["coverage"][metric]
                expected = cohort["required"]
                status = "pass" if observed >= expected else "fail"
                name = f"cohort_{'history' if metric == 'history_managers' else 'picks'}_gw_{cohort['event']}"
                await self.db.execute(
                    """
                    INSERT INTO data_quality_results
                        (pipeline_run_id,season_id,event,check_name,status,observed_value,expected_value)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)
                    """,
                    run_id,
                    settings.season_id,
                    cohort["event"],
                    name,
                    status,
                    str(observed),
                    str(expected),
                )
                results.append({"check": name, "status": status, "observed": str(observed)})
        return results


async def run(args: argparse.Namespace) -> None:
    db = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=max(4, args.concurrency + 2)
    )
    pipeline = SeasonPipeline(db, args.concurrency, args.pause)
    run_id = await db.fetchval(
        "INSERT INTO pipeline_runs (season_id,job_name) VALUES ($1,$2) RETURNING id",
        settings.season_id,
        args.job,
    )
    stats: dict[str, Any] = {}
    try:
        if args.job == "bootstrap":
            stats["bootstrap"] = await pipeline.sync_bootstrap()
        elif args.job == "standings":
            stats["standings"] = await pipeline.sync_standings(
                args.max_pages or None,
                resume=args.resume,
                require_data_checked=args.require_data_checked,
                if_needed=args.if_needed,
                repair_passes=args.repair_passes,
            )
        elif args.job == "live":
            event = args.event or await pipeline.current_event()
            if not event:
                raise RuntimeError("No current event; run bootstrap first or pass --event")
            stats["live"] = await pipeline.sync_event_live(event)
        elif args.job == "cohort":
            if args.all_completed:
                stats["cohorts"] = await pipeline.sync_completed_cohorts(
                    args.cohort_size,
                    args.include_picks,
                    args.if_needed,
                    args.min_success_rate,
                )
            else:
                stats["cohort"] = await pipeline.sync_cohort(
                    args.cohort_size,
                    args.include_picks,
                    event=args.event,
                    if_needed=args.if_needed,
                    min_success_rate=args.min_success_rate,
                )
        elif args.job == "weekly":
            stats["bootstrap"] = await pipeline.sync_bootstrap()
            stats["standings"] = await pipeline.sync_standings(
                args.max_pages or None,
                resume=args.resume,
                require_data_checked=args.require_data_checked,
                if_needed=args.if_needed,
                repair_passes=args.repair_passes,
            )
            event = stats["bootstrap"].get("current_event")
            if event:
                stats["live"] = await pipeline.sync_event_live(event)
            stats["cohort"] = await pipeline.sync_cohort(args.cohort_size, args.include_picks)
        else:
            raise ValueError(f"Unknown job {args.job}")

        event = await pipeline.current_event()
        cohort_results = stats.get("cohorts") or ([stats["cohort"]] if "cohort" in stats else [])
        stats["quality"] = await pipeline.quality_checks(
            run_id,
            event,
            cohort_results=cohort_results,
            require_picks=args.include_picks,
        )
        if any(row["status"] == "fail" for row in stats["quality"]):
            raise RuntimeError("One or more required data-quality checks failed")
        await db.execute(
            """
            UPDATE pipeline_runs SET status='finished',finished_at=now(),stats=$2::jsonb
            WHERE id=$1
            """,
            run_id,
            json_dumps(stats),
        )
        print(json.dumps(stats, indent=2, default=str))
    except Exception as exc:
        await db.execute(
            """
            UPDATE pipeline_runs SET status='failed',finished_at=now(),stats=$2::jsonb,error=$3
            WHERE id=$1
            """,
            run_id,
            json_dumps(stats),
            repr(exc),
        )
        raise
    finally:
        await pipeline.close()
        await db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect season-aware FPL Kenya data")
    parser.add_argument("job", choices=["bootstrap", "standings", "live", "cohort", "weekly"])
    parser.add_argument("--concurrency", type=int, default=settings.request_concurrency)
    parser.add_argument("--pause", type=float, default=settings.request_pause_seconds)
    parser.add_argument("--max-pages", type=int, default=200, help="0 means all standings pages")
    parser.add_argument("--resume", action="store_true", help="resume a recent full crawl")
    parser.add_argument(
        "--require-data-checked",
        action="store_true",
        help="skip a full crawl until official FPL data is checked",
    )
    parser.add_argument(
        "--if-needed",
        action="store_true",
        help="skip standings or cohort work that already meets its completion contract",
    )
    parser.add_argument(
        "--repair-passes",
        type=int,
        default=2,
        help="additional full passes used to close gaps caused by moving ranks",
    )
    parser.add_argument("--cohort-size", type=int, default=settings.deep_cohort_size)
    parser.add_argument("--include-picks", action="store_true")
    parser.add_argument(
        "--all-completed",
        action="store_true",
        help="collect an event-specific cohort for every completed gameweek",
    )
    parser.add_argument(
        "--min-success-rate",
        type=float,
        default=settings.cohort_min_success_rate,
        help="minimum stored history/picks coverage required for a cohort run",
    )
    parser.add_argument("--event", type=int)
    args = parser.parse_args()
    if not 0 < args.min_success_rate <= 1:
        parser.error("--min-success-rate must be greater than 0 and at most 1")
    if args.cohort_size < 1:
        parser.error("--cohort-size must be positive")
    return args


if __name__ == "__main__":
    arguments = parse_args()
    if "DATABASE_URL" not in os.environ:
        print("DATABASE_URL is required", file=sys.stderr)
        raise SystemExit(2)
    asyncio.run(run(arguments))
