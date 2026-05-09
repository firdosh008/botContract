"""Scrape LinkedIn jobs via Playwright with saved session.

Run `python scripts/setup.py` first to log in and save the session.
"""

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from models.schemas import JobLead, is_target_country
from agent.config import LINKEDIN_SESSION
from rich.console import Console

console = Console()

TECH_KEYWORDS = [
    "Python", "FastAPI", "LangChain", "OpenAI", "Anthropic", "Claude",
    "RAG", "vector database", "Pinecone", "Weaviate", "pgvector",
    "LLM", "GPT", "agent", "multi-agent", "MLflow", "Hugging Face",
    "AWS", "GCP", "PostgreSQL", "TypeScript", "React", "Next.js",
]

CONTRACT_KEYWORDS = ["contract", "freelance", "freelancer", "consultant", "consulting", "part-time"]

SEARCH_KEYWORDS = [
    "AI engineer contract remote",
    "LLM engineer freelance",
    "RAG developer contract",
]


def _extract_tech_stack(text: str) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in TECH_KEYWORDS if kw.lower() in text_lower]


def _is_contract(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in CONTRACT_KEYWORDS)


def _detect_country(location: str, description: str) -> str:
    """Detect which country a posting is from."""
    combined = (location + " " + description[:500]).lower()
    country_map = {
        "US": ["united states", " usa", " san francisco", " new york", " boston", " austin", " seattle", "remote us"],
        "UK": ["united kingdom", " london", " uk ", "remote uk"],
        "Canada": ["canada", " toronto", " vancouver"],
        "Australia": ["australia", " sydney", " melbourne"],
        "Germany": ["germany", " berlin", " munich"],
        "Netherlands": ["netherlands", " amsterdam"],
        "Switzerland": ["switzerland", " zurich"],
        "France": ["france", " paris"],
        "Sweden": ["sweden", " stockholm"],
    }
    for country, patterns in country_map.items():
        for pat in patterns:
            if pat in combined:
                return country
    return ""


