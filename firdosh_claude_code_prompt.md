# Claude Code Master Prompt
## Automated Client Sourcing + Outreach Agent for Firdosh Ahmad

---

## ROLE AND MISSION

You are a senior full-stack AI engineer and autonomous agent builder. Your mission is to build a production-grade, fully automated **Client Sourcing and Outreach System** for a freelance AI engineer named Firdosh Ahmad. This system must run daily, find international clients actively hiring for AI/LLM/RAG/multi-agent roles, enrich lead data, generate personalized outreach content, and track everything in a Notion CRM — with zero manual effort after setup.

You will build this end-to-end: file structure, all source code, MCP configurations, environment setup, scheduling logic, and a Notion schema. Do not skip steps. Do not summarize steps as "implement this similarly." Write every file in full.

---

## IDENTITY CONTEXT — WHO FIRDOSH IS

Before writing a single line of code, internalize this profile. Every generated email, DM, and application must sound like it was written by this exact person:

**Name:** Firdosh Ahmad  
**Location:** India (IST timezone — available 6am–2pm IST, overlapping US EST evenings and EU mornings)  
**Role seeking:** Freelance / Contract AI Engineer — international clients only (US, UK, EU, Canada, Australia)  
**Rate:** $35–60/hr USD (negotiable for strong projects)  
**Contact:** f.ahmad.job@gmail.com  

**Core technical skills (ranked by strength):**
1. RAG pipeline design and implementation (structured + unstructured data, semantic search, vector DBs)
2. Multi-agent system orchestration (FastAPI, LLM APIs — OpenAI, Anthropic, Gemini)
3. AI observability and evaluation (MLflow, prompt evaluation frameworks — model-based + rule-based graders)
4. LLM-powered workflow automation (RFP processing, document processing, agent orchestration)
5. Full-stack engineering (React, Next.js, FastAPI, REST APIs, Redux, PostgreSQL)
6. Frontend performance optimization (reduced API latency by ~6.6 seconds in production)

**Certifications and credentials:**
- Anthropic Claude Certification (2026) — Agent Skills, MCP, Claude API, Production Workflows
- LeetCode: 950+ problems solved, Rating 1852, Top 5.96% globally
- IEEE GCAT Conference: multi-object tracking system (MOTA 78.1) using YOLOv4 + Deep SORT

**Projects:**
- **Objs.ai** (Feb–Apr 2026): AI document processing with RAG, event-driven webhooks, dynamic UI
- **Zemuria Venture Studio** (Apr 2025–Jan 2026): Multi-agent FastAPI system, RAG pipelines, MLflow observability, RFP automation
- **The Crazy Mountaineer** (Mar–Aug 2023): Full-stack travel booking platform

**Tone for outreach:** Professional but human. Direct. No fluff. Concise. Shows genuine understanding of what the company is building. Never sounds like a template. Never starts with "I hope this message finds you well."

---

## SYSTEM ARCHITECTURE OVERVIEW

Build this exact architecture. Do not deviate unless there is a technically superior reason, which you must explain inline as a code comment.

```
client-sourcing-agent/
├── .env.example
├── .env                        # gitignored
├── .gitignore
├── README.md
├── requirements.txt
├── mcp_config.json             # MCP server configurations for Claude Code
├── notion_schema.json          # Notion DB schema to create on first run
│
├── agent/
│   ├── __init__.py
│   ├── main.py                 # Entry point — orchestrates all phases
│   ├── config.py               # Loads env, constants, Firdosh's resume context
│   ├── scorer.py               # LLM-based job fit scoring against Firdosh's profile
│   ├── enricher.py             # Company enrichment using Apify MCP
│   ├── writer.py               # Outreach content generation (emails + LinkedIn DMs)
│   ├── sender.py               # Gmail draft creation via Gmail MCP
│   └── logger.py               # Notion CRM write operations
│
├── scrapers/
│   ├── __init__.py
│   ├── linkedin_jobs.py        # Apify LinkedIn Jobs Scraper MCP wrapper
│   ├── hackernews_jobs.py      # Apify HN Who's Hiring Scraper MCP wrapper
│   ├── wellfound.py            # Playwright MCP scraper for Wellfound remote AI jobs
│   └── product_hunt.py        # Product Hunt new AI launches (last 7 days)
│
├── models/
│   ├── __init__.py
│   └── schemas.py              # Pydantic models: JobLead, EnrichedLead, OutreachDraft
│
├── prompts/
│   ├── fit_scorer.txt          # System prompt for job fit scoring
│   ├── email_writer.txt        # System prompt for cold email generation
│   ├── dm_writer.txt           # System prompt for LinkedIn DM generation
│   └── company_analyst.txt     # System prompt for company intel summarization
│
├── evals/
│   ├── __init__.py
│   ├── eval_scorer.py          # Evaluates fit scorer accuracy on synthetic test cases
│   ├── eval_writer.py          # Evaluates outreach quality: personalization, tone, length
│   └── test_cases.json         # 20 synthetic job postings with expected scores
│
├── scripts/
│   ├── setup.py                # One-time: creates Notion DB, validates MCP connections
│   ├── run_daily.sh            # Shell script triggered by cron / GitHub Actions
│   └── backfill.py             # Manual: backfill older leads into Notion
│
└── .github/
    └── workflows/
        └── daily_agent.yml     # GitHub Actions cron: runs at 7am IST (1:30am UTC) daily
```

