# Full-country FPL Kenya collection strategy

## What “everybody” means

The Kenya classic league currently contains roughly 275,718 public entries across 5,515
standings pages. The platform collects the complete national standings table: entry ID,
public team and manager labels, Kenya rank, previous rank, total points, gameweek points,
and played state.

Manager profile, history, and picks endpoints are a separate workload. Bulk-fetching those
for every entry would require between 550,000 and 825,000 requests per gameweek. That is
not operationally responsible. The platform therefore uses:

- complete national standings for every manager;
- a declared, reproducible deep cohort for behavioural analysis;
- manager detail already cached in the warehouse when a profile has been collected;
- on-demand enrichment as the future extension for managers someone actually views.

The public interface must never describe cohort behaviour as behaviour from all Kenyan
managers.

## Refresh tiers

### Live head crawl

- First 200 pages, approximately 10,000 unique entries.
- Runs every two hours while rankings can move.
- Gives fast leaders and live national context without repeatedly walking the whole league.
- Always labelled `bounded` and never presented as complete coverage.

### Complete country crawl

- Runs once per gameweek after official FPL `data_checked` becomes true.
- Discovers the terminal page with exponential search followed by binary search.
- Fetches the complete page range with bounded concurrency.
- Publishes only after every page passes validation.
- The morning timer retries until the current gameweek has one complete snapshot, then skips.

### Live player data

- One event-live endpoint every five minutes.
- Independent from standings collection.
- Keeps player scores fresh without multiplying manager requests.

### Behavioural cohort

- Profile, history, chip, and pick data for a declared cohort.
- Used for captaincy, bench, transfer, and chip analysis.
- Every published fact includes its sample size and source snapshot.

## Efficiency and resilience techniques

1. **Boundary discovery** — find the last page in logarithmic time instead of crawling until
   an empty page appears.
2. **Bounded concurrency** — four workers by default, controlled through
   `FPLKE_CONCURRENCY`; this shortens wall time without creating an aggressive request burst.
3. **Backoff and jitter** — retry transient failures up to five times with exponential delays.
4. **Request pacing** — a configurable pause follows successful requests.
5. **Page checkpoints** — every page records pending/running/finished/failed state, attempts,
   row count, duration, and fetch time.
6. **Resume** — an interrupted crawl resumes missing or failed pages from a recent snapshot.
7. **Immutable raw lineage** — source responses retain URL, event, page, hash, timestamp, and
   payload for reproducibility.
8. **Idempotent page writes** — retrying a page replaces that page's canonical rows inside a
   transaction.
9. **Atomic publication** — running or failed snapshots never enter the public latest-snapshot
   view.
10. **Completeness proof** — publication requires a contiguous page set, a verified terminal
    page, the expected raw row count, zero failed pages, and at least the expected number of
    unique entry IDs.
11. **Moving-rank repair** — when ranks shift during collection, subsequent passes are unioned
    into the same snapshot until cross-page gaps are closed.
12. **One final snapshot per event** — `--if-needed` skips repeat work only after a complete
    snapshot captured with official `data_checked=true` exists.
13. **Workload separation** — full standings, fast standings, live players, and deep manager
    data run on different schedules and can fail independently.
14. **Search indexes** — entry ID plus trigram indexes keep all-country team/manager lookup
    responsive at hundreds of thousands of rows.
15. **Publication labels** — the UI distinguishes fast live slices from complete country
    tables and live/provisional/final content.

## Completeness contract

A full snapshot is publishable only when:

```text
finished_pages == expected_pages
failed_pages == 0
rows_fetched == expected_rows
unique_entries >= expected_rows
terminal_page.has_next == false
```

If a live crawl has cross-page gaps, bounded repair passes first union newly observed entries
into the same snapshot. If an invariant still fails, the crawl is marked failed and the
previously published snapshot remains live.

## Operational commands

Start or resume a full crawl regardless of event status:

```bash
python fplke_pipeline.py standings --max-pages 0 --resume
```

Safe scheduled form—wait for official checks and skip duplicate work:

```bash
python fplke_pipeline.py standings --max-pages 0 --resume \
  --require-data-checked --if-needed
```

Run the fast live slice:

```bash
python fplke_pipeline.py standings --max-pages 200
```

## Capacity and retention

The current VPS has enough headroom for one canonical full snapshot per gameweek. Full crawls
must not run every two hours: that would create avoidable API traffic and database growth.
At season end, retain final full snapshots and their content lineage; bounded intra-gameweek
snapshots can be compacted after an explicit backup and retention review.

## Project cockpit

`/fplke/ops` reads safe state from `/v2/ops` and the generated artifact endpoints. It shows:

- current published coverage;
- complete-crawl progress and heartbeat;
- live/bootstrap/fixture/standings freshness;
- quality results and recent pipeline runs;
- article, social, engineering, and JSON content-pack previews.

It intentionally excludes credentials, environment values, raw logs, and database connection
details.