async def scrape_linkedin_jobs(max_results: int = 50) -> list[JobLead]:
    """Scrape LinkedIn for AI contract roles using saved session."""
    console.log("[blue]LinkedIn: scraping via Playwright...[/blue]")
    t0 = time.time()

    if not LINKEDIN_SESSION.exists():
        console.log("[red]No LinkedIn session. Run: python scripts/setup.py[/red]")
        return []

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        console.log("[red]Playwright not installed[/red]")
        return []

    leads = []
    seen_ids = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        # Restore FULL session (cookies + localStorage)
        storage = json.loads(LINKEDIN_SESSION.read_text(encoding="utf-8"))
        context = await browser.new_context(
            storage_state=LINKEDIN_SESSION,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
        )

        # Verify login
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        if "login" in page.url:
            console.log("[red]Session expired. Re-run: python scripts/setup.py[/red]")
            await page.close()
            await browser.close()
            return []
        console.log("[dim]  LinkedIn session valid[/dim]")
        await page.close()

        for kw_idx, kw in enumerate(SEARCH_KEYWORDS):
            if len(leads) >= max_results:
                break

            try:
                page = await context.new_page()
                url = f"https://www.linkedin.com/jobs/search/?keywords={kw.replace(' ', '%20')}&f_WT=2&sortBy=DD&geoId=92000000"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # Scroll to load
                for _ in range(4):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)

                content = await page.content()

                # Try extracting from __NEXT_DATA__ first
                next_match = re.search(
                    r'<script id="__NEXT_DATA__"[^>]*type="application/json"[^>]*>(.*?)</script>',
                    content, re.DOTALL,
                )
                if next_match:
                    try:
                        nd = json.loads(next_match.group(1))
                        jobs_found = 0

                        def walk(obj, depth=0):
                            nonlocal jobs_found
                            if depth > 10:
                                return
                            if isinstance(obj, dict):
                                # Look for job-related data structures
                                if ("jobPostingUrn" in str(obj) or "jobPostingId" in str(obj)) and "title" in obj:
                                    title = str(obj.get("title", "")).strip()
                                    if not title or title == "None":
                                        return
                                    jid_raw = str(obj.get("jobPostingUrn", obj.get("jobPostingId", "")))
                                    jid = jid_raw.split(":")[-1]
                                    if jid in seen_ids or not jid:
                                        return
                                    seen_ids.add(jid)

                                    company = str(obj.get("companyName", ""))
                                    if not company:
                                        company_obj = obj.get("company", {})
                                        if isinstance(company_obj, dict):
                                            company = str(company_obj.get("name", ""))
                                    location = str(obj.get("formattedLocation", "Remote"))
                                    full_desc = str(obj.get("description", {}).get("text", "")) if isinstance(obj.get("description"), dict) else str(obj.get("description", ""))

                                    country = _detect_country(location, full_desc)
                                    if not is_target_country(location):
                                        return  # Skip non-target countries

                                    leads.append(JobLead(
                                        id=f"linkedin-{jid}",
                                        title=title,
                                        company=company or "Unknown",
                                        location=location,
                                        source="linkedin",
                                        posted_at=datetime.now(timezone.utc),
                                        description=full_desc or f"{title} at {company} — {location}",
                                        apply_url=f"https://www.linkedin.com/jobs/view/{jid}/",
                                        is_remote=True,
                                        is_contract=_is_contract(f"{title} {full_desc}"),
                                        country=country,
                                        tech_stack=_extract_tech_stack(f"{title} {company} {full_desc}"),
                                    ))
                                    jobs_found += 1
                                for v in obj.values():
                                    walk(v, depth + 1)
                            elif isinstance(obj, list):
                                for item in obj:
                                    walk(item, depth + 1)

                        walk(nd)
                        console.log(f"[dim]  Keyword '{kw}': {jobs_found} jobs from embedded data[/dim]")
                    except (json.JSONDecodeError, KeyError) as e:
                        console.log(f"[dim]  __NEXT_DATA__ parse: {e}[/dim]")

                # If NEXT_DATA didn't work, try regex on page HTML
                if not leads:
                    # Find job cards by the data attributes LinkedIn uses
                    pattern = r'data-job-id="(\d+)"[^>]*>'
                    matches = re.findall(pattern, content)
                    for jid in matches:
                        if jid in seen_ids:
                            continue
                        seen_ids.add(jid)
                        # Extract nearby text
                        context_match = re.search(
                            rf'data-job-id="{jid}".*?</li>', content, re.DOTALL
                        )
                        context_text = context_match.group(0) if context_match else ""
                        title_match = re.search(r'(?:class="[^"]*title[^"]*"[^>]*>|aria-label=")([^"<]+)', context_text)
                        company_match = re.search(r'(?:class="[^"]*company[^"]*"[^>]*>|class="[^"]*subtitle[^"]*"[^>]*>)([^"<]+)', context_text)

                        title = title_match.group(1).strip() if title_match else ""
                        company = company_match.group(1).strip() if company_match else "Unknown"

                        leads.append(JobLead(
                            id=f"linkedin-{jid}",
                            title=title,
                            company=company,
                            location="Remote",
                            source="linkedin",
                            posted_at=datetime.now(timezone.utc),
                            description=context_text[:2000],
                            apply_url=f"https://www.linkedin.com/jobs/view/{jid}/",
                            is_remote=True,
                            is_contract=_is_contract(f"{title} {context_text}"),
                            country="",
                            tech_stack=_extract_tech_stack(f"{title} {company}"),
                        ))

                await page.close()
                await asyncio.sleep(2)

            except Exception as e:
                console.log(f"[yellow]  Search '{kw}' error: {e}[/yellow]")

        await browser.close()

    # Filter to target countries and prefer contract roles
    leads = [l for l in leads if is_target_country(l.location)]
    leads.sort(key=lambda l: (not l.is_contract, -len(l.tech_stack)))
    leads = leads[:max_results]

    elapsed = time.time() - t0
    console.log(f"[green]LinkedIn: {len(leads)} leads ({elapsed:.1f}s)[/green]")
    return leads