---

## PHASE-BY-PHASE BUILD INSTRUCTIONS

### PHASE 0 — Environment and MCP Setup

**0.1 — Create `.env.example` with every required variable:**

```
# Anthropic
ANTHROPIC_API_KEY=

# Apify (for LinkedIn Jobs, HN Jobs, Company Research MCPs)
APIFY_API_TOKEN=

# Notion
NOTION_API_TOKEN=
NOTION_DATABASE_ID=          # Created by scripts/setup.py on first run

# Gmail OAuth (set by npx gmail-mcp-server auth)
GMAIL_CREDENTIALS_PATH=./gmail_credentials.json
GMAIL_TOKEN_PATH=./gmail_token.json

# LinkedIn (for stickerdaniel MCP — optional, used for DM enrichment)
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=

# Bright Data (fallback if LinkedIn MCP hits CAPTCHA)
BRIGHT_DATA_API_KEY=

# Agent behavior
MAX_LEADS_PER_DAY=10
MIN_FIT_SCORE=7              # 1–10 scale; leads below this are discarded
OUTREACH_MODE=draft          # Options: draft | auto_send (start with draft)
DAILY_DIGEST_EMAIL=f.ahmad.job@gmail.com
```

**0.2 — Create `mcp_config.json` for Claude Code:**

This file configures all MCP servers. Claude Code reads this at startup. Write the complete JSON:

```json
{
  "mcpServers": {
    "apify": {
      "command": "npx",
      "args": ["-y", "@apify/mcp-server"],
      "env": {
        "APIFY_TOKEN": "${APIFY_API_TOKEN}"
      }
    },
    "notion": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "NOTION_API_TOKEN": "${NOTION_API_TOKEN}"
      }
    },
    "gmail": {
      "command": "npx",
      "args": ["gmail-mcp-server"],
      "env": {
        "CREDENTIALS_PATH": "${GMAIL_CREDENTIALS_PATH}",
        "TOKEN_PATH": "${GMAIL_TOKEN_PATH}"
      }
    },
    "linkedin": {
      "command": "uvx",
      "args": ["linkedin-scraper-mcp@latest"],
      "env": {
        "UV_HTTP_TIMEOUT": "300"
      }
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp"]
    }
  }
}
```

**0.3 — `requirements.txt`:**

```
anthropic>=0.40.0
pydantic>=2.0
httpx>=0.27.0
python-dotenv>=1.0
rich>=13.0           # pretty CLI output for daily digest
tenacity>=8.0        # retry logic for API calls
schedule>=1.2        # for local scheduling alternative to cron
pytest>=8.0
```

---

### PHASE 1 — Data Models (`models/schemas.py`)

Write complete Pydantic v2 models. These are the contracts between every module. Every field must have a description. Every model must have a `model_config` with `json_schema_extra` showing a realistic example.

