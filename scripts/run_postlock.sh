#!/usr/bin/env bash
set -euo pipefail

cd /opt/fplke
set -a
. /opt/fplke/.env
set +a

/opt/fplke/.venv/bin/python fplke_pipeline.py bootstrap
/opt/fplke/.venv/bin/python fplke_pipeline.py standings --max-pages 0 --resume --require-data-checked --if-needed
/opt/fplke/.venv/bin/python fplke_pipeline.py cohort --cohort-size 1000 --include-picks
/opt/fplke/.venv/bin/python generate_weekly_content.py

echo "post-lock coverage check and content pack generated"
