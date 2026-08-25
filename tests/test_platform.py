import os
import unittest
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "postgresql://example:example@127.0.0.1/example")

from fplke_api import app  # noqa: E402
from fplke_pipeline import datetime_or_none, decimal_or_none  # noqa: E402
from generate_weekly_content import manager_label, render_engineering, render_social  # noqa: E402


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
            "leader": {"entry_name": "Nairobi Press", "total": 52},
            "cohort": {"avg_points": "31.20", "median_points": "30", "managers": 1000},
            "topPlayers": [{"web_name": "Player", "total_points": 12}],
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


if __name__ == "__main__":
    unittest.main()