```python
# models/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class JobLead(BaseModel):
    """Raw job posting as scraped from a source."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "linkedin-3987234987",
                "title": "AI Engineer — RAG & Agents",
                "company": "Acme AI",
                "location": "Remote (US)",
                "source": "linkedin",
                "posted_at": "2026-05-08T06:00:00Z",
                "description": "We're building ...",
                "apply_url": "https://linkedin.com/jobs/view/...",
                "salary_range": "$80k–$120k or $60–$100/hr"
            }
        }
    }

    id: str = Field(description="Unique ID from the source platform")
    title: str = Field(description="Job title as posted")
    company: str = Field(description="Company name")
    location: str = Field(description="Location string from posting")
    source: Literal["linkedin", "hackernews", "wellfound", "product_hunt"]
    posted_at: Optional[datetime] = Field(None, description="UTC datetime of posting")
    description: str = Field(description="Full job description text")
    apply_url: str = Field(description="Direct link to apply or contact")
    salary_range: Optional[str] = Field(None, description="Salary or rate if mentioned")
    is_remote: bool = Field(default=True)
    tech_stack: list[str] = Field(default_factory=list, description="Extracted tech keywords")


class FitScore(BaseModel):
    """LLM-generated fit assessment for a job lead."""
    score: int = Field(ge=1, le=10, description="Overall fit 1–10")
    reasons: list[str] = Field(description="Top 3 reasons this is a good or poor fit")
    matched_skills: list[str] = Field(description="Firdosh's skills that directly match")
    gap_skills: list[str] = Field(description="Skills required but not in Firdosh's profile")
    outreach_angle: str = Field(description="Single best hook for the outreach message")
    recommended_channel: Literal["email", "linkedin_dm", "both"]


class CompanyIntel(BaseModel):
    """Enriched company context for personalization."""
    name: str
    size_estimate: Optional[str] = None       # e.g. "10–50 employees"
    funding_stage: Optional[str] = None        # e.g. "Series A ($12M)"
    tech_stack: list[str] = Field(default_factory=list)
    recent_news: Optional[str] = None          # 1–2 sentence summary
    key_person_name: Optional[str] = None      # CTO / founder name
    key_person_title: Optional[str] = None
    key_person_linkedin: Optional[str] = None
    pain_point_hypothesis: str = Field(
        description="Claude's 1-sentence hypothesis of what AI problem they're trying to solve"
    )


class OutreachDraft(BaseModel):
    """Generated outreach content ready for review."""
    lead_id: str
    company: str
    channel: Literal["email", "linkedin_dm"]
    subject: Optional[str] = None             # Email only
    body: str
    word_count: int
    personalization_score: int = Field(ge=1, le=10, description="Self-evaluated personalization 1–10")
    status: Literal["draft", "approved", "sent", "no_response", "replied"] = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EnrichedLead(BaseModel):
    """A job lead with all enrichment and outreach content attached."""
    job: JobLead
    fit: FitScore
    intel: CompanyIntel
    email_draft: Optional[OutreachDraft] = None
    dm_draft: Optional[OutreachDraft] = None
    notion_page_id: Optional[str] = None      # Set after Notion write
```

---

### PHASE 2 — Scrapers

#### `scrapers/linkedin_jobs.py`

Build a clean async wrapper around the Apify LinkedIn Jobs Scraper MCP. The function must:
- Accept `keywords`, `date_posted_hours` (default: 24), `max_results` (default: 50)
- Filter for remote roles only
- Return a list of `JobLead` objects
- Handle errors gracefully with `tenacity` retry (3 attempts, exponential backoff)
- Log each scrape with rich output showing count and time elapsed

Key Apify actor to call: `automly/linkedin-jobs-scraper`

Parameters to pass:
```python
{
    "searchTerms": ["LLM engineer", "AI engineer RAG", "multi-agent AI", "GenAI engineer"],
    "location": "Worldwide",
    "workType": "REMOTE",
    "experienceLevel": ["MID_SENIOR", "SENIOR"],
    "datePosted": "PAST_24_HOURS",
    "maxResults": 50
}
```

Parse the response into `JobLead` objects. Extract `tech_stack` by scanning description for: Python, FastAPI, LangChain, OpenAI, Anthropic, Claude, RAG, vector database, Pinecone, Weaviate, pgvector, LLM, GPT, agent, multi-agent, MLflow, Hugging Face, AWS, GCP, PostgreSQL, TypeScript, React, Next.js.

#### `scrapers/hackernews_jobs.py`

Wrap the Apify HN Who's Hiring scraper: `logiover/hacker-news-who-is-hiring-scraper`

This thread posts monthly. The scraper should:
- Always pull the current month's thread
- Filter comments to only those posted or updated within the last 24 hours (use `created_at` field)
- Only include posts mentioning: LLM, RAG, AI, agent, GPT, Claude, Anthropic, vector, embedding, FastAPI, Python
- Mark `is_remote=True` only if the post text explicitly says "remote", "REMOTE", or "anywhere"

#### `scrapers/wellfound.py`

Use the Playwright MCP to navigate to:
`https://wellfound.com/jobs?role=ai-engineer&remote=true&jobType=contract`

