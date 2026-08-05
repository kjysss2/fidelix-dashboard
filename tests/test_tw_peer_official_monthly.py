import copy
import unittest
from unittest.mock import patch

import server


WINBOND_JUNE = """
<div>
  June 2026 Unit: NT$ 1,000 Revenue Consolidated(Note)
  2026 Jun 20,596,799
  2026 May 20,001,444
  Increase(Decrease) 2.98%
  2025 Jun 7,105,364
  Increase(Decrease) 189.88%
</div>
"""

WINBOND_JULY = """
<div>
  July 2026 Unit: NT$ 1,000 Revenue Consolidated(Note)
  2026 Jul 23,000,000
  2026 Jun 20,596,799
  Increase(Decrease) 11.67%
  2025 Jul 7,500,000
  Increase(Decrease) 206.67%
</div>
"""

MACRONIX_ROWS = [
    {
        "Year": "2026",
        "Month": "06",
        "Revenue": "6956348",
        "Revenue_LY": "2200717",
        "AnnounceDate": "2026/07/07",
    },
    {
        "Year": "2026",
        "Month": "07",
        "Revenue": "8000000",
        "Revenue_LY": "3000000",
        "AnnounceDate": "2026/08/07",
    },
]


class TaiwanPeerOfficialMonthlyTests(unittest.TestCase):
    def test_parses_winbond_official_page(self):
        item = server.parse_winbond_monthly_page(
            WINBOND_JUNE,
            server.WINBOND_MONTHLY_REVENUE_URL,
        )
        self.assertIsNotNone(item)
        self.assertEqual(item["period"], "2026-06")
        self.assertEqual(item["revenue"], 20596.799)
        self.assertEqual(item["mom"], 2.98)
        self.assertEqual(item["yoy"], 189.88)

    def test_parses_macronix_official_json(self):
        item = server.parse_macronix_monthly_rows(
            MACRONIX_ROWS,
            server.MACRONIX_MONTHLY_REVENUE_URL,
        )
        self.assertIsNotNone(item)
        self.assertEqual(item["period"], "2026-07")
        self.assertEqual(item["revenue"], 8000.0)
        self.assertAlmostEqual(item["mom"], 15.0029, places=4)
        self.assertAlmostEqual(item["yoy"], 166.6667, places=4)

    @patch("server.fetch_bytes", return_value=WINBOND_JULY.encode("utf-8"))
    def test_refreshes_newer_winbond_official_month(self, _bytes):
        data = copy.deepcopy(server.SERVICE.dashboard)
        winbond = next(company for company in data["companies"] if company["id"] == "winbond")
        winbond["metrics"]["period"] = "2026-06"
        winbond["monthlyHistory"] = [
            item for item in winbond["monthlyHistory"] if item["period"] <= "2026-06"
        ]

        self.assertTrue(server.SERVICE._refresh_winbond_official_monthly(data))
        self.assertEqual(winbond["metrics"]["period"], "2026-07")
        self.assertEqual(winbond["metrics"]["revenue"], 23000.0)
        self.assertEqual(winbond["monthlyHistory"][-1]["period"], "2026-07")
        self.assertEqual(winbond["sourceLabel"], "Winbond official IR")

    @patch("server.fetch_json", return_value=MACRONIX_ROWS)
    def test_refreshes_newer_macronix_official_month(self, _json):
        data = copy.deepcopy(server.SERVICE.dashboard)
        macronix = next(company for company in data["companies"] if company["id"] == "macronix")
        macronix["metrics"]["period"] = "2026-06"
        macronix["monthlyHistory"] = [
            item for item in macronix["monthlyHistory"] if item["period"] <= "2026-06"
        ]

        self.assertTrue(server.SERVICE._refresh_macronix_official_monthly(data))
        self.assertEqual(macronix["metrics"]["period"], "2026-07")
        self.assertEqual(macronix["metrics"]["revenue"], 8000.0)
        self.assertEqual(macronix["monthlyHistory"][-1]["period"], "2026-07")
        self.assertEqual(macronix["sourceLabel"], "Macronix official IR")

    @patch("server.fetch_json")
    def test_stale_twse_row_does_not_downgrade_official_month(self, fetch_json):
        def row(code, revenue):
            return {
                "出表日期": "1150805",
                "資料年月": "11506",
                "公司代號": code,
                "營業收入-當月營收": str(revenue),
                "營業收入-上月比較增減(%)": "1.0",
                "營業收入-去年同月增減(%)": "2.0",
                "備註": "",
            }

        fetch_json.return_value = [
            row("2344", 20596799),
            row("2408", 29388309),
            row("2337", 6956348),
        ]
        data = copy.deepcopy(server.SERVICE.dashboard)
        nanya = next(company for company in data["companies"] if company["id"] == "nanya")
        nanya["metrics"].update({"period": "2026-07", "revenue": 43868.0})

        server.SERVICE._refresh_twse(data)

        self.assertEqual(nanya["metrics"]["period"], "2026-07")
        self.assertEqual(nanya["metrics"]["revenue"], 43868.0)


if __name__ == "__main__":
    unittest.main()
