import argparse
import asyncio
import json
import os
import random
import sys
from datetime import datetime, timezone

import asyncpg
import httpx


BASE_URL = "https://fantasy.premierleague.com/api"
KENYA_LEAGUE_ID = 131
KENYA_REGION_ID = 111
USER_AGENT = "fplke-data-collector/0.1 (+research; respectful-rate-limited)"


def json_dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class Collector:
    def __init__(self, db, concurrency=8, pause=0.05):
        self.db = db
        self.sem = asyncio.Semaphore(concurrency)
        self.pause = pause
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(45.0),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    async def fetch_json(self, path, attempts=5):
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        for attempt in range(1, attempts + 1):
            async with self.sem:
                response = await self.client.get(url)
            if response.status_code == 200:
                if self.pause:
                    await asyncio.sleep(self.pause)
                return url, response.status_code, response.json()
            if response.status_code in {403, 404}:
                return url, response.status_code, {"detail": response.text[:500]}
            wait = min(60, (2**attempt) + random.random())
            print(f"retry status={response.status_code} url={url} wait={wait:.1f}s", flush=True)
            await asyncio.sleep(wait)
        response.raise_for_status()

    async def store_raw(self, resource_type, resource_id, url, status_code, payload, event=None, page=None):
        await self.db.execute(
            """
            INSERT INTO raw_api_responses
                (resource_type, resource_id, event, page, url, status_code, payload, fetched_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, now())
            ON CONFLICT (source, resource_type, resource_id)
            DO UPDATE SET
                event = EXCLUDED.event,
                page = EXCLUDED.page,
                url = EXCLUDED.url,
                status_code = EXCLUDED.status_code,
                payload = EXCLUDED.payload,
                fetched_at = now()
            """,
            resource_type,
            str(resource_id),
            event,
            page,
            url,
            status_code,
            json_dumps(payload),
        )

    async def sync_static(self):
        url, status, bootstrap = await self.fetch_json("/bootstrap-static/")
        await self.store_raw("bootstrap", "latest", url, status, bootstrap)
        current_event = next((event["id"] for event in bootstrap["events"] if event.get("is_current")), None)
        await self.db.execute(
            """
            INSERT INTO fpl_bootstrap_snapshots
                (current_event, player_count, team_count, event_count, payload)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            current_event,
            len(bootstrap.get("elements", [])),
            len(bootstrap.get("teams", [])),
            len(bootstrap.get("events", [])),
            json_dumps(bootstrap),
        )

        url, status, fixtures = await self.fetch_json("/fixtures/")
        await self.store_raw("fixtures", "latest", url, status, fixtures)
        await self.db.execute(
            "INSERT INTO fixtures_snapshots (fixture_count, payload) VALUES ($1, $2::jsonb)",
            len(fixtures),
            json_dumps(fixtures),
        )

        events = [event["id"] for event in bootstrap.get("events", [])]
        for event_id in events:
            url, status, payload = await self.fetch_json(f"/event/{event_id}/live/")
            await self.store_raw("event_live", event_id, url, status, payload, event=event_id)
            if status == 200:
                await self.db.execute(
                    """
                    INSERT INTO event_live (event, payload, fetched_at)
                    VALUES ($1, $2::jsonb, now())
                    ON CONFLICT (event)
                    DO UPDATE SET payload = EXCLUDED.payload, fetched_at = now()
                    """,
                    event_id,
                    json_dumps(payload),
                )
            print(f"static event_live {event_id}/{len(events)}", flush=True)

        player_ids = [element["id"] for element in bootstrap.get("elements", [])]
        await self.map_limited(player_ids, self.sync_element_summary, "element summaries")

    async def sync_element_summary(self, element_id):
        url, status, payload = await self.fetch_json(f"/element-summary/{element_id}/")
        await self.store_raw("element_summary", element_id, url, status, payload)
        if status != 200:
            return
        await self.db.execute(
            """
            INSERT INTO element_summaries
                (element, fixtures_rows, history_rows, history_past_rows, payload, fetched_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, now())
            ON CONFLICT (element)
            DO UPDATE SET
                fixtures_rows = EXCLUDED.fixtures_rows,
                history_rows = EXCLUDED.history_rows,
                history_past_rows = EXCLUDED.history_past_rows,
                payload = EXCLUDED.payload,
                fetched_at = now()
            """,
            element_id,
            len(payload.get("fixtures", [])),
            len(payload.get("history", [])),
            len(payload.get("history_past", [])),
            json_dumps(payload),
        )

    async def sync_kenya_standings(self, start_page=1, max_pages=None):
        page = start_page
        while True:
            url, status, payload = await self.fetch_json(
                f"/leagues-classic/{KENYA_LEAGUE_ID}/standings/?page_standings={page}"
            )
            await self.store_raw("kenya_standings_page", page, url, status, payload, page=page)
            if status != 200:
                print(f"standings page {page} failed status={status}", flush=True)
                break

            standings = payload.get("standings", {})
            results = standings.get("results", [])
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    for row in results:
                        await conn.execute(
                            """
                            INSERT INTO kenya_standings
                                (league_id, page, entry, entry_name, player_name, rank, last_rank,
                                 rank_sort, total, event_total, has_played, club_badge_src, raw, fetched_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb, now())
                            ON CONFLICT (league_id, entry)
                            DO UPDATE SET
                                page = EXCLUDED.page,
                                entry_name = EXCLUDED.entry_name,
                                player_name = EXCLUDED.player_name,
                                rank = EXCLUDED.rank,
                                last_rank = EXCLUDED.last_rank,
                                rank_sort = EXCLUDED.rank_sort,
                                total = EXCLUDED.total,
                                event_total = EXCLUDED.event_total,
                                has_played = EXCLUDED.has_played,
                                club_badge_src = EXCLUDED.club_badge_src,
                                raw = EXCLUDED.raw,
                                fetched_at = now()
                            """,
                            KENYA_LEAGUE_ID,
                            page,
                            row.get("entry"),
                            row.get("entry_name"),
                            row.get("player_name"),
                            row.get("rank"),
                            row.get("last_rank"),
                            row.get("rank_sort"),
                            row.get("total"),
                            row.get("event_total"),
                            row.get("has_played"),
                            row.get("club_badge_src"),
                            json_dumps(row),
                        )

            print(f"standings page={page} rows={len(results)} has_next={standings.get('has_next')}", flush=True)
            if max_pages and page >= start_page + max_pages - 1:
                break
            if not standings.get("has_next"):
                break
            page += 1

    async def pending_entries(self, table_name, limit=None):
        sql = f"""
            SELECT ks.entry
            FROM kenya_standings ks
            LEFT JOIN {table_name} existing ON existing.entry = ks.entry
            WHERE ks.league_id = $1 AND existing.entry IS NULL
            ORDER BY ks.rank NULLS LAST
        """
        args = [KENYA_LEAGUE_ID]
        if limit:
            sql += " LIMIT $2"
            args.append(limit)
        rows = await self.db.fetch(sql, *args)
        return [row["entry"] for row in rows]

    async def sync_manager_profile(self, entry):
        url, status, payload = await self.fetch_json(f"/entry/{entry}/")
        await self.store_raw("manager_profile", entry, url, status, payload)
        if status != 200:
            return
        await self.db.execute(
            """
            INSERT INTO managers
                (entry, player_first_name, player_last_name, player_region_id, player_region_name,
                 player_region_iso_code, summary_overall_points, summary_overall_rank,
                 summary_event_points, current_event, raw, fetched_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,now())
            ON CONFLICT (entry)
            DO UPDATE SET
                player_first_name = EXCLUDED.player_first_name,
                player_last_name = EXCLUDED.player_last_name,
                player_region_id = EXCLUDED.player_region_id,
                player_region_name = EXCLUDED.player_region_name,
                player_region_iso_code = EXCLUDED.player_region_iso_code,
                summary_overall_points = EXCLUDED.summary_overall_points,
                summary_overall_rank = EXCLUDED.summary_overall_rank,
                summary_event_points = EXCLUDED.summary_event_points,
                current_event = EXCLUDED.current_event,
                raw = EXCLUDED.raw,
                fetched_at = now()
            """,
            entry,
            payload.get("player_first_name"),
            payload.get("player_last_name"),
            payload.get("player_region_id"),
            payload.get("player_region_name"),
            payload.get("player_region_iso_code"),
            payload.get("summary_overall_points"),
            payload.get("summary_overall_rank"),
            payload.get("summary_event_points"),
            payload.get("current_event"),
            json_dumps(payload),
        )

    async def sync_manager_history(self, entry):
        url, status, payload = await self.fetch_json(f"/entry/{entry}/history/")
        await self.store_raw("manager_history", entry, url, status, payload)
        if status != 200:
            return
        await self.db.execute(
            """
            INSERT INTO manager_history
                (entry, current_rows, past_rows, chips_rows, raw, fetched_at)
            VALUES ($1,$2,$3,$4,$5::jsonb,now())
            ON CONFLICT (entry)
            DO UPDATE SET
                current_rows = EXCLUDED.current_rows,
                past_rows = EXCLUDED.past_rows,
                chips_rows = EXCLUDED.chips_rows,
                raw = EXCLUDED.raw,
                fetched_at = now()
            """,
            entry,
            len(payload.get("current", [])),
            len(payload.get("past", [])),
            len(payload.get("chips", [])),
            json_dumps(payload),
        )

    async def sync_manager_transfers(self, entry):
        url, status, payload = await self.fetch_json(f"/entry/{entry}/transfers/")
        await self.store_raw("manager_transfers", entry, url, status, payload)
        if status != 200:
            return
        await self.db.execute(
            """
            INSERT INTO manager_transfers (entry, transfer_rows, raw, fetched_at)
            VALUES ($1,$2,$3::jsonb,now())
            ON CONFLICT (entry)
            DO UPDATE SET transfer_rows = EXCLUDED.transfer_rows, raw = EXCLUDED.raw, fetched_at = now()
            """,
            entry,
            len(payload) if isinstance(payload, list) else 0,
            json_dumps(payload),
        )

    async def sync_manager_picks(self, entry, event):
        url, status, payload = await self.fetch_json(f"/entry/{entry}/event/{event}/picks/")
        await self.store_raw("manager_picks", f"{entry}:{event}", url, status, payload, event=event)
        if status != 200:
            return
        await self.db.execute(
            """
            INSERT INTO manager_picks
                (entry, event, picks_rows, automatic_subs_rows, raw, fetched_at)
            VALUES ($1,$2,$3,$4,$5::jsonb,now())
            ON CONFLICT (entry, event)
            DO UPDATE SET
                picks_rows = EXCLUDED.picks_rows,
                automatic_subs_rows = EXCLUDED.automatic_subs_rows,
                raw = EXCLUDED.raw,
                fetched_at = now()
            """,
            entry,
            event,
            len(payload.get("picks", [])),
            len(payload.get("automatic_subs", [])),
            json_dumps(payload),
        )

    async def map_limited(self, items, func, label):
        total = len(items)
        done = 0

        async def wrapped(item):
            nonlocal done
            try:
                await func(item)
            except Exception as exc:
                print(f"{label} item={item} error={exc}", flush=True)
            done += 1
            if done % 100 == 0 or done == total:
                print(f"{label} {done}/{total}", flush=True)

        await asyncio.gather(*(wrapped(item) for item in items))

    async def sync_profiles(self, limit=None):
        entries = await self.pending_entries("managers", limit)
        await self.map_limited(entries, self.sync_manager_profile, "manager profiles")

    async def sync_histories(self, limit=None):
        entries = await self.pending_entries("manager_history", limit)
        await self.map_limited(entries, self.sync_manager_history, "manager histories")

    async def sync_transfers(self, limit=None):
        entries = await self.pending_entries("manager_transfers", limit)
        await self.map_limited(entries, self.sync_manager_transfers, "manager transfers")

    async def sync_picks(self, events, limit=None):
        rows = await self.db.fetch(
            """
            SELECT ks.entry, e.event
            FROM kenya_standings ks
            CROSS JOIN unnest($1::int[]) AS e(event)
            LEFT JOIN manager_picks mp ON mp.entry = ks.entry AND mp.event = e.event
            WHERE ks.league_id = $2 AND mp.entry IS NULL
            ORDER BY ks.rank NULLS LAST, e.event
            LIMIT $3
            """,
            events,
            KENYA_LEAGUE_ID,
            limit or 1000000000,
        )
        items = [(row["entry"], row["event"]) for row in rows]

        async def one(item):
            entry, event = item
            await self.sync_manager_picks(entry, event)

        await self.map_limited(items, one, "manager picks")


async def run_job(args):
    db = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=max(4, args.concurrency + 2))
    collector = Collector(db, concurrency=args.concurrency, pause=args.pause)
    run_id = await db.fetchval(
        "INSERT INTO collection_runs (job_name) VALUES ($1) RETURNING id",
        args.job,
    )
    stats = {}
    try:
        if args.job == "static":
            await collector.sync_static()
        elif args.job == "standings":
            await collector.sync_kenya_standings(start_page=args.start_page, max_pages=args.max_pages)
        elif args.job == "profiles":
            await collector.sync_profiles(limit=args.limit)
        elif args.job == "histories":
            await collector.sync_histories(limit=args.limit)
        elif args.job == "transfers":
            await collector.sync_transfers(limit=args.limit)
        elif args.job == "picks":
            events = list(range(args.event_start, args.event_end + 1))
            await collector.sync_picks(events, limit=args.limit)
        elif args.job == "core":
            await collector.sync_static()
            await collector.sync_kenya_standings(start_page=args.start_page, max_pages=args.max_pages)
            await collector.sync_profiles(limit=args.limit)
            await collector.sync_histories(limit=args.limit)
        else:
            raise ValueError(f"unknown job: {args.job}")

        counts = await db.fetchrow(
            """
            SELECT
                (SELECT count(*) FROM kenya_standings) AS standings,
                (SELECT count(*) FROM managers) AS profiles,
                (SELECT count(*) FROM manager_history) AS histories,
                (SELECT count(*) FROM manager_transfers) AS transfers,
                (SELECT count(*) FROM manager_picks) AS picks,
                (SELECT count(*) FROM raw_api_responses) AS raw
            """
        )
        stats = dict(counts)
        await db.execute(
            "UPDATE collection_runs SET finished_at=now(), status='finished', stats=$2::jsonb WHERE id=$1",
            run_id,
            json_dumps(stats),
        )
    except Exception as exc:
        await db.execute(
            "UPDATE collection_runs SET finished_at=now(), status='failed', stats=$2::jsonb, error=$3 WHERE id=$1",
            run_id,
            json_dumps(stats),
            repr(exc),
        )
        raise
    finally:
        await collector.close()
        await db.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Collect Fantasy Premier League Kenya data.")
    parser.add_argument("job", choices=["static", "standings", "profiles", "histories", "transfers", "picks", "core"])
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--pause", type=float, default=0.05)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--event-start", type=int, default=1)
    parser.add_argument("--event-end", type=int, default=38)
    return parser.parse_args()


if __name__ == "__main__":
    if "DATABASE_URL" not in os.environ:
        print("DATABASE_URL is required", file=sys.stderr)
        sys.exit(2)
    asyncio.run(run_job(parse_args()))