Steps:
1. Navigate to URL
2. Wait for job cards to load (wait for selector `.job-listing` or equivalent)
3. Extract: title, company, description snippet, apply URL, posted date
4. Filter to jobs posted ≤ 24 hours ago based on the relative timestamp shown ("2 hours ago", "1 day ago" — accept only those ≤ 24h)
5. For each job, click through to get the full description
6. Return as `JobLead` objects with `source="wellfound"`

Handle pagination: scrape up to 3 pages max.

#### `scrapers/product_hunt.py`

Use Playwright MCP to navigate to `https://www.producthunt.com/topics/artificial-intelligence`

Extract AI products launched in the last 7 days (weekly cadence — founders are freshly building and need engineering help):
- Product name
- Maker profile links (these become cold DM targets, not job applicants)
- Description
- Upvote count (proxy for traction — prioritize >50 upvotes)
- Website URL

Return these as `JobLead` objects with `source="product_hunt"`, `apply_url` pointing to the maker's profile, and `title="AI Freelance Opportunity (Product Hunt Launch)"`.

---

### PHASE 3 — Job Fit Scorer (`agent/scorer.py`)

This is the most important quality gate. Every lead passes through this before enrichment. Low-scoring leads are discarded to keep enrichment costs low.

**Write `prompts/fit_scorer.txt` — the system prompt:**

```
You are a specialized job fit evaluator for Firdosh Ahmad, an AI Engineer based in India seeking international freelance/contract work.

FIRDOSH'S PROFILE:
- Core expertise: RAG pipelines, multi-agent systems (FastAPI), LLM APIs (OpenAI, Anthropic, Gemini), AI observability (MLflow), prompt evaluation frameworks
- Production experience: built systems at Zemuria Venture Studio, reduced API latency by 6.6s, built RFP automation with agent orchestration
- Full-stack ability: React, Next.js, FastAPI, PostgreSQL, REST APIs
- Certification: Anthropic Claude (2026)
- Availability: Remote only, IST timezone (6am–2pm IST = US EST evenings / EU mornings)
- Seeking: $35–60/hr USD, contract or freelance
- NOT seeking: full-time employment, India-only roles

SCORING RULES:
- Score 1–10 where 10 = perfect match
- Score 8–10: remote, uses RAG/LLM/agents, contract/freelance ok, strong tech overlap
- Score 6–7: remote, AI-adjacent, partial stack match
- Score 4–5: mostly relevant but wrong contract type or unclear remote
- Score 1–3: full-time only, non-AI, India-only, or missing key requirements
- Auto-score 1 if: requires US/EU citizenship, requires on-site, requires security clearance

EVALUATION CRITERIA (weight in order):
1. Tech stack match (RAG, LLM, agents, FastAPI, Python) — 40%
2. Contract type (freelance/contract preferred over full-time) — 20%
3. Remote availability — 20%
4. Rate compatibility — 10%
5. Timezone overlap feasibility — 10%

OUTPUT FORMAT:
Return a single JSON object matching this schema exactly. No markdown, no explanation, just the JSON.
{
  "score": <int 1-10>,
  "reasons": [<str>, <str>, <str>],
  "matched_skills": [<str>, ...],
  "gap_skills": [<str>, ...],
  "outreach_angle": "<single sentence — the ONE thing that makes Firdosh uniquely qualified for THIS job>",
  "recommended_channel": "<email|linkedin_dm|both>"
}
```

**`agent/scorer.py` implementation:**

```python
import anthropic
import json
from models.schemas import JobLead, FitScore
from agent.config import ANTHROPIC_API_KEY, MIN_FIT_SCORE
from pathlib import Path

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
SCORER_PROMPT = Path("prompts/fit_scorer.txt").read_text()

def score_job_fit(job: JobLead) -> FitScore | None:
    """
    Score a job posting against Firdosh's profile.
    Returns None if the score is below MIN_FIT_SCORE (lead discarded).
    """
    user_message = f"""
JOB TITLE: {job.title}
COMPANY: {job.company}
LOCATION: {job.location}
SOURCE: {job.source}
SALARY/RATE: {job.salary_range or 'Not specified'}
IS REMOTE: {job.is_remote}
TECH STACK DETECTED: {', '.join(job.tech_stack) if job.tech_stack else 'Not detected'}

FULL JOB DESCRIPTION:
{job.description[:3000]}
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SCORER_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = response.content[0].text.strip()

    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    fit = FitScore(**data)

    if fit.score < MIN_FIT_SCORE:
        return None  # Discarded

    return fit
```

