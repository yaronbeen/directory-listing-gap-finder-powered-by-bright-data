import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from report import analyze, canonical_domain, classify_page, csv_cell, evaluate_page, match_brand, write_outputs


class DirectoryTests(unittest.TestCase):
    def test_domain_and_brand_boundaries(self):
        self.assertEqual(canonical_domain("https://www.Example.com/path"), "example.com")
        self.assertTrue(match_brand("Acme is listed", "Acme"))
        self.assertFalse(match_brand("AcmeSoft is different", "Acme"))

    def test_page_types_and_safe_routes(self):
        self.assertEqual(classify_page("Best CRM Software", "A curated list of CRM tools with submit a site"), "listicle")
        self.assertEqual(classify_page("Acme Alternatives", "Compare alternatives to Acme"), "alternatives")
        self.assertEqual(classify_page("Awesome SEO", "awesome-list on GitHub"), "awesome_list")
        page = {"url": "https://directory.example/best-crm", "title": "Best CRM Software", "text": "Acme and Beta. Submit a site at https://directory.example/submit", "submission_routes": ["https://directory.example/submit", "javascript:alert(1)"], "captured_at": "2026-11-09"}
        result = evaluate_page(page, "MyCo", ["Acme", "Beta"])
        self.assertEqual(result["own_presence"], "not_observed_in_capture")
        self.assertEqual(result["submission_routes"], ["https://directory.example/submit"])
        self.assertEqual(result["priority"], "review")

    def test_failed_capture_is_unknown_not_absent(self):
        result = evaluate_page({"url": "https://example.com", "capture_status": "failed"}, "MyCo", ["Acme"])
        self.assertEqual(result["own_presence"], "unknown")
        self.assertEqual(result["priority"], "manual_review")

    def test_csv_diff_and_outputs(self):
        self.assertEqual(csv_cell("\t=1+1"), "'\t=1+1")
        payload = {"own_brand": "MyCo", "competitors": ["Acme"], "pages": [{"url": "https://directory.example/best-crm", "title": "Best CRM Software", "text": "Acme. Submit at https://directory.example/submit", "submission_routes": ["https://directory.example/submit"], "captured_at": "2026-11-09"}]}
        first = analyze(payload)
        second = analyze(payload, first["snapshot"])
        self.assertEqual(second["rows"][0]["status"], "unchanged")
        with tempfile.TemporaryDirectory() as tmp:
            write_outputs(second, tmp)
            self.assertTrue((Path(tmp) / "opportunities.csv").is_file())
            self.assertIn("not_observed_in_capture", (Path(tmp) / "run.json").read_text())


if __name__ == "__main__":
    unittest.main()
