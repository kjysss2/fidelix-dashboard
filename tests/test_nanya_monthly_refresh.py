import copy
import unittest
from unittest.mock import patch

import server


LISTING = """
<a href="/en/IR/16/?IRId=13150">
  Nanya Technology Reports Results for the Second Quarter 2026
</a>
<a href="/en/IR/16/?IRId=13157">
  Nanya Technology July 2026 Revenue NT$ 43,868 Million&nbsp;
</a>
"""

RELEASE = """
<p>2026/08/04</p>
<h1>Nanya Technology July 2026 Revenue NT$ 43,868 Million</h1>
<p>August 4, 2026 – Nanya Technology Corporation today announced its
unaudited consolidated net sales revenue of NT$ 43,868 million for July 2026,
representing a 49.27% increase month-over-month, 719.61% increase year-over-year.</p>
"""


class NanyaMonthlyRefreshTests(unittest.TestCase):
    def test_finds_latest_monthly_release(self):
        self.assertEqual(
            server.find_nanya_latest_monthly_release(LISTING, 2026),
            ("2026-07", "https://www.nanya.com/en/IR/16/?IRId=13157"),
        )

    def test_parses_official_monthly_release(self):
        item = server.parse_nanya_monthly_release(
            RELEASE,
            "2026-07",
            "https://www.nanya.com/en/IR/16/?IRId=13157",
        )
        self.assertIsNotNone(item)
        self.assertEqual(item["revenue"], 43868.0)
        self.assertEqual(item["mom"], 49.27)
        self.assertEqual(item["yoy"], 719.61)

    @patch("server.fetch_bytes", return_value=RELEASE.encode("utf-8"))
    @patch("server.fetch_json", return_value={"msg": LISTING})
    def test_refreshes_stale_nanya_month_without_touching_peers(self, _json, _bytes):
        data = copy.deepcopy(server.SERVICE.dashboard)
        nanya = next(company for company in data["companies"] if company["id"] == "nanya")
        nanya["metrics"]["period"] = "2026-06"
        nanya["monthlyHistory"] = [
            item for item in nanya["monthlyHistory"] if item["period"] <= "2026-06"
        ]
        before_peers = {
            company["id"]: copy.deepcopy(company)
            for company in data["companies"]
            if company["id"] != "nanya"
        }

        self.assertTrue(server.SERVICE._refresh_nanya_official_monthly(data))

        self.assertEqual(nanya["metrics"]["period"], "2026-07")
        self.assertEqual(nanya["metrics"]["revenue"], 43868.0)
        self.assertEqual(nanya["metrics"]["revenueDisplay"], "NT$ 438.7억")
        self.assertEqual(nanya["sourceUrl"], "https://www.nanya.com/en/IR/16/?IRId=13157")
        self.assertEqual(nanya["monthlyHistory"][-1], {
            "period": "2026-07",
            "revenue": 43868.0,
            "mom": 49.27,
            "yoy": 719.61,
        })
        self.assertEqual(
            before_peers,
            {
                company["id"]: company
                for company in data["companies"]
                if company["id"] != "nanya"
            },
        )

    @patch("server.fetch_json", return_value={"msg": LISTING})
    def test_does_not_replace_same_or_newer_twse_period(self, _json):
        data = copy.deepcopy(server.SERVICE.dashboard)
        nanya = next(company for company in data["companies"] if company["id"] == "nanya")
        nanya["metrics"]["period"] = "2026-07"

        self.assertFalse(server.SERVICE._refresh_nanya_official_monthly(data))


if __name__ == "__main__":
    unittest.main()
