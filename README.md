# Directory Listing Gap Finder | Powered by Bright Data

> **Before you chase another listing, check the page. Check the competitors. Check the route.**

Find public directories, alternatives pages, marketplaces, and “best X” lists where your competitors appear but your brand was not observed in the captured page. Turn them into a careful manual-review queue with the evidence and visible submission route attached.

## In plain English

**Find “best X” lists and directories where your competitors are listed but you may not be.**

An AI-agent skill. You give your brand and a few competitors. Your agent uses Bright Data MCP to search for directories, alternatives pages and listicles, reads them, and checks who appears on each.

| | |
|---|---|
| **You give it** | Your brand and domain, 3-5 competitors, a category and a country. |
| **You get** | `opportunities.csv` and `action-plan.md`: a prioritized list of pages where competitors appear and you were not seen, with the quoted evidence, the visible submission route and one next action. |
| **Made for** | SEO and marketing people doing manual listing and citation outreach. |
| **Boundaries** | It never submits, claims or contacts anyone; “not seen” is never “absent”. |

## The decision

**Which listing or profile update deserves manual attention first?**

Use it to:

- Build a focused citation and listing research queue.
- Spot incomplete or outdated profiles without claiming sitewide absence.
- Give an SEO assistant the exact page, match, route, and next manual action.

## Why Bright Data

Search results give you places to look. They do not give you a presence matrix. [Bright Data](https://docs.brightdata.com/products/mcp-server/overview) MCP connects search and public-page-to-Markdown collection in one agent workflow, so each opportunity can carry page evidence instead of a guessed verdict. That means less copy-paste research and fewer imaginary listing gaps.

## Start with 5,000 free credits

**New Bright Data accounts include 5,000 free credits per month. No credit card is required.** Credits share one account-level pool, reset monthly, and are subject to current eligibility and product terms.

The default plan uses **4 searches and 12 public-page fetches**, with at most **2 retries**. Your agent shows the cap before collecting. A fetched page is evidence; a submission route is not a promise of acceptance.

## What you get

- `report.md`: a prioritized manual-review queue.
- `opportunities.csv`: stable `page_url` keys, presence states, competitor matches, routes, and a concrete `next_action`.
- `action-plan.md`: a human checklist explaining why each page is queued and what to verify or do next.
- `run.json`: the current snapshot for detecting page, presence, and route changes; vanished pages are not labeled as removed.
- Three honest states: `observed`, `not_observed_in_capture`, and `unknown`; failed captures always route to recapture or manual inspection.

## Give this to your agent

```text
Use directory-listing-gap-finder for [category].
My brand is [brand] and domain is [domain].
My competitors are [3-5 names/domains]. My country is [two-letter country].

Use Bright Data MCP for at most 4 searches across best, alternatives, marketplace,
and directory queries. Filter irrelevant results, then fetch at most 12 selected
public pages. Show the 16-request plan first. Retry at most twice overall.

Record capture_status=truncated when MCP says content was cut. Treat failed,
challenged, empty, or truncated captures as unknown. Match whole brand names and
supplied domains only. Supply competitor_domains for common-word names such as
Close, Linear, or Copper; ambiguous text alone stays unknown. Do not derive
registrable domains or invent authority scores. Classify page type from the title,
not an incidental word buried in the article. Capture visible http/https submit,
claim, or editorial routes without opening forms.
Run scripts/report.py and return the manual-review queue plus action-plan.md.
Follow the listed verification steps manually. Do not submit, claim, pay, publish,
or promise backlink value.
```

## Install

Requires Python 3.10+ and an MCP-compatible agent. This is a public repo.

### 1. Connect Bright Data MCP

Follow [Install Bright Data MCP](docs/install-bright-data-mcp.md). Choose hosted or local setup, then verify `search_engine` and `scrape_as_markdown` are connected as `brightdata`.

### 2. Clone the skill

```bash
git clone https://github.com/yaronbeen/directory-listing-gap-finder-powered-by-bright-data.git \
  ~/.claude/skills/directory-listing-gap-finder
```

For OpenCode, clone into `~/.config/opencode/skills/directory-listing-gap-finder`. See the [connection and schema guide](docs/technical-guide.md).

## Run the example

```bash
cd ~/.claude/skills/directory-listing-gap-finder
python3 scripts/report.py examples/input.json --output-dir examples/output
```

For a later run:

```bash
python3 scripts/report.py new-input.json \
  --previous examples/output/run.json --output-dir output
```

The example is synthetic. The [live-check note](docs/live-check.md) records successful and failed public-page checks.

## Example output

| Priority | Page | Type | Own presence | Competitor presence | Match evidence | Routes | Status |
|---|---|---|---|---|---|---|---|
| review | https://directory.example/best-crm | listicle | not_observed_in_capture | Acme: observed; Beta: observed | Acme: brand text: A curated list of CRM tools featuring Acme and Beta.; Beta: brand text: curated list of CRM tools featuring Acme and Beta. | https://directory.example/submit | new |
| update_profile | https://marketplace.example/apps/myco | marketplace | observed | Acme: not_observed_in_capture; Beta: not_observed_in_capture | Own: linked domain: app.myco.co.uk | https://marketplace.example/claim | new |
| manual_review | https://news.example/top-crm | unknown | unknown | Acme: unknown; Beta: unknown | none | none captured | new |

A `review` row requires a relevant page type, an observed competitor, an unobserved own brand in a complete capture, and a safe visible route. Everything else stays manual.

## Tests

The first commit defines behavior before implementation.

```bash
python3 -m unittest discover -s tests -v
```

Tests cover whole-brand matching, ambiguous common-word brands, supplied domains and subdomains, title-based page types, failed and truncated captures, match evidence, safe routes, priority gates, next-action plans, MCP installation docs, CSV injection, stable diffs, and a sanitized live listicle. See [the testing note](docs/testing.md).

## What this is not

- Not a backlink guarantee, domain-authority score, or ranking forecast.
- Not a sitewide crawler. Presence applies to one captured page only.
- Not automatic submission. Login, payment, and publishing stay out.
- Not permission to ignore a directory or publisher's current terms. Review them before collection.
- Not a Public Suffix List implementation. Your supplied domain and its subdomains are matched literally, including multi-part suffixes; no registrable domain is guessed.

## Repo map

```text
SKILL.md                 Agent workflow and MCP limits
scripts/report.py        Stdlib-only deterministic helper
tests/                   Unit tests + sanitized live fixture
examples/                Synthetic input and generated output
docs/                    Setup, schema, testing, and live-check notes
```

## FAQ

**Why is `not_observed_in_capture` so wordy?**  Because “not listed” is often false. Lazy loading and truncation can hide names. Precision prevents wasted outreach.

**Can a queue be empty?**  Yes. No qualifying opportunity is better than 20 weak ones.

**Does a submit link mean free inclusion?**  No. It only records what was visible. Terms, price, eligibility, and link attributes require manual review.

---

Independent project by Yaron Been. MIT licensed. Powered by Bright Data; no affiliation or endorsement is implied.
