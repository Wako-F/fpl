# FPL Kenya data desk

Season-aware Fantasy Premier League data, analysis, and weekly editorial tooling for Kenyan managers.

The active product covers **2026/27**. The legacy API remains available to power the frozen 2025/26 archive.

## Architecture

- `fplke_pipeline.py`: season-aware official FPL collector.
- `migrations/`: additive PostgreSQL migrations.
- `fplke_api.py`: FastAPI legacy and `/v2` read APIs.
- `generate_weekly_content.py`: deterministic weekly facts and editorial drafts.
- `frontend/`: Next.js 16 website.
- `systemd/`: production ingestion and content timers.
- `tests/`: backend contract and content tests.

## Local setup

Create a PostgreSQL database and Redis instance, copy `.env.example` to `.env`, then run:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
psql "$DATABASE_URL" -f schema.sql
psql "$DATABASE_URL" -f migrations/001_season_platform.sql
psql "$DATABASE_URL" -f migrations/002_full_country_crawls.sql
python fplke_pipeline.py bootstrap
python fplke_pipeline.py standings --max-pages 20
python fplke_pipeline.py live
python fplke_pipeline.py cohort --cohort-size 100 --include-picks
python generate_weekly_content.py
uvicorn fplke_api:app --reload --port 8010
```

On Windows, activate the virtual environment with `.venv\Scripts\Activate.ps1` and run the equivalent commands.

Start the frontend separately:

```bash
cd frontend
npm ci
copy .env.example .env.local
npm run dev
```

## Data scope

The live pipeline uses a bounded standings crawl and a 1,000-manager deep cohort. A checkpointed
full-country crawl runs once per completed gameweek so the published national table can include
every Kenyan manager. See [`FULL_COUNTRY_STRATEGY.md`](FULL_COUNTRY_STRATEGY.md) for the workload
split, completeness contract, and operating tactics.

- National scores and ranks: latest captured Kenya country-league snapshot.
- Captaincy, chips, picks, transfers, and bench behaviour: declared deep cohort.
- Live player scores: official event live endpoint.
- Generated content: labelled `live`, `provisional`, or `final` with lineage and sample size.

## Weekly operation

During the gameweek:

```bash
python fplke_pipeline.py bootstrap
python fplke_pipeline.py live
python fplke_pipeline.py standings --max-pages 200
```

After the gameweek lock:

```bash
scripts/run_postlock.sh
```

This refreshes static data and standings, updates the manager cohort and picks, and writes the article, social, engineering, and machine-readable briefs under `content/generated/`.

## Production control room

The read-only VPS cockpit is served at `/fplke/ops`. It shows complete-crawl progress, published
coverage, data freshness, quality checks, recent pipeline runs, and previews of the generated
article, social, engineering, and JSON artifacts. It does not expose credentials or raw logs.

## Verification

```bash
python -m py_compile collect_fplke.py fplke_pipeline.py fplke_settings.py fplke_api.py generate_weekly_content.py
python -m unittest discover -s tests -v
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

## Deployment

The frontend project root is `frontend`. Configure these Vercel environment variables in the project rather than committing them:

```text
FPLKE_API_BASE=https://your-api-domain.example.com
NEXT_PUBLIC_BASE_PATH=
NEXT_PUBLIC_SITE_URL=https://your-site.example.com
```

See `VPS_OPERATIONS.md` for backend deployment, schedules, verification, rollback, and GW1 handover.

FPL Kenya is independent and is not affiliated with or endorsed by the Premier League.
