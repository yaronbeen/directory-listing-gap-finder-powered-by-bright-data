import json
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
        self.assertEqual(classify_page("Awesome SEO List", "A curated collection on GitHub"), "awesome_list")
        self.assertEqual(classify_page("CRM Software", "Our approach is an alternative to old workflows"), "unknown")
        page = {"url": "https://directory.example/best-crm", "title": "Best CRM Software", "text": "Acme and Beta. Submit a site at https://directory.example/submit", "submission_routes": ["https://directory.example/submit", "javascript:alert(1)"], "captured_at": "2026-11-09"}
        result = evaluate_page(page, "MyCo", ["Acme", "Beta"])
        self.assertEqual(result["own_presence"], "not_observed_in_capture")
        self.assertEqual(result["submission_routes"], ["https://directory.example/submit"])
        self.assertEqual(result["priority"], "review")

    def test_failed_capture_is_unknown_not_absent(self):
        result = evaluate_page({"url": "https://example.com", "capture_status": "failed"}, "MyCo", ["Acme"])
        self.assertEqual(result["own_presence"], "unknown")
        self.assertEqual(result["priority"], "manual_review")
        truncated = evaluate_page({"url": "https://example.com", "text": "Acme", "capture_status": "truncated"}, "MyCo", ["Acme"])
        self.assertEqual(truncated["own_presence"], "unknown")
        exact_domain = evaluate_page({"url": "https://directory.example", "title": "Best CRM", "text": "Tools", "linked_domains": ["app.myco.co.uk"], "capture_status": "ok"}, "MyCo", ["Acme"], "myco.co.uk")
        self.assertEqual(exact_domain["own_presence"], "observed")

    def test_common_word_brands_require_domain_evidence(self):
        page = {"url": "https://directory.example/best-crm", "title": "Best CRM Software", "text": "Close deals faster with a linear workflow.", "submission_routes": ["https://directory.example/submit"], "capture_status": "ok"}
        ambiguous = evaluate_page(page, "MyCo", ["Close", "Linear"])
        self.assertEqual(ambiguous["competitors_observed"], [])
        self.assertEqual(ambiguous["competitor_presence"], {"Close": "unknown", "Linear": "unknown"})
        self.assertEqual(ambiguous["priority"], "manual_review")
        linked = dict(page, linked_domains=["close.com"])
        resolved = evaluate_page(linked, "MyCo", ["Close"], competitor_domains={"Close": "close.com"})
        self.assertEqual(resolved["competitors_observed"], ["Close"])
        self.assertIn("close.com", resolved["competitor_match_evidence"]["Close"])
        own_ambiguous = evaluate_page(page, "Linear", ["Acme"])
        self.assertEqual(own_ambiguous["own_presence"], "unknown")

    def test_match_evidence_and_route_are_emitted(self):
        page = {"url": "https://directory.example/best-crm", "title": "Best CRM Software", "text": "Acme is listed here.", "submission_routes": ["https://directory.example/submit"], "capture_status": "ok"}
        result = analyze({"own_brand": "MyCo", "competitors": ["Acme"], "pages": [page]})
        self.assertIn("Acme is listed here", result["rows"][0]["competitor_match_evidence"]["Acme"])
        self.assertIn("Match evidence", result["report"])
        self.assertIn("https://directory.example/submit", result["report"])

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

    def test_missing_own_brand_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze({"competitors": ["Acme"], "pages": [{"url": "https://example.com", "text": "Acme", "capture_status": "ok"}]})

    def test_sanitized_live_capture_page_type(self):
        fixture = json.loads((Path(__file__).parent / "fixtures" / "sanitized_live.json").read_text())
        page = fixture["page"]
        self.assertEqual(classify_page(page["title"], page["text"]), "listicle")


    def test_shipped_example_output_and_readme_table_are_current(self):
        root = Path(__file__).parents[1]
        result = analyze(json.loads((root / "examples" / "input.json").read_text()))
        self.assertEqual(result["report"], (root / "examples" / "output" / "report.md").read_text())
        readme = (root / "README.md").read_text()
        for line in result["report"].splitlines():
            if line.startswith("|"):
                self.assertIn(line, readme)


if __name__ == "__main__":
    unittest.main()
