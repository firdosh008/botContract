"""Pipeline tracker — logs leads to CSV and generates client-focused data.md."""

import csv
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from rich.console import Console
from rich.table import Table
from models.schemas import EnrichedLead
from agent.config import PIPELINE_CSV, FAILED_LEADS_PATH

console = Console()

CSV_COLUMNS = [
    "company",
    "role",
    "country",
    "source",
    "status",
    "fit_score",
    "is_contract",
    "contact_name",
    "contact_title",
    "contact_email",
    "contact_linkedin",
    "company_email",
    "website",
    "pain_point",
    "apply_url",
    "outreach_channel",
    "outreach_sent_at",
    "follow_up_due",
    "notes",
]

SOURCE_MAP = {
    "linkedin": "LinkedIn",
    "hackernews": "Hacker News",
    "wellfound": "Wellfound",
    "product_hunt": "Product Hunt",
}


def _ensure_csv_exists():
    if not PIPELINE_CSV.exists():
        PIPELINE_CSV.write_text(",".join(CSV_COLUMNS) + "\n", encoding="utf-8")
        console.log("[green]Created pipeline.csv[/green]")


def _read_csv() -> list[dict]:
    if not PIPELINE_CSV.exists():
        return []
    with open(PIPELINE_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(rows: list[dict]):
    with open(PIPELINE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _find_existing_row(company: str) -> tuple[int, dict] | None:
    rows = _read_csv()
    for i, row in enumerate(rows):
        if row.get("company", "").lower() == company.lower():
            return i, row
    return None


def _add_business_days(start: date, n: int) -> date:
    current = start
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def log_to_pipeline(lead: EnrichedLead) -> bool:
    """Write or update a lead in pipeline.csv."""
    t0 = time.time()
    _ensure_csv_exists()

    source_label = SOURCE_MAP.get(lead.job.source, lead.job.source.title())
    channel_map = {"email": "Email", "linkedin_dm": "LinkedIn DM", "both": "Both"}

    status = "Draft Ready"
    if lead.email_draft and lead.email_draft.status == "sent":
        status = "Sent"

    follow_up_due = _add_business_days(date.today(), 3).isoformat()
    if status == "Sent":
        follow_up_due = _add_business_days(date.today(), 5).isoformat()

    new_row = {
        "company": lead.job.company,
        "role": lead.job.title,
        "country": lead.job.country or "",
        "source": source_label,
        "status": status,
        "fit_score": str(lead.fit.score),
        "is_contract": "Yes" if lead.job.is_contract else "No",
        "contact_name": lead.intel.contact_name or "",
        "contact_title": lead.intel.contact_title or "",
        "contact_email": lead.intel.contact_email or "",
        "contact_linkedin": lead.intel.contact_linkedin or "",
        "company_email": lead.intel.company_email or "",
        "website": lead.intel.website or "",
        "pain_point": lead.intel.pain_point_hypothesis,
        "apply_url": lead.job.apply_url,
        "outreach_channel": channel_map.get(lead.fit.recommended_channel, "Email"),
        "outreach_sent_at": datetime.utcnow().strftime("%Y-%m-%d") if status == "Sent" else "",
        "follow_up_due": follow_up_due,
        "notes": "; ".join(lead.fit.reasons),
    }

    try:
        rows = _read_csv()
        existing = _find_existing_row(lead.job.company)

        if existing:
            rows[existing[0]] = new_row
        else:
            rows.append(new_row)

        _write_csv(rows)
        console.log(f"[green]  Pipeline logged: {lead.job.company} ({time.time() - t0:.1f}s)[/green]")
        return True
    except Exception as e:
        console.log(f"[red]CSV write failed for {lead.job.company}: {e}[/red]")
        return False


def send_daily_digest(leads: list[EnrichedLead]):
    """Print summary and update data.md with client-focused view."""
    console.rule("[bold]Daily Digest[/bold]")

    scores = [l.fit.score for l in leads] if leads else []
    emails = sum(1 for l in leads if l.email_draft)
    dms = sum(1 for l in leads if l.dm_draft)
    contracts = sum(1 for l in leads if l.job.is_contract)

    console.print(f"  Total leads: {len(leads)}")
    if scores:
        console.print(f"  Avg fit: {sum(scores) / len(scores):.1f} | Best: {max(scores)}")
    console.print(f"  Contract/freelance: {contracts}")
    console.print(f"  Drafts: {emails} emails, {dms} DMs")

    # Per-country breakdown
    countries = {}
    for l in leads:
        c = l.job.country or "Unknown"
        countries[c] = countries.get(c, 0) + 1
    if countries:
        console.print(f"  Countries: {', '.join(f'{k}({v})' for k, v in sorted(countries.items()))}")

    # Top leads table
    if leads:
        console.print("\n[bold]Top Client Leads:[/bold]")
        table = Table("Score", "Company", "Role", "Contact", "Country")
        for l in sorted(leads, key=lambda x: x.fit.score, reverse=True)[:10]:
            table.add_row(
                str(l.fit.score),
                l.job.company,
                l.job.title[:45],
                l.intel.contact_name or "—",
                l.job.country or "—",
            )
        console.print(table)

    _update_data_md(leads)


def _update_data_md(leads: list[EnrichedLead]):
    """Generate client-focused data.md — a proposal-ready client list."""
    path = Path(__file__).resolve().parent.parent / "data.md"
    today = date.today().isoformat()

    rows = _read_csv()
    total = len(rows)
    contract_count = sum(1 for r in rows if r.get("is_contract") == "Yes")

    content = f"""# Client Pipeline — Firdosh Ahmad

**Last updated:** {today}
**Total potential clients:** {total}
**Contract/freelance leads:** {contract_count}

---

## How to Use This

This is your daily client sourcing report. Each entry is a company actively hiring
for AI/LLM/RAG/agent work that matches your skill set. Target countries only
(US, UK, Canada, Australia, EU — high-paying markets).

**Priority order:**
1. Companies with contact info → send proposal immediately
2. Companies with LinkedIn contact → send connection request + DM
3. Apply URL only → apply and find the hiring manager on LinkedIn

---

## Hot Leads — Has Contact Info

| # | Company | Role | Contact | Email | Country | Score | Why You |
|---|---------|------|---------|-------|---------|-------|----------|
"""
    # Leads with contact info
    hot = [r for r in rows if r.get("contact_name") or r.get("contact_email")]
    if hot:
        for i, r in enumerate(hot[:20], 1):
            contact = r.get("contact_name", "—")
            email = r.get("contact_email", r.get("company_email", "—"))
            country = r.get("country", "—")
            score = r.get("fit_score", "—")
            pain = r.get("pain_point", "")[:80]
            content += f"| {i} | **{r.get('company', '')}** | {r.get('role', '')[:50]} | {contact} | {email} | {country} | {score} | {pain} |\n"
    else:
        content += "| — | No leads with contact info yet | | | | | | |\n"

    content += f"""
---

## All Pipeline Leads

| # | Company | Role | Country | Contract? | Contact | Score | Source |
|---|---------|------|---------|-----------|---------|-------|--------|
"""
    if rows:
        for i, r in enumerate(rows[:50], 1):
            contract = r.get("is_contract", "—")
            contact = r.get("contact_name", "—")
            content += f"| {i} | **{r.get('company', '')}** | {r.get('role', '')[:50]} | {r.get('country', '—')} | {contract} | {contact} | {r.get('fit_score', '—')} | {r.get('source', '—')} |\n"
    else:
        content += "| — | No leads yet | | | | | | |\n"

    if leads:
        content += f"""
---

## Today's Run Summary ({today})

- Leads found: {len(leads)}
- Average fit score: {sum(l.fit.score for l in leads) / len(leads):.1f}
- Drafts created: {sum(1 for l in leads if l.email_draft or l.dm_draft)}
- Contract opportunities: {sum(1 for l in leads if l.job.is_contract)}

### Top leads from this run:
| Score | Company | Role | Contact | Country |
|-------|---------|------|---------|---------|
"""
        for l in sorted(leads, key=lambda x: x.fit.score, reverse=True)[:10]:
            content += f"| {l.fit.score} | **{l.job.company}** | {l.job.title[:40]} | {l.intel.contact_name or '—'} | {l.job.country or '—'} |\n"

    path.write_text(content, encoding="utf-8")
    console.log(f"[dim]Updated data.md[/dim]")