**Eval requirement:** In `evals/eval_scorer.py`, write a test suite with 20 synthetic job postings in `evals/test_cases.json`. Include:
- 5 perfect matches (score should be ≥8): remote, RAG+agents, contract, $50–100/hr
- 5 good matches (score 6–7): remote AI roles, partial stack match
- 5 mediocre (score 3–5): full-time or partial remote
- 5 hard rejects (score 1–2): on-site, no AI, citizenship required

The eval script must run all 20, compute mean score deviation vs expected, and print a pass/fail for each case. Target: >85% of cases within ±1.5 of expected score.

---

### PHASE 4 — Company Enricher (`agent/enricher.py`)

For each lead that passes scoring, enrich it using the Apify Company Research MCP (`renzomacar/multi-scraper-mcp`).

**Write `prompts/company_analyst.txt`:**

```
You are a research analyst preparing a briefing for Firdosh Ahmad, a freelance AI engineer doing cold outreach. 

Given raw company data from multiple sources, produce a concise intel summary that Firdosh can use to write a highly personalized outreach message.

Focus on:
1. What problem is this company solving with AI? (Be specific — not generic)
2. What engineering pain points do they likely have? (e.g. RAG latency, hallucinations, agent reliability)
3. Who is the right person to contact? (CTO, Head of AI, Founding Engineer)
4. What recent signal makes NOW the right time to reach out? (new funding, new product, job posting itself)

Output a JSON object matching this schema exactly. No markdown, no prose, just JSON:
{
  "size_estimate": "<string or null>",
  "funding_stage": "<string or null>",
  "tech_stack": [<strings>],
  "recent_news": "<1-2 sentence summary or null>",
  "key_person_name": "<string or null>",
  "key_person_title": "<string or null>",
  "key_person_linkedin": "<URL or null>",
  "pain_point_hypothesis": "<1 sentence — specific pain point Firdosh solves for them>"
}
```

**`agent/enricher.py` implementation:**

The enricher must:
1. Call Apify `renzomacar/multi-scraper-mcp` with the company name and website (if extractable from the job posting URL domain)
2. Pass raw response to Claude with the `company_analyst.txt` system prompt
3. Return a `CompanyIntel` object
4. If enrichment fails (API error, unknown company), return a minimal `CompanyIntel` with only `pain_point_hypothesis` generated from the job description alone
5. Cache results in a local `.enrichment_cache.json` file (company name → CompanyIntel) to avoid re-enriching the same company across runs

---

### PHASE 5 — Outreach Writer (`agent/writer.py`)

This is the highest-stakes module. Quality > quantity. Every message must feel like Firdosh wrote it after spending 10 minutes researching the company.

**Write `prompts/email_writer.txt`:**

```
You are writing a cold outreach email on behalf of Firdosh Ahmad, a freelance AI Engineer based in India. 

FIRDOSH'S VOICE:
- Direct, no-fluff
- Shows genuine understanding of what the company is building
- Leads with value, not desperation
- Never uses: "I hope this finds you well", "I wanted to reach out", "I am passionate about"
- Uses first-person naturally
- Signs off as: Firdosh Ahmad | AI Engineer | f.ahmad.job@gmail.com

EMAIL RULES:
- Subject line: specific and curiosity-driving, max 8 words, no emojis
- Body: 3 paragraphs, max 150 words total
  - Para 1 (2-3 sentences): One observation about THEIR specific product/problem + why it caught Firdosh's attention
  - Para 2 (2-3 sentences): The ONE most relevant thing from Firdosh's background (pick the most precise match, not a list of everything)
  - Para 3 (1-2 sentences): Simple, low-friction CTA — "Worth a 20-min call?" or "Happy to share a quick loom of a relevant project if useful."
- Never attach CV or mention LinkedIn in body (include in signature only if natural)
- Never say the word "leverage"

INPUT YOU WILL RECEIVE:
- Job title and company name
- Fit score and outreach angle
- Company intel (funding, pain point hypothesis, key person name)
- Firdosh's most relevant project for this job

OUTPUT FORMAT:
Return a JSON object:
{
  "subject": "<string>",
  "body": "<string — the complete email body with line breaks as \\n>",
  "word_count": <int>,
  "personalization_score": <int 1-10>
}
```

**Write `prompts/dm_writer.txt`:**

