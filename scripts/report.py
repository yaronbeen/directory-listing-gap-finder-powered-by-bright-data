#!/usr/bin/env python3
"""Build an evidence-safe manual listing review queue from captured pages."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

AMBIGUOUS_BRANDS = {
    "apollo", "apple", "buffer", "close", "copper", "linear", "monday",
    "notion", "orange", "paddle", "pitch", "square", "wise", "zoom",
}


def csv_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


def canonical_domain(value):
    parsed = urlsplit(value if "://" in value else "//" + value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def find_brand_evidence(text, brand):
    if not brand:
        return None
    match = re.search(r"(?<![\w])" + re.escape(brand) + r"(?![\w])", text, re.I)
    if not match:
        return None
    start = max(0, match.start() - 40)
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    excerpt = text[start:min(len(text), match.end() + 60)]
    return " ".join(excerpt.split())


def match_brand(text, brand):
    return find_brand_evidence(text, brand) is not None


def domain_evidence(linked_domains, domain):
    target = canonical_domain(domain or "")
    if not target:
        return None
    for candidate in linked_domains or []:
        host = canonical_domain(candidate)
        if host == target or host.endswith("." + target):
            return f"linked domain: {host}"
    return None


def brand_presence(text, brand, domain, linked_domains):
    domain_match = domain_evidence(linked_domains, domain)
    if domain_match:
        return "observed", domain_match
    text_match = find_brand_evidence(text, brand)
    if brand.casefold() in AMBIGUOUS_BRANDS:
        return ("unknown", None) if text_match else ("not_observed_in_capture", None)
    if text_match:
        return "observed", f"brand text: {text_match}"
    return ("unknown", None) if not brand and not domain else ("not_observed_in_capture", None)


def classify_page(title, text):
    label = title.lower()
    if "awesome" in label and ("list" in label or "github" in label):
        return "awesome_list"
    if "alternative" in label:
        return "alternatives"
    if re.search(r"\b(best|top)\b", label) or "curated list" in label:
        return "listicle"
    if "marketplace" in label:
        return "marketplace"
    if "directory" in label or "submit a site" in label:
        return "directory"
    return "unknown"


def safe_routes(routes):
    return sorted({r for r in routes if urlsplit(r).scheme in {"http", "https"} and urlsplit(r).netloc})


def evaluate_page(page, own_brand, competitors, own_domain=None, competitor_domains=None):
    text = str(page.get("text", ""))
    failed = page.get("capture_status", "ok") not in {"ok", "complete"} or not text
    result = {
        "page_url": page.get("url"),
        "title": page.get("title", ""),
        "page_type": classify_page(page.get("title", ""), text) if not failed else "unknown",
        "capture_status": page.get("capture_status", "ok"),
        "captured_at": page.get("captured_at"),
        "submission_routes": safe_routes(page.get("submission_routes", [])),
        "own_match_evidence": None,
        "competitor_match_evidence": {},
    }
    if failed:
        result.update({"own_presence": "unknown", "competitors_observed": [], "competitor_presence": {c: "unknown" for c in competitors}, "priority": "manual_review"})
        return result
    linked_domains = page.get("linked_domains", [])
    own_presence, own_evidence = brand_presence(text, own_brand, own_domain, linked_domains)
    result["own_match_evidence"] = own_evidence
    observed = []
    competitor_presence = {}
    for competitor in competitors:
        domain = (competitor_domains or {}).get(competitor)
        presence, evidence = brand_presence(text, competitor, domain, linked_domains)
        competitor_presence[competitor] = presence
        if presence == "observed":
            observed.append(competitor)
            result["competitor_match_evidence"][competitor] = evidence
    own_observed = own_presence == "observed"
    result.update({"own_presence": own_presence, "competitors_observed": observed, "competitor_presence": competitor_presence})
    eligible_type = result["page_type"] in {"directory", "listicle", "alternatives", "awesome_list", "marketplace"}
    if eligible_type and observed and own_presence == "not_observed_in_capture" and result["submission_routes"]:
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


def md(value):
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render(result):
    lines = ["# Directory Listing Gap Finder | Powered by Bright Data", "", "Presence applies only to the captured page text. `not_observed_in_capture` is not a sitewide absence claim. A visible route does not promise acceptance, a followed link, or SEO impact.", "", "| Priority | Page | Type | Own presence | Competitor presence | Match evidence | Routes | Status |", "|---|---|---|---|---|---|---|---|"]
    for row in result["rows"]:
        competitors = "; ".join(f"{name}: {state}" for name, state in row["competitor_presence"].items()) or "none supplied"
        evidence = []
        if row.get("own_match_evidence"):
            evidence.append(f"Own: {row['own_match_evidence']}")
        evidence += [f"{name}: {quote}" for name, quote in row.get("competitor_match_evidence", {}).items()]
        routes = "<br>".join(row["submission_routes"]) or "none captured"
        lines.append(f"| {row['priority']} | {md(row['page_url'])} | {row['page_type']} | {row['own_presence']} | {md(competitors)} | {md('; '.join(evidence) or 'none')} | {md(routes)} | {row['status']} |")
    return "\n".join(lines) + "\n"


def analyze(payload, previous=None):
    own = payload.get("own_brand") or ""
    if not own.strip():
        raise ValueError("own_brand is required")
    competitors = payload.get("competitors") or []
    competitor_domains = payload.get("competitor_domains") or {}
    rows = [evaluate_page(p, own, competitors, payload.get("own_domain"), competitor_domains) for p in payload.get("pages", [])]
    old = {r["page_url"]: comparison_value(r) for r in (previous or {}).get("rows", [])}
    for row in rows:
        identity = row["page_url"]
        row["status"] = "new" if identity not in old else ("unchanged" if old[identity] == comparison_value(row) else "changed")
    rows.sort(key=lambda r: ({"review": 0, "update_profile": 1, "manual_review": 2}[r["priority"]], r["page_url"] or ""))
    run_id = hashlib.sha256(json.dumps(comparison_value(rows), sort_keys=True).encode()).hexdigest()[:12]
    result = {"rows": rows, "snapshot": {"schema_version": 1, "run_id": run_id, "own_brand": own, "competitors": competitors, "competitor_domains": competitor_domains, "rows": rows}}
    result["report"] = render(result)
    return result


def write_outputs(result, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(result["report"])
    (out / "run.json").write_text(json.dumps(result["snapshot"], indent=2, sort_keys=True) + "\n")
    fields = ["page_url", "page_type", "own_presence", "competitors_observed", "competitor_presence", "own_match_evidence", "competitor_match_evidence", "submission_routes", "priority", "status", "captured_at"]
    json_fields = {"competitors_observed", "competitor_presence", "competitor_match_evidence", "submission_routes"}
    with (out / "opportunities.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in result["rows"]:
            writer.writerow({key: csv_cell(json.dumps(row[key]) if key in json_fields else row.get(key)) for key in fields})


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
