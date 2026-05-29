# FPL Kenya

Fantasy Premier League data and analysis for Kenyan managers.

The project has two parts:

- `frontend/`: Next.js dashboard.
- root Python files: collector, API, schema, and analytics SQL used to build the dataset.

## Frontend

```bash
cd frontend
npm ci
npm run dev
```

For production, set:

```bash
FPLKE_API_BASE=https://your-public-api-host
NEXT_PUBLIC_BASE_PATH=
```

`NEXT_PUBLIC_BASE_PATH` is empty on Vercel. It is only set when the app is served under a subpath.

## Data Pipeline

The collector stores official public FPL API responses as JSONB and indexes the fields used by the dashboard.

Main jobs:

```bash
python collect_fplke.py static
python collect_fplke.py standings
python collect_fplke.py profiles
python collect_fplke.py histories
```

`core` runs `static`, `standings`, `profiles`, and `histories`.

The Kenya country league is `131`; the Kenya region id observed from manager profiles is `111`.

## Deployment Notes

The Vercel project should use `frontend` as its root directory. The project config lives in `frontend/vercel.json`.

Required Vercel environment variables:

```bash
FPLKE_API_BASE=http://38.242.228.254/fplke-data
NEXT_PUBLIC_BASE_PATH=
```

CLI deploy:

```bash
npx vercel deploy --prod --cwd frontend --local-config frontend/vercel.json
```

Do not commit VPS operation notes, SSH commands, `.env` files, deployment bundles, or generated archives.