```
You are writing a LinkedIn connection request note and follow-up DM on behalf of Firdosh Ahmad.

LINKEDIN DM RULES:
- Connection request note: max 280 characters. No pitch. Genuine observation or shared interest. End with a soft question.
- Follow-up DM (sent 3 days after connection accepted): max 100 words. Same rules as email but tighter. One problem, one signal, one ask.
- Never open with "Hi [Name], I came across your profile..."
- Never say "synergies", "circle back", "touch base"
- If you have the person's first name, use it once, naturally

OUTPUT FORMAT:
{
  "connection_note": "<string max 280 chars>",
  "followup_dm": "<string max 100 words>",
  "personalization_score": <int 1-10>
}
```

**`agent/writer.py` — the generation function must:**

1. Accept an `EnrichedLead` object
2. Identify the most relevant project from Firdosh's profile for this specific job (RAG → Objs.ai; agents/RFP → Zemuria; frontend → One-For-Life; tracking → IEEE paper)
3. Call Claude with the appropriate prompt + all context assembled
4. Self-evaluate: if `personalization_score < 7`, regenerate once with a stricter instruction appended: `"The previous version was too generic. Be more specific about {company_name}'s exact problem."`
5. Return `OutreachDraft` objects for email and/or LinkedIn DM based on `FitScore.recommended_channel`

**Eval requirement:** In `evals/eval_writer.py`, write automated quality checks that flag any generated message that:
- Contains banned phrases: "hope this finds you", "I wanted to reach out", "leverage", "passionate", "synergies", "touch base"
- Exceeds word limits (email > 150 words, DM > 100 words)
- Has `personalization_score < 7`
- Has a subject line > 8 words
- Doesn't mention anything company-specific (detected by checking if company name or product appears in the body)

---

### PHASE 6 — Notion CRM Logger (`agent/logger.py`)

**First, define `notion_schema.json`:**

```json
{
  "database_name": "🎯 Client Pipeline — Firdosh",
  "properties": {
    "Company": { "type": "title" },
    "Role": { "type": "rich_text" },
    "Source": {
      "type": "select",
      "options": ["LinkedIn", "Hacker News", "Wellfound", "Product Hunt"]
    },
    "Status": {
      "type": "select",
      "options": ["New", "Draft Ready", "Sent", "No Response", "Replied", "Call Booked", "Rejected"]
    },
    "Fit Score": { "type": "number", "format": "number" },
    "Apply URL": { "type": "url" },
    "Posted At": { "type": "date" },
    "Outreach Channel": {
      "type": "select",
      "options": ["Email", "LinkedIn DM", "Both"]
    },
    "Key Contact": { "type": "rich_text" },
    "Pain Point": { "type": "rich_text" },
    "Outreach Sent At": { "type": "date" },
    "Follow Up Due": { "type": "date" },
    "Notes": { "type": "rich_text" },
    "Email Draft": { "type": "rich_text" },
    "LinkedIn DM Draft": { "type": "rich_text" }
  }
}
```

**`agent/logger.py` must:**

1. On `scripts/setup.py` first run: create the Notion database using the schema above via Notion MCP
2. On each daily run: for each `EnrichedLead`, create a new Notion page with all fields populated
3. Set "Follow Up Due" to 5 business days from today if status is "Sent"
4. Set "Follow Up Due" to 3 days from today if status is "Draft Ready"
5. If a lead's company already exists in Notion (check by company name match), update the existing page rather than creating a duplicate
6. After all leads are written, generate a daily digest: total found, total scored above threshold, total drafted, total auto-sent (if in auto_send mode)

---

### PHASE 7 — Main Orchestrator (`agent/main.py`)

This is the entry point. It coordinates all phases with clear logging.

