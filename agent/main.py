"""
Client Sourcing Agent — Main Orchestrator

Runs the full pipeline: scrape → score → enrich → write → draft/send → log.

No external services required — everything runs locally:
  - Scraping: Playwright (LinkedIn) + free APIs (HN, Wellfound, Product Hunt)
  - Scoring: Claude Haiku
  - Enrichment: Crunchbase + DuckDuckGo (free) + Claude
  - Writing: Claude Sonnet
  - Delivery: Local .md files (or SMTP if configured)
  - Tracking: pipeline.csv + data.md
"""

import asyncio
import time
from rich.console import Console
from agent.config import MAX_LEADS_PER_DAY, OUTREACH_MODE
from agent.scorer import score_job_fit
from agent.enricher import enrich_company
from agent.writer import generate_outreach
from agent.logger import log_to_pipeline, send_daily_digest
from agent.sender import save_draft_locally, send_via_smtp
from scrapers.linkedin_jobs import scrape_linkedin_jobs
from scrapers.hackernews_jobs import scrape_hn_jobs
from scrapers.wellfound import scrape_wellfound
from scrapers.product_hunt import scrape_product_hunt
from models.schemas import EnrichedLead, is_target_country

console = Console()


async def run_pipeline():
    """Execute the full client sourcing pipeline."""
    pipeline_start = time.time()
    console.rule("[bold blue]Client Sourcing Agent — Daily Run[/bold blue]")
    console.print(f"[dim]Mode: {OUTREACH_MODE} | Max leads: {MAX_LEADS_PER_DAY}[/dim]")

    # ═══════════════════════════════════════════════════
    # Phase 1: Scrape all sources in parallel
    # ═══════════════════════════════════════════════════
    console.rule("[bold]Phase 1: Scraping[/bold]")
    t0 = time.time()
    raw_leads = []

    results = await asyncio.gather(
        scrape_linkedin_jobs(),
        scrape_hn_jobs(),
        scrape_wellfound(),
        scrape_product_hunt(),
        return_exceptions=True,
    )

    sources = ["linkedin", "hackernews", "wellfound", "product_hunt"]
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            console.log(f"[yellow]  {sources[i]} scraper error: {r}[/yellow]")
        else:
            console.log(f"[dim]  {sources[i]}: {len(r)} leads[/dim]")
            raw_leads.extend(r)

    console.log(f"Total raw leads scraped: {len(raw_leads)} ({time.time() - t0:.1f}s)")

    # Deduplicate by company + title
    seen = set()
    unique_leads = []
    for lead in raw_leads:
        key = f"{lead.company.lower()}::{lead.title.lower()}"
        if key not in seen:
            seen.add(key)
            unique_leads.append(lead)

    console.log(f"After deduplication: {len(unique_leads)} ({len(raw_leads) - len(unique_leads)} duplicates)")

    # Filter to target countries only
    target_leads = [l for l in unique_leads if is_target_country(l.location)]
    skipped = len(unique_leads) - len(target_leads)
    if skipped:
        console.log(f"Country filter: {len(target_leads)} target country leads ({skipped} skipped)")
    unique_leads = target_leads

    # Prefer contract/freelance leads — sort them first
    unique_leads.sort(key=lambda l: (not l.is_contract, -len(l.tech_stack)))

    # ═══════════════════════════════════════════════════
    # Phase 2: Score all leads
    # ═══════════════════════════════════════════════════
    console.rule("[bold]Phase 2: Scoring[/bold]")
    t0 = time.time()
    scored_leads = []

    for lead in unique_leads:
        try:
            fit = score_job_fit(lead)
            if fit:
                scored_leads.append((lead, fit))
        except Exception as e:
            console.log(f"[yellow]Scoring error for {lead.company}: {e}[/yellow]")

    scored_leads.sort(key=lambda x: x[1].score, reverse=True)
    top_leads = scored_leads[:MAX_LEADS_PER_DAY]
    console.log(f"Passing threshold: {len(scored_leads)} → top {len(top_leads)} ({time.time() - t0:.1f}s)")

    if not top_leads:
        console.log("[yellow]No leads passed scoring threshold. Exiting.[/yellow]")
        send_daily_digest([])
        return

    # ═══════════════════════════════════════════════════
    # Phase 3: Enrich + Write outreach
    # ═══════════════════════════════════════════════════
    console.rule("[bold]Phase 3: Enrich & Write[/bold]")
    t0 = time.time()
    enriched: list[EnrichedLead] = []

    for job, fit in top_leads:
        try:
            intel = enrich_company(job)
            outreach = generate_outreach(job, fit, intel)
            enriched.append(
                EnrichedLead(
                    job=job,
                    fit=fit,
                    intel=intel,
                    email_draft=outreach.get("email_draft"),
                    dm_draft=outreach.get("dm_draft"),
                )
            )
        except Exception as e:
            console.log(f"[red]Enrich/write failed for {job.company}: {e}[/red]")

    console.log(f"{len(enriched)} leads enriched with outreach ({time.time() - t0:.1f}s)")

    # ═══════════════════════════════════════════════════
    # Phase 4: Save drafts (or send)
    # ═══════════════════════════════════════════════════
    console.rule("[bold]Phase 4: Save Drafts[/bold]")
    t0 = time.time()

    for lead in enriched:
        try:
            if lead.email_draft:
                if OUTREACH_MODE == "auto_send":
                    success = send_via_smtp(lead.email_draft)
                    if success:
                        lead.email_draft.status = "sent"
                else:
                    save_draft_locally(lead.email_draft)

            if lead.dm_draft:
                if OUTREACH_MODE != "auto_send":
                    save_draft_locally(lead.dm_draft)
        except Exception as e:
            console.log(f"[red]Draft/send failed for {lead.job.company}: {e}[/red]")

    console.log(f"Drafts saved ({time.time() - t0:.1f}s)")

    # ═══════════════════════════════════════════════════
    # Phase 5: Log to pipeline CSV
    # ═══════════════════════════════════════════════════
    console.rule("[bold]Phase 5: Pipeline Logging[/bold]")
    t0 = time.time()

    for lead in enriched:
        try:
            log_to_pipeline(lead)
        except Exception as e:
            console.log(f"[red]Pipeline logging failed for {lead.job.company}: {e}[/red]")

    console.log(f"Pipeline CSV updated ({time.time() - t0:.1f}s)")

    # ═══════════════════════════════════════════════════
    # Phase 6: Daily digest
    # ═══════════════════════════════════════════════════
    send_daily_digest(enriched)

    total_elapsed = time.time() - pipeline_start
    console.rule(f"[bold green]Pipeline complete in {total_elapsed:.1f}s[/bold green]")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
