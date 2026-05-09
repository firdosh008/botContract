"""Scrape Hacker News "Who Is Hiring" threads via the free Firebase API."""

import asyncio
import re
import time
from datetime import datetime, timedelta, timezone
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt
from rich.console import Console
from models.schemas import JobLead, is_target_country

console = Console()

HN_API = "https://hacker-news.firebaseio.com/v0"

AI_KEYWORDS = [
    "LLM", "RAG", "AI", "agent", "GPT", "Claude", "Anthropic",
    "vector", "embedding", "FastAPI", "Python", "machine learning",
    "langchain", "openai",
]

CONTRACT_KEYWORDS = ["contract", "freelance", "freelancer", "consultant", "part-time"]

TARGET_LOCATIONS = [
    "remote", "anywhere", "worldwide", "global",
    "us", "usa", "united states", "sf", "san francisco", "new york", "nyc", "boston",
    "austin", "seattle", "remote us",
    "uk", "london", "united kingdom", "remote uk",
    "canada", "toronto", "vancouver",
    "australia", "sydney", "melbourne",
    "germany", "berlin", "munich",
    "france", "paris",
    "netherlands", "amsterdam",
    "switzerland", "zurich",
    "sweden", "stockholm",
    "eu", "europe", "emea", "americas",
]


def _is_ai_related(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in AI_KEYWORDS)


def _is_target_location(text: str) -> bool:
    text_lower = text.lower()
    return any(loc in text_lower for loc in TARGET_LOCATIONS)


def _is_contract(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in CONTRACT_KEYWORDS)


def _extract_company(text: str) -> str:
    """Extract company name from a HN job posting's first line."""
    first_line = text.split("\n")[0].strip()

    # Remove HTML tags
    first_line = re.sub(r'<[^>]+>', '', first_line)

    # Try pipe-separated: "Company | Role | Location"
    if "|" in first_line:
        company = first_line.split("|")[0].strip()
        company = re.sub(r'\s*\([^)]*\)\s*$', '', company).strip()
        if company and len(company) < 80:
            return company

    # Try em-dash
    if "—" in first_line:
        company = first_line.split("—")[0].strip()
        company = re.sub(r'\s*\([^)]*\)\s*$', '', company).strip()
        if company and len(company) < 80:
            return company

    # Try "Company - Role"
    if " - " in first_line:
        parts = first_line.split(" - ")
        company = parts[0].strip()
        company = re.sub(r'\s*\([^)]*\)\s*$', '', company).strip()
        if company and len(company) < 80:
            return company

    # Try "Company: Role"
    if ":" in first_line:
        company = first_line.split(":")[0].strip()
        if company and len(company) < 40:
            return company

    return "Unknown"


def _extract_role(text: str) -> str:
    """Extract the job role/title from a HN posting."""
    first_line = text.split("\n")[0].strip()
    first_line = re.sub(r'<[^>]+>', '', first_line)

    for sep in ["|", "—", " - ", ":"]:
        if sep in first_line:
            parts = first_line.split(sep)
            if len(parts) >= 2:
                role = parts[1].strip()
                if role and len(role) < 120:
                    return role

    return first_line[:120]


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(3))
async def _fetch_item(item_id: int) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{HN_API}/item/{item_id}.json")
        resp.raise_for_status()
        return resp.json()


async def _find_hiring_thread() -> int | None:
    """Find the current month's Who Is Hiring thread ID."""
    console.log("[dim]  Searching for Who Is Hiring thread...[/dim]")

    async with httpx.AsyncClient(timeout=15) as client:
        # Try known user whoishiring
        resp = await client.get(f"{HN_API}/user/whoishiring.json")
        resp.raise_for_status()
        user_data = resp.json()
        submitted = user_data.get("submitted", [])[:5]
        if submitted:
            for sid in submitted:
                item = await _fetch_item(sid)
                title = (item.get("title", "") or "").lower()
                if "who is hiring" in title:
                    return sid

    # Fallback: search top stories
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{HN_API}/topstories.json")
        top_ids = resp.json()[:200]
        for batch_start in range(0, len(top_ids), 20):
            batch = top_ids[batch_start:batch_start + 20]
            items = await asyncio.gather(*[_fetch_item(iid) for iid in batch], return_exceptions=True)
            for item in items:
                if isinstance(item, Exception):
                    continue
                if "who is hiring" in (item.get("title", "") or "").lower():
                    return item["id"]

    return None


async def scrape_hn_jobs() -> list[JobLead]:
    """Scrape HN Who Is Hiring for AI-related posts targeting high-paying countries."""
    console.log("[blue]HN: fetching Who Is Hiring via Firebase API...[/blue]")
    t0 = time.time()

    try:
        thread_id = await _find_hiring_thread()
    except Exception as e:
        console.log(f"[red]HN thread search failed: {e}[/red]")
        return []

    if not thread_id:
        console.log("[yellow]Could not find Who Is Hiring thread[/yellow]")
        return []

    console.log(f"[dim]  Thread ID: {thread_id}[/dim]")

    try:
        thread = await _fetch_item(thread_id)
    except Exception as e:
        console.log(f"[red]Thread fetch failed: {e}[/red]")
        return []

    comment_ids = thread.get("kids", [])
    if not comment_ids:
        console.log("[yellow]No comments in thread[/yellow]")
        return []

    console.log(f"[dim]  Processing {len(comment_ids)} comments...[/dim]")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    leads = []
    ai_count = 0
    loc_count = 0

    for batch_start in range(0, min(len(comment_ids), 500), 20):
        batch = comment_ids[batch_start:batch_start + 20]
        items = await asyncio.gather(*[_fetch_item(cid) for cid in batch], return_exceptions=True)

        for item in items:
            if isinstance(item, Exception):
                continue

            text = item.get("text", "").strip()
            if not text:
                continue

            post_time = datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc)
            if post_time < cutoff:
                continue

            is_ai = _is_ai_related(text)
            is_good_loc = _is_target_location(text)

            if is_ai:
                ai_count += 1
            if is_good_loc:
                loc_count += 1

            if not is_ai or not is_good_loc:
                continue

            company = _extract_company(text)
            role = _extract_role(text)
            is_contract = _is_contract(text)
            country = "US"  # Default — HN is US-heavy

            leads.append(JobLead(
                id=f"hn-{item.get('id', '')}",
                title=role,
                company=company,
                location="Remote" if "remote" in text.lower() else "See post",
                source="hackernews",
                posted_at=post_time,
                description=text[:3000],
                apply_url=f"https://news.ycombinator.com/item?id={item.get('id', '')}",
                is_remote="remote" in text.lower() or "anywhere" in text.lower(),
                is_contract=is_contract,
                country=country,
            ))

    elapsed = time.time() - t0
    console.log(f"[dim]  AI-related: {ai_count}, target location: {loc_count}, matched: {len(leads)}[/dim]")
    console.log(f"[green]HN: {len(leads)} leads ({elapsed:.1f}s)[/green]")
    return leads
