# FPL Kenya weekly content

Each gameweek produces a deterministic editorial pack from the season-aware database:

```bash
python generate_weekly_content.py --event 1
```

Output is written to `content/generated/<season>/gw-<event>/`:

- `brief.json`: machine-readable facts, samples, freshness, and lineage.
- `article.md`: the website/newsletter source draft.
- `social.md`: short copy, carousel outline, and alt text.
- `engineering.md`: the weekly data engineering/build-in-public note.

Generated copy is a draft. Check the status (`live`, `provisional`, or `final`), manager names, and data-quality results before publishing.
