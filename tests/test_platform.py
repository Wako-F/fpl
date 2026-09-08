import os
import tempfile
import unittest
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "postgresql://example:example@127.0.0.1/example")

from fplke_api import app  # noqa: E402
from fplke_pipeline import SeasonPipeline, datetime_or_none, decimal_or_none  # noqa: E402
from generate_weekly_content import (  # noqa: E402
    dashboard_svg,
    manager_label,
    render_analysis,
    render_engineering,
    render_social,
    write_pack,
)


class PipelineHelpersTest(unittest.TestCase):
    def test_decimal_normalisation(self):
        self.assertEqual(decimal_or_none("12.5"), Decimal("12.5"))
        self.assertIsNone(decimal_or_none(""))
        self.assertIsNone(decimal_or_none("not-a-number"))

    def test_iso_timestamp_normalisation(self):
        value = datetime_or_none("2026-08-21T17:30:00Z")
        self.assertEqual(value.isoformat(), "2026-08-21T17:30:00+00:00")
        self.assertIsNone(datetime_or_none(None))

    def test_manager_label_fallbacks(self):
        self.assertEqual(manager_label({"entry_name": "Mathare XI"}), "Mathare XI")
        self.assertEqual(manager_label({"entry": 42}), "Entry 42")
        self.assertEqual(manager_label(None), "Not available")


class ApiContractTest(unittest.TestCase):
    def test_required_v2_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        required = {
            "/v2/seasons",
            "/v2/status",
            "/v2/overview",
            "/v2/leaderboard",
            "/v2/players",
            "/v2/managers/{entry}",
            "/v2/gameweeks/{event}/content",
            "/v2/gameweeks/{event}/fixtures",
            "/v2/ops",
            "/v2/content-packs/{event}/{artifact}",
        }
        self.assertTrue(required.issubset(paths))


class ContentContractTest(unittest.TestCase):
    def setUp(self):
        self.pack = {
            "event": 1,
            "status": "live",
            "generatedAt": "2026-08-25T00:00:00+00:00",
            "leader": {"entry_name": "Nairobi Press", "total": 52},
            "weeklyLeader": {"entry_name": "Westlands XI", "points": 64},
            "cohort": {"avg_points": 31.2, "median_points": 30, "p90_points": 45, "managers": 1000},
            "eventDetails": {"average_entry_score": 29},
            "overview": {"managers": 10000},
            "samples": {"nationalManagers": 10000, "cohortManagers": 1000, "picksManagers": 980},
            "captains": [{"web_name": "Captain", "share_pct": 40, "managers": 392}],
            "topPlayers": [{"web_name": "Player", "short_name": "NBO", "total_points": 12, "minutes": 90}],
            "scoreDistribution": [{"bucket_start": 20, "managers": 100}],
            "transferBehaviour": {"managers": 1000, "hit_managers_pct": 10, "total_hit_points": 400, "avg_transfer_cost": 0.4},
            "benchBehaviour": {"avg_bench_points": 5, "total_bench_points": 5000, "double_digit_bench_pct": 12},
            "movers": [],
            "analysis": [{"title": "Signal", "finding": "Finding.", "evidence": "Evidence.", "caveat": "Caveat."}],
            "visualizations": [{"key": "decision-dashboard"}],
            "methodology": {"managerCohort": "Event-specific ranked cohort."},
            "snapshot": {"id": 7, "managers_collected": 10000, "is_complete": False},
        }

    def test_social_copy_labels_status(self):
        output = render_social(self.pack)
        self.assertIn("Status: live", output)
        self.assertIn("GW1", output)

    def test_engineering_copy_contains_lineage(self):
        output = render_engineering(self.pack)
        self.assertIn("Standings snapshot: `7`", output)
        self.assertIn("Season key: `2026-27`", output)

    def test_analysis_contains_evidence_and_caveat(self):
        output = render_analysis(self.pack)
        self.assertIn("**Evidence:** Evidence.", output)
        self.assertIn("**Interpretation note:** Caveat.", output)

    def test_svg_is_accessible(self):
        output = dashboard_svg(self.pack)
        self.assertIn('role="img"', output)
        self.assertIn("<title", output)
        self.assertIn("Cohort n=1,000", output)

    def test_pack_writes_manifest_and_visualizations(self):
        with tempfile.TemporaryDirectory() as directory:
            target = write_pack(self.pack, directory)
            self.assertTrue((target / "manifest.json").is_file())
            self.assertTrue((target / "analysis.md").is_file())
            self.assertTrue((target / "visualizations" / "captaincy.svg").is_file())
            manifest = (target / "manifest.json").read_text(encoding="utf-8")
            self.assertIn("sha256", manifest)


class CohortAccountingTest(unittest.IsolatedAsyncioTestCase):
    async def test_map_limited_counts_successes_not_attempts(self):
        pipeline = SeasonPipeline.__new__(SeasonPipeline)
        pipeline.concurrency = 2

        async def work(item):
            if item == 2:
                raise RuntimeError("expected")

        result = await pipeline.map_limited([1, 2, 3], work, "test")
        self.assertEqual(result["attempted"], 3)
        self.assertEqual(result["succeeded"], 2)
        self.assertEqual(result["failed"], 1)


if __name__ == "__main__":
    unittest.main()
