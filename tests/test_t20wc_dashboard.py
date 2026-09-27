import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class T20WorldCupDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data/t20wc_deliveries.json").read_text(encoding="utf-8"))

    def test_delivery_archive_is_complete_for_played_afghanistan_matches(self):
        self.assertGreaterEqual(self.data["meta"]["matches"], 368)
        self.assertGreaterEqual(self.data["meta"]["deliveries"], 84000)
        self.assertEqual(34, len(self.data["reconciliation"]))
        self.assertTrue(all(check["passed"] for check in self.data["reconciliation"]))
        self.assertEqual({"no play"}, {gap["reason"] for gap in self.data["gaps"]})
        self.assertEqual(10, len(self.data["gaps"]))
        self.assertEqual(378, self.data["meta"]["fixtures"])
        self.assertEqual(10, self.data["meta"]["no_play"])

    def test_schema_supports_batting_bowling_and_phase_analysis(self):
        fields = set(self.data["fields"])
        self.assertTrue({
            "match_id", "edition", "innings", "super_over", "over", "batter", "bowler",
            "batter_runs", "total_runs", "bowler_runs", "legal", "batter_ball",
            "wicket", "bowler_wicket", "wicket_kind", "player_out", "source",
        }.issubset(fields))
        self.assertEqual("2007-09-11", self.data["meta"]["first_delivery_date"])
        self.assertEqual("2026-03-08", self.data["meta"]["last_delivery_date"])
        self.assertEqual([2007, 2009, 2010, 2012, 2014, 2016, 2021, 2022, 2024, 2026], self.data["meta"]["editions"])
        self.assertEqual(4, self.data["meta"]["super_over_matches"])
        self.assertEqual(57, self.data["meta"]["super_over_deliveries"])

    def test_published_rows_do_not_retain_commentary_prose(self):
        forbidden = {"text", "shortText", "commentary", "description"}
        self.assertFalse(forbidden.intersection(self.data["fields"]))
        self.assertTrue(all(len(row) == len(self.data["fields"]) for row in self.data["deliveries"]))

    def test_afghanistan_manual_files_are_factual_and_rebuildable(self):
        manual = sorted((ROOT / "data/t20wc_manual").glob("*.json"))
        self.assertEqual(34, len(manual))
        for path in manual:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(self.data["fields"], payload["fields"])
            self.assertNotIn("commentary", payload)
            self.assertTrue(payload["deliveries"])

    def test_every_played_match_has_a_separate_delivery_file(self):
        files = sorted((ROOT / "data/t20wc_matches").glob("*.json"))
        self.assertEqual(378, len(files))
        expected_ids = {match["id"] for match in self.data["matches"]} | {match["id"] for match in self.data["gaps"]}
        self.assertEqual(expected_ids, {path.stem for path in files})
        delivery_count = 0
        super_over_count = 0
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(path.stem, payload["match"]["id"])
            self.assertEqual(self.data["fields"], payload["fields"])
            self.assertEqual(len(payload["deliveries"]), payload["counts"]["deliveries"])
            delivery_count += payload["counts"]["deliveries"]
            super_over_count += payload["counts"]["super_over"]
        self.assertEqual(self.data["meta"]["deliveries"], delivery_count)
        self.assertEqual(self.data["meta"]["super_over_deliveries"], super_over_count)


if __name__ == "__main__":
    unittest.main()
