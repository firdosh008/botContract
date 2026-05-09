# Client Sourcing Agent

Automated client sourcing and outreach system for freelance AI engineer Firdosh Ahmad. Scrapes job boards daily, scores leads with Claude AI, enriches company data, generates personalized cold emails and LinkedIn DMs, and tracks everything in a local CSV file — no external services, zero monthly costs beyond Claude API.

## How It Works

```
 SCRAPE              SCORE              ENRICH             WRITE            SAVE
┌─────────┐   1─10  ┌─────────┐    ┌─────────────┐    ┌──────────┐    ┌──────────┐
│ LinkedIn │───────→│         │    │ Crunchbase   │    │ Email    │    │ .md file │
│ HN API   │───────→│ Claude  │───→│ DuckDuckGo   │───→│ Writer   │───→│ in       │
│ Wellfound│───────→│ Scorer  │    │ Claude       │    │ LinkedIn │    │ outreach │
│ Prod Hunt│───────→│         │    │ Intel        │    │ DM Writer│    │ _drafts  │
└─────────┘         └─────────┘    └─────────────┘    └──────────┘    └──────────┘
     ↓                    ↓                ↓                ↓                 ↓
  Playwright           <7 = discard     Cached per       Self-eval:        pipeline.csv
  + free APIs          from pipeline    company          <7 = regenerate   + data.md
```

## No External Services

Everything runs locally with free tools:

| What | How | Cost |
|------|-----|------|
| LinkedIn scraping | Playwright with your credentials | Free |
| HN Jobs | Official Firebase API | Free |
| Wellfound | Embedded JSON + Playwright | Free |
| Product Hunt | Apollo cache parsing | Free |
| Company research | Crunchbase + DuckDuckGo + Claude | Free + API |
| Job scoring | Claude Haiku | ~$0.001/lead |
| Outreach writing | Claude Sonnet | ~$0.01/lead |
| Pipeline tracking | CSV file + data.md | Free |
| Email drafts | Local .md files | Free |
| Optional: sending | SMTP (Gmail app password) | Free |

## Setup

### 1. Prerequisites

- **Python 3.12+**
- **Anthropic API key**: https://console.anthropic.com
- **LinkedIn account**: A disposable account is recommended (to avoid rate limits on your main one)

### 2. Install

```bash
git clone <repo-url>
cd client-sourcing-agent

cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, LINKEDIN_EMAIL, LINKEDIN_PASSWORD

pip install -r requirements.txt
playwright install chromium
```

### 3. Validate

```bash
python scripts/setup.py
```

This checks your environment, installs dependencies, and tests LinkedIn login.

### 4. Run

```bash
# First run
python -m agent.main

# Or schedule it daily
bash scripts/run_daily.sh
```

### 5. Review Output

- **`pipeline.csv`** — Open in Excel. Your full CRM with all leads, scores, statuses, and follow-up dates.
- **`outreach_drafts/`** — Each lead gets a `.md` file with the email/DM ready to copy-paste.
- **`data.md`** — Pipeline summary updated every run.

## Configuration

All in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Your Claude API key |
| `LINKEDIN_EMAIL` | — | LinkedIn login (disposable account recommended) |
| `LINKEDIN_PASSWORD` | — | LinkedIn password |
| `MAX_LEADS_PER_DAY` | 10 | Leads per run |
| `MIN_FIT_SCORE` | 7 | Minimum score (1–10) to keep a lead |
| `OUTREACH_MODE` | `local` | `local` = save drafts as files; `auto_send` = send via SMTP |

### Switching to Auto-Send

When you're confident in the drafts:

1. In `.env`: `OUTREACH_MODE=auto_send`
2. Add `SMTP_EMAIL` and `SMTP_APP_PASSWORD` (use a [Gmail app password](https://support.google.com/accounts/answer/185833), not your account password)

## Daily Run Cost

At 10 leads/day:
- Scoring (Haiku): ~$0.01
- Writing (Sonnet): ~$0.15
- Enrichment (Haiku): ~$0.02
- **Total: ~$0.18/day (~$5/month)**

## Project Structure

```
├── agent/              # Core pipeline
│   ├── main.py         # Orchestrator
│   ├── config.py       # Config + Firdosh's profile
│   ├── scorer.py       # Claude Haiku: job fit 1–10
│   ├── enricher.py     # Crunchbase + Claude: company intel
│   ├── writer.py       # Claude Sonnet: email + DM generation
│   ├── sender.py       # Save .md drafts or SMTP send
│   └── logger.py       # CSV pipeline + data.md digest
├── scrapers/           # Job sources
│   ├── linkedin_jobs.py    # Playwright + auth
│   ├── hackernews_jobs.py  # HN Firebase API
│   ├── wellfound.py        # Embedded JSON + Playwright
│   └── product_hunt.py     # Apollo cache parsing
├── models/schemas.py   # Pydantic v2 data contracts
├── prompts/            # Claude system prompts
├── evals/              # Quality checks
├── scripts/
│   ├── setup.py        # Validate env + test LinkedIn
│   ├── run_daily.sh    # Shell entry point
│   └── backfill.py     # Retry failed writes
└── .github/workflows/  # GitHub Actions cron
```

## Extending

Add a new scraper in 3 steps:

1. Create `scrapers/newsource.py` with `async def scrape_newsource() -> list[JobLead]`
2. Import in `agent/main.py` and add to `asyncio.gather()`
3. Add `"newsource"` to the `source` Literal in `models/schemas.py`

The pipeline handles scoring, enrichment, writing, and logging automatically.
"# botContract" 
