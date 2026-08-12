import unittest

import server


class DartMetricTests(unittest.TestCase):
    def test_defaults_to_current_period_amount_for_quarter_history(self):
        rows = [{
            "sj_nm": "손익계산서",
            "account_nm": "매출액",
            "thstrm_amount": "33,434,395,547",
            "thstrm_add_amount": "54,923,791,090",
        }]

        value, account = server.DashboardService._dart_metric(rows, [r"^매출액$"])

        self.assertEqual(value, 33434395547)
        self.assertEqual(account, "매출액")

    def test_can_prefer_cumulative_amount_for_half_year_metrics(self):
        rows = [{
            "sj_nm": "손익계산서",
            "account_nm": "매출액",
            "thstrm_amount": "33,434,395,547",
            "thstrm_add_amount": "54,923,791,090",
        }]

        value, account = server.DashboardService._dart_metric(
            rows,
            [r"^매출액$"],
            ("thstrm_add_amount", "thstrm_amount"),
        )

        self.assertEqual(value, 54923791090)
        self.assertEqual(account, "매출액")


if __name__ == "__main__":
    unittest.main()
