import unittest

import build_pages


class NanyaReleaseParserTests(unittest.TestCase):
    def test_finds_target_quarter_release(self):
        listing = """
        <a href="/en/IR/16/?IRId=13157">Nanya Technology July 2026 Revenue</a>
        <a href="/en/IR/16/?IRId=13150">
          Nanya Technology Reports Results for the Second Quarter 2026
        </a>
        """

        self.assertEqual(
            build_pages.find_nanya_results_release_url(listing, 2026, 2),
            "https://www.nanya.com/en/IR/16/?IRId=13150",
        )

    def test_parses_all_q2_metrics_from_official_release(self):
        release = """
        <p>2026/07/10</p>
        <p>Nanya Technology Reports Results for the Second Quarter 2026</p>
        <p>Nanya's quarterly sales revenue was NT$82,549 million.</p>
        <p>Operating income of the quarter was NT$60,826 million;
           operating margin was 73.7 percent.</p>
        <p>The Company had net income of NT$50,192 million,
           with net margin of 60.8 percent.</p>
        """

        item = build_pages.parse_nanya_results_release(
            release,
            2026,
            2,
            "https://www.nanya.com/en/IR/16/?IRId=13150",
        )

        self.assertIsNotNone(item)
        self.assertEqual(item["revenue"], 82549.0)
        self.assertEqual(item["operatingIncome"], 60826.0)
        self.assertEqual(item["netIncome"], 50192.0)
        self.assertAlmostEqual(item["operatingMargin"], 73.6847, places=4)
        self.assertAlmostEqual(item["netMargin"], 60.8027, places=4)
        self.assertEqual(item["announcementDate"], "2026-07-10")
        self.assertTrue(item["isPreliminary"])
        self.assertEqual(item["source"], "Nanya official IR")

    def test_rejects_a_different_quarter(self):
        release = """
        <p>Nanya Technology Reports Results for the First Quarter 2026</p>
        <p>Nanya's quarterly sales revenue was NT$49,087 million.</p>
        <p>Operating income of the quarter was NT$30,111 million.</p>
        <p>The Company had net income of NT$26,058 million.</p>
        """

        self.assertIsNone(
            build_pages.parse_nanya_results_release(
                release,
                2026,
                2,
                "https://www.nanya.com/en/IR/16/?IRId=12105",
            )
        )

    def test_preliminary_feed_replaces_old_source(self):
        data = {
            "feed": [{
                "id": "nanya-preliminary-2026q2",
                "companyId": "nanya",
                "url": "https://example.com/old-secondary-source",
                "source": "secondary source",
                "date": "2026-07-10",
            }]
        }
        item = {
            "period": "2026Q2",
            "announcementDate": "2026-07-10",
            "sourceUrl": "https://www.nanya.com/en/IR/16/?IRId=13150",
            "source": "Nanya official IR",
        }

        build_pages.add_preliminary_feed(data, item)

        self.assertEqual(len(data["feed"]), 1)
        self.assertEqual(data["feed"][0]["url"], item["sourceUrl"])
        self.assertEqual(data["feed"][0]["source"], item["source"])


if __name__ == "__main__":
    unittest.main()
