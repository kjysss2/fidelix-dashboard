import copy
import unittest
from unittest.mock import patch

import server


LISTING = """
<a href="/tw/press-room/4IMHLL2IMP?category=investor-Info">
  晶豪科技2026年07月份營收報告
  晶豪科技股份有限公司今(04)日公布2026年07月合併營業收入報告，
  合併營收入為新台幣67.85億元，較去年同期增加491.06%。
</a>
"""

RELEASE = """
<h1>晶豪科技2026年07月份營收報告</h1>
<p>晶豪科技股份有限公司今(04)日公布2026年07月合併營業收入報告，
合併營收入為新台幣67.85億元，較去年同期增加491.06%；
當年累計合併營業收入為新台幣279.98億元，較去年同期增加281.48%。</p>
"""


class EsmtMonthlyRefreshTests(unittest.TestCase):
    def test_finds_latest_official_release(self):
        self.assertEqual(
            server.find_esmt_latest_monthly_release(LISTING),
            (
                "2026-07",
                "https://www.esmt.com.tw/tw/press-room/4IMHLL2IMP?category=investor-Info",
            ),
        )

    def test_parses_official_release(self):
        item = server.parse_esmt_monthly_release(
            RELEASE,
            "2026-07",
            "https://www.esmt.com.tw/tw/press-room/4IMHLL2IMP",
        )
        self.assertIsNotNone(item)
        self.assertEqual(item["revenue"], 6785.0)
        self.assertEqual(item["yoy"], 491.06)
        self.assertIsNone(item["mom"])

    @patch(
        "server.fetch_bytes",
        side_effect=[LISTING.encode("utf-8"), RELEASE.encode("utf-8")],
    )
    def test_refreshes_esmt_and_derives_mom(self, _bytes):
        data = copy.deepcopy(server.SERVICE.dashboard)
        esmt = next(company for company in data["companies"] if company["id"] == "esmt")
        esmt["metrics"]["period"] = "2026-06"
        esmt["monthlyHistory"] = [{
            "period": "2026-06",
            "revenue": 4845.479,
            "mom": 8.48,
            "yoy": 328.35,
        }]

        self.assertTrue(server.SERVICE._refresh_esmt_official_monthly(data))

        self.assertEqual(esmt["metrics"]["period"], "2026-07")
        self.assertEqual(esmt["metrics"]["revenue"], 6785.0)
        self.assertEqual(esmt["metrics"]["revenueDisplay"], "NT$ 67.9억")
        self.assertAlmostEqual(esmt["metrics"]["revenueQoQ"], 40.03, places=2)
        self.assertEqual(esmt["metrics"]["revenueYoY"], 491.06)
        self.assertEqual(esmt["monthlyHistory"][-1]["period"], "2026-07")
        self.assertEqual(esmt["sourceLabel"], "ESMT official IR")

    @patch.object(server.SERVICE, "_fetch_mops_period")
    def test_history_refresh_keeps_each_company_latest_month(self, fetch_period):
        data = copy.deepcopy(server.SERVICE.dashboard)
        before = {
            company["id"]: company["monthlyHistory"][-1]["period"]
            for company in data["companies"]
            if company["id"] in {"winbond", "nanya", "macronix", "esmt"}
        }

        server.SERVICE._refresh_mops_history(data)

        after = {
            company["id"]: company["monthlyHistory"][-1]["period"]
            for company in data["companies"]
            if company["id"] in {"winbond", "nanya", "macronix", "esmt"}
        }
        self.assertEqual(after, before)
        fetch_period.assert_not_called()


if __name__ == "__main__":
    unittest.main()
