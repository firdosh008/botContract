"""Scrape Wellfound (AngelList) for remote AI contract roles via Playwright."""

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from models.schemas import JobLead, is_target_country
from rich.console import Console

console = Console()

WELLFOUND_URL = "https://wellfound.com/jobs?role=ai-engineer&remote=true&jobType=contract"
MAX_PAGES = 3


async def scrape_wellfound() -> list[JobLead]:
    """Scrape Wellfound for remote AI contract roles."""
    console.log("[blue]Wellfound: scraping via Playwright...[/blue]")
    t0 = time.time()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        console.log("[red]Playwright not installed[/red]")
        return []

    leads = []
    seen_ids = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
        )

        for page_num in range(1, MAX_PAGES + 1):
            try:
                page = await context.new_page()
                url = f"{WELLFOUND_URL}&page={page_num}"
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(3)

                content = await page.content()

                # Strategy 1: __NEXT_DATA__ embedded JSON
                script_match = re.search(
                    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', content, re.DOTALL
                )
                if script_match:
                    try:
                        nd = json.loads(script_match.group(1))
                        jobs_found = 0

                        def walk(obj, depth=0):
                            nonlocal jobs_found
                            if depth > 8:
                                return
                            if isinstance(obj, dict):
                                # Wellfound job entries typically have a slug + title
                                if "slug" in obj and "title" in obj and isinstance(obj.get("title"), str):
                                    title = obj["title"]
                                    slug = obj.get("slug", "")
                                    company = ""
                                    if isinstance(obj.get("company"), dict):
                                        company = obj["company"].get("name", "")
                                    elif "companyName" in obj:
                                        company = str(obj["companyName"])

                                    if not title or not company:
                                        return

                                    uid = f"wf-{slug or hash(title + company)}"
                                    if uid in seen_ids:
                                        return
                                    seen_ids.add(uid)

                                    location = (
                                        obj.get("locationNames", [None])[0]
                                        or obj.get("location", "Remote")
                                    )
                                    if not isinstance(location, str):
                                        location = "Remote"

                                    if not is_target_country(str(location)):
                                        return

                                    desc = str(obj.get("description", obj.get("body", "")))
                                    apply_url = f"https://wellfound.com{slug}" if slug else ""

                                    leads.append(JobLead(
                                        id=uid,
                                        title=title,
                                        company=company,
                                        location=str(location),
                                        source="wellfound",
                                        posted_at=datetime.now(timezone.utc),
                                        description=desc[:3000],
                                        apply_url=apply_url,
                                        is_remote=True,
                                        is_contract=True,
                                        country="",
                                        tech_stack=[],
                                    ))
                                    jobs_found += 1
                                for v in obj.values():
                                    walk(v, depth + 1)
                            elif isinstance(obj, list):
                                for item in obj:
                                    walk(item, depth + 1)

                        walk(nd)
                        console.log(f"[dim]  Page {page_num}: {jobs_found} jobs from embedded data[/dim]")
                    except (json.JSONDecodeError, KeyError) as e:
                        console.log(f"[dim]  Wellfound JSON parse: {e}[/dim]")

                await page.close()
                await asyncio.sleep(1)

            except Exception as e:
                console.log(f"[yellow]  Wellfound page {page_num} error: {e}[/yellow]")

        await browser.close()

    elapsed = time.time() - t0
    console.log(f"[green]Wellfound: {len(leads)} leads ({elapsed:.1f}s)[/green]")
    return leads