```python
# agent/main.py

"""
Client Sourcing Agent — Main Orchestrator
Runs the full pipeline: scrape → score → enrich → write → draft/send → log
"""

import asyncio
from rich.console import Console
from rich.progress import Progress
from agent.config import MAX_LEADS_PER_DAY, OUTREACH_MODE
from agent.scorer import score_job_fit
from agent.enricher import enrich_company
from agent.writer import generate_outreach
from agent.logger import log_to_notion, send_daily_digest
from agent.sender import create_gmail_draft, send_email
from scrapers.linkedin_jobs import scrape_linkedin_jobs
from scrapers.hackernews_jobs import scrape_hn_jobs
from scrapers.wellfound import scrape_wellfound
from scrapers.product_hunt import scrape_product_hunt
from models.schemas import EnrichedLead

console = Console()

async def run_pipeline():
    console.rule("[bold blue]Client Sourcing Agent — Daily Run[/bold blue]")

    # PHASE 1: Scrape all sources in parallel
    console.log("📡 Scraping all sources...")
    raw_leads = []
    results = await asyncio.gather(
        scrape_linkedin_jobs(),
        scrape_hn_jobs(),
        scrape_wellfound(),
        scrape_product_hunt(),
        return_exceptions=True
    )
    for r in results:
        if isinstance(r, Exception):
            console.log(f"[yellow]Scraper error: {r}[/yellow]")
        else:
            raw_leads.extend(r)

    console.log(f"✅ Total raw leads scraped: {len(raw_leads)}")

    # Deduplicate by company + title
    seen = set()
    unique_leads = []
    for lead in raw_leads:
        key = f"{lead.company.lower()}::{lead.title.lower()}"
        if key not in seen:
            seen.add(key)
            unique_leads.append(lead)

    console.log(f"🔍 After deduplication: {len(unique_leads)}")

    # PHASE 2: Score all leads
    console.log("🧠 Scoring job fit...")
    scored_leads = []
    for lead in unique_leads:
        fit = score_job_fit(lead)
        if fit:
            scored_leads.append((lead, fit))

    # Sort by score descending, take top N
    scored_leads.sort(key=lambda x: x[1].score, reverse=True)
    top_leads = scored_leads[:MAX_LEADS_PER_DAY]
    console.log(f"🎯 Leads passing fit threshold: {len(scored_leads)} → taking top {len(top_leads)}")

    # PHASE 3: Enrich + Write outreach
    enriched: list[EnrichedLead] = []
    for job, fit in top_leads:
        intel = enrich_company(job)
        outreach = generate_outreach(job, fit, intel)
        enriched.append(EnrichedLead(job=job, fit=fit, intel=intel, **outreach))

    # PHASE 4: Send or draft
    for lead in enriched:
        if OUTREACH_MODE == "auto_send" and lead.email_draft:
            send_email(lead.email_draft)
            lead.email_draft.status = "sent"
        elif lead.email_draft:
            create_gmail_draft(lead.email_draft)
            lead.email_draft.status = "draft"

    # PHASE 5: Log to Notion
    for lead in enriched:
        notion_id = log_to_notion(lead)
        lead.notion_page_id = notion_id

    # PHASE 6: Send digest
    send_daily_digest(enriched)
    console.rule("[bold green]Pipeline complete[/bold green]")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
```

---

### PHASE 8 — Scheduling (`scripts/run_daily.sh` + GitHub Actions)

**`scripts/run_daily.sh`:**

```bash
#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .env
python -m agent.main
```

**`.github/workflows/daily_agent.yml`:**

```yaml
name: Daily Client Sourcing Agent

on:
  schedule:
    - cron: '30 1 * * 1-5'  # 1:30am UTC = 7:00am IST, Mon–Fri only
  workflow_dispatch:          # Allow manual trigger for testing

jobs:
  run-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Set up Node.js (for MCP servers)
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Python dependencies
        run: pip install -r requirements.txt

      - name: Install MCP servers
        run: |
          npm install -g gmail-mcp-server @notionhq/notion-mcp-server @apify/mcp-server
          pip install uv
          uvx linkedin-scraper-mcp@latest --version || true

      - name: Run agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          APIFY_API_TOKEN: ${{ secrets.APIFY_API_TOKEN }}
          NOTION_API_TOKEN: ${{ secrets.NOTION_API_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
          GMAIL_CREDENTIALS_PATH: ./gmail_credentials.json
          GMAIL_TOKEN_PATH: ./gmail_token.json
          LINKEDIN_EMAIL: ${{ secrets.LINKEDIN_EMAIL }}
          LINKEDIN_PASSWORD: ${{ secrets.LINKEDIN_PASSWORD }}
          MAX_LEADS_PER_DAY: '10'
          MIN_FIT_SCORE: '7'
          OUTREACH_MODE: 'draft'
        run: python -m agent.main

      - name: Upload run logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: agent-run-logs-${{ github.run_number }}
          path: logs/
          retention-days: 30
```

**Note for Firdosh:** Add all secrets at `https://github.com/YOUR_REPO/settings/secrets/actions`. Start with `OUTREACH_MODE=draft` — review everything in Gmail and Notion before switching to `auto_send`.

---

### PHASE 9 — README.md

Write a complete README that includes:

