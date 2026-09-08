# FPL Kenya weekly content

Each gameweek produces a deterministic editorial pack from the season-aware database:

```bash
python generate_weekly_content.py --event 1
```

Output is written to `content/generated/<season>/gw-<event>/`:

- `brief.json`: machine-readable facts, samples, freshness, and lineage.
- `article.md`: the website/newsletter source draft.
- `analysis.md`: evidence, interpretation, and caveats for the week's main signals.
- `social.md`: short copy, carousel outline, and alt text.
- `engineering.md`: the weekly data engineering/build-in-public note.
- `manifest.json`: byte sizes and SHA-256 checksums for reproducibility.
- `visualizations/*.svg`: decision dashboard, score distribution, captaincy,
  player performance, and rank-movement graphics where the source data exists.

Generate every completed gameweek after cohort backfill:

```bash
python fplke_pipeline.py cohort --cohort-size 1000 --include-picks --all-completed --if-needed
python generate_weekly_content.py --all-completed
```

Generation fails closed when history or picks coverage is below
`FPLKE_CONTENT_MIN_COHORT_SIZE`; incomplete packs are not silently published.

Generated copy is a draft. Check the status (`live`, `provisional`, or `final`), manager names, and data-quality results before publishing.
