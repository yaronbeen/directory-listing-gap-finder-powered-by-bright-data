#!/usr/bin/env python3
"""Build an evidence-safe manual listing review queue from captured pages."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def csv_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


def canonical_domain(value):
    parsed = urlsplit(value if "://" in value else "//" + value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def match_brand(text, brand):
    return bool(re.search(r"(?<![\w])" + re.escape(brand) + r"(?![\w])", text, re.I))


def classify_page(title, text):
    combined = f"{title} {text}".lower()
    if "awesome" in combined and ("list" in combined or "github" in combined):
        return "awesome_list"
    if "alternative" in combined:
        return "alternatives"
    if re.search(r"\b(best|top)\b", title.lower()) or "curated list" in combined:
        return "listicle"
    if "marketplace" in combined:
        return "marketplace"
    if "directory" in combined or "submit a site" in combined:
        return "directory"
    return "unknown"


def safe_routes(routes):
    return sorted({r for r in routes if urlsplit(r).scheme in {"http", "https"} and urlsplit(r).netloc})


def evaluate_page(page, own_brand, competitors, own_domain=None):
    text = str(page.get("text", ""))
    failed = page.get("capture_status", "ok") not in {"ok", "complete"} or not text
    result = {
        "page_url": page.get("url"),
        "title": page.get("title", ""),
        "page_type": classify_page(page.get("title", ""), text) if not failed else "unknown",
        "capture_status": page.get("capture_status", "ok"),
        "captured_at": page.get("captured_at"),
        "submission_routes": safe_routes(page.get("submission_routes", [])),
    }
    if failed:
        result.update({"own_presence": "unknown", "competitors_observed": [], "competitor_presence": {c: "unknown" for c in competitors}, "priority": "manual_review"})
        return result
    own_observed = match_brand(text, own_brand)
    if own_domain and page.get("linked_domains"):
        own_observed = own_observed or any(canonical_domain(d) == canonical_domain(own_domain) or canonical_domain(d).endswith("." + canonical_domain(own_domain)) for d in page["linked_domains"])
    observed = [c for c in competitors if match_brand(text, c)]
    result.update({"own_presence": "observed" if own_observed else "not_observed_in_capture", "competitors_observed": observed, "competitor_presence": {c: "observed" if c in observed else "not_observed_in_capture" for c in competitors}})
    eligible_type = result["page_type"] in {"directory", "listicle", "alternatives", "awesome_list", "marketplace"}
    if eligible_type and observed and not own_observed and result["submission_routes"]:
        result["priority"] = "review"
    elif own_observed and result["submission_routes"]:
        result["priority"] = "update_profile"
    else:
        result["priority"] = "manual_review"
    return result


def comparison_value(value):
    if isinstance(value, dict):
        return {k: comparison_value(v) for k, v in value.items() if k not in {"status", "captured_at"}}
    if isinstance(value, list):
        return [comparison_value(v) for v in value]
    return value


def render(result):
    lines = ["# Directory Listing Gap Finder | Powered by Bright Data", "", "Presence applies only to the captured page text. `not_observed_in_capture` is not a sitewide absence claim. A visible route does not promise acceptance, a followed link, or SEO impact.", "", "| Priority | Page | Type | Own presence | Competitors observed | Status |", "|---|---|---|---|---|---|"]
    for row in result["rows"]:
        lines.append(f"| {row['priority']} | {row['page_url']} | {row['page_type']} | {row['own_presence']} | {', '.join(row['competitors_observed']) or 'none observed'} | {row['status']} |")
    return "\n".join(lines) + "\n"


def analyze(payload, previous=None):
    own = payload.get("own_brand") or ""
    competitors = payload.get("competitors") or []
    rows = [evaluate_page(p, own, competitors, payload.get("own_domain")) for p in payload.get("pages", [])]
    old = {r["page_url"]: comparison_value(r) for r in (previous or {}).get("rows", [])}
    for row in rows:
        identity = row["page_url"]
        row["status"] = "new" if identity not in old else ("unchanged" if old[identity] == comparison_value(row) else "changed")
    rows.sort(key=lambda r: ({"review": 0, "update_profile": 1, "manual_review": 2}[r["priority"]], r["page_url"] or ""))
    run_id = hashlib.sha256(json.dumps(comparison_value(rows), sort_keys=True).encode()).hexdigest()[:12]
    result = {"rows": rows, "snapshot": {"schema_version": 1, "run_id": run_id, "own_brand": own, "competitors": competitors, "rows": rows}}
    result["report"] = render(result)
    return result


def write_outputs(result, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(result["report"])
    (out / "run.json").write_text(json.dumps(result["snapshot"], indent=2, sort_keys=True) + "\n")
    fields = ["page_url", "page_type", "own_presence", "competitors_observed", "submission_routes", "priority", "status", "captured_at"]
    with (out / "opportunities.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in result["rows"]:
            writer.writerow({key: csv_cell(json.dumps(row[key]) if key in {"competitors_observed", "submission_routes"} else row.get(key)) for key in fields})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--previous", help="Prior run.json; omit on the first run")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text())
    previous = json.loads(Path(args.previous).read_text()) if args.previous else None
    write_outputs(analyze(payload, previous), args.output_dir)


if __name__ == "__main__":
    main()