1. **What this does** — 3-sentence summary for someone who has never seen this
2. **Architecture diagram** — ASCII art of the pipeline (scrape → score → enrich → write → draft → log)
3. **Prerequisites** — Python 3.12, Node 20, uv, Apify account, Notion integration, Gmail API credentials
4. **Setup** — Step-by-step with exact commands:
   - Clone repo
   - Copy `.env.example` to `.env` and fill in values
   - `npm install -g gmail-mcp-server @notionhq/notion-mcp-server @apify/mcp-server`
   - `pip install uv && uvx linkedin-scraper-mcp@latest --login`
   - `pip install -r requirements.txt`
   - `python scripts/setup.py` (creates Notion DB, validates MCP connections)
   - `python -m agent.main` (first run)
5. **MCP server details** — table with Name, Purpose, URL, Auth method
6. **Outreach mode guide** — when to switch from `draft` to `auto_send`
7. **Rate limits and safety** — LinkedIn: max 80 requests/week. Email: max 20/day to start.
8. **Extending the system** — how to add a new scraper source in 3 steps

---

## QUALITY STANDARDS — APPLY TO EVERY FILE

These are non-negotiable. Apply them across every file you generate.

### Code quality
- All functions must have Google-style docstrings with `Args`, `Returns`, `Raises`
- All external API calls must be wrapped in `tenacity.retry` with 3 attempts and exponential backoff (base=2, multiplier=1, max=30)
- All Pydantic models must validate inputs — never trust raw API data
- Log every major operation with `rich.console.log` showing: action, entity, result, elapsed time
- All files must start with a module-level docstring explaining its role in the pipeline

### Error handling
- Scraper failures must be caught per-scraper and logged — one failing scraper must not crash the entire run
- If Claude API returns malformed JSON, retry with a stricter prompt appended: `"Your previous response was not valid JSON. Return ONLY the JSON object with no other text."`
- If Notion write fails, write the lead to a local `failed_leads.jsonl` file for manual recovery

### Security
- Never hardcode credentials anywhere — all from env
- `.env` must be in `.gitignore`
- `gmail_credentials.json` and `gmail_token.json` must be in `.gitignore`
- LinkedIn credentials must never appear in logs

### Cost management
- Log estimated token usage per run (use `response.usage.input_tokens + output_tokens`)
- The scorer runs on every lead — use `claude-haiku-4-5-20251001` for scoring (cheaper), `claude-sonnet-4-20250514` for writing (higher quality)
- Cache company enrichment results locally to avoid repeat API calls

---

## EVALUATION CRITERIA FOR YOUR OUTPUT

Before considering the implementation complete, verify each checkpoint:

**Functional correctness:**
- [ ] `python scripts/setup.py` creates the Notion database without errors
- [ ] `python -m agent.main` runs end-to-end with real MCP connections
- [ ] At least one lead from each source is scraped and processed per run
- [ ] Generated emails pass all `eval_writer.py` quality checks
- [ ] Fit scorer passes 85%+ of `eval_scorer.py` test cases
- [ ] All leads appear in Notion with correct fields populated

**Code quality:**
- [ ] No hardcoded credentials in any file
- [ ] Every external call has retry logic
- [ ] Every module has a docstring
- [ ] `requirements.txt` pins all dependencies to major versions

**Outreach quality:**
- [ ] No generated email exceeds 150 words
- [ ] No banned phrase appears in any generated message
- [ ] Every email contains a specific reference to the target company's product or problem
- [ ] Personalization score ≥ 7 for all approved drafts

---

## EXECUTION INSTRUCTIONS FOR CLAUDE CODE

Now build the entire system. Work through each phase in order. Do not stop after generating a single file — continue until all files listed in the architecture are complete.

For each file:
1. State which file you are building
2. Write the complete file contents (no placeholders, no "implement this similarly")
3. State any assumptions you made and why
4. Move to the next file

Start with: `models/schemas.py` → `agent/config.py` → `prompts/` → `scrapers/` → `agent/scorer.py` → `agent/enricher.py` → `agent/writer.py` → `agent/sender.py` → `agent/logger.py` → `agent/main.py` → `scripts/setup.py` → `scripts/run_daily.sh` → `.github/workflows/daily_agent.yml` → `evals/` → `README.md`

After all files are written, run `python scripts/setup.py` to validate the environment, then `python -m agent.main` with `MAX_LEADS_PER_DAY=2` and `OUTREACH_MODE=draft` as a smoke test.

If any step fails, diagnose the error, fix the root cause, and re-run. Do not paper over errors by catching and silently ignoring them.
