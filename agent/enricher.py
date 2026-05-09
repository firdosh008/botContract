"""Company enrichment — researches target companies for personalization."""

import asyncio
import json
import re
import time
from pathlib import Path
import anthropic
import httpx
from rich.console import Console
from models.schemas import JobLead, CompanyIntel
from agent.config import ANTHROPIC_API_KEY, ANALYST_MODEL, PROMPTS_DIR, CACHE_PATH

console = Console()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
ANALYST_PROMPT = (PROMPTS_DIR / "company_analyst.txt").read_text(encoding="utf-8")


def _load_cache() -> dict:
    """Load the enrichment cache from disk."""
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_cache(cache: dict):
    """Persist the enrichment cache to disk."""
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_key(company: str) -> str:
    """Normalize company name for cache lookup."""
    return company.lower().strip()


async def _scrape_crunchbase(company: str) -> str:
    """
    Try to get company info from Crunchbase free page.
    Returns raw HTML text with company data, or empty string.
    """
    # Normalize company name for URL: lowercase, replace spaces with hyphens, remove special chars
    slug = re.sub(r'[^a-z0-9-]', '', company.lower().replace(' ', '-').replace('.', ''))
    url = f"https://www.crunchbase.com/organization/{slug}"

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }) as http:
            resp = await http.get(url)
            if resp.status_code == 200:
                html = resp.text

                # Extract key data points with regex
                snippets = []
                # Description
                desc_match = re.search(r'"description":"([^"]+)"', html)
                if desc_match:
                    snippets.append(f"Description: {desc_match.group(1)}")

                # Funding
                funding_matches = re.findall(r'"funding_total[^}]*"value":"([^"]+)"', html)
                if funding_matches:
                    snippets.append(f"Total funding: {funding_matches[0]}")

                # Employee count
                emp_match = re.search(r'"num_employees_enum[^"]*"([^"]+)"', html)
                if emp_match:
                    snippets.append(f"Employees: {emp_match.group(1)}")

                # Categories/industries
                cat_matches = re.findall(r'"category_name":"([^"]+)"', html)
                if cat_matches:
                    snippets.append(f"Categories: {', '.join(cat_matches[:5])}")

                if snippets:
                    return f"Crunchbase data for {company}:\n" + "\n".join(snippets)

            return ""
    except Exception:
        return ""


async def _search_company_web(company: str) -> str:
    """
    Quick web search for company info via DuckDuckGo's HTML version (no API key needed).
    """
    try:
        query = f"{company} company AI funding team size"
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"

        async with httpx.AsyncClient(timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }) as http:
            resp = await http.get(url)
            if resp.status_code == 200:
                # Extract snippet texts
                snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                cleaned = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:5]]
                if cleaned:
                    return f"Web search results for {company}:\n" + "\n".join(cleaned)
        return ""
    except Exception:
        return ""


def _claude_summarize(raw_data: str, job_description: str, company: str) -> CompanyIntel:
    """Use Claude to distill raw company data into structured intel."""
    user_message = f"""
COMPANY: {company}
RAW RESEARCH DATA:
{raw_data[:4000]}

JOB DESCRIPTION (for context on what they're hiring for):
{job_description[:1500]}

Return the JSON object with the company intel — include contact_email and contact_name if you can find or infer them.
"""

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=ANALYST_MODEL,
                max_tokens=800,
                system=ANALYST_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            data = json.loads(raw)
            # Map JSON fields to CompanyIntel, keeping only valid fields
            valid_fields = {f for f in CompanyIntel.model_fields if f != "name"}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return CompanyIntel(name=company, **filtered)
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == 2:
                raise
            user_message += "\n\nYour previous response was not valid JSON. Return ONLY the JSON object."


def _minimal_intel_from_job(job: JobLead) -> CompanyIntel:
    """Build a minimal CompanyIntel from the job description alone."""
    user_message = f"""
There is no external company data available. Based solely on this job posting, produce a company intel JSON.
Try to infer the company domain from the company name and suggest likely contact email patterns.

COMPANY: {job.company}
TITLE: {job.title}
DESCRIPTION:
{job.description[:2000]}

Return the JSON.
"""

    response = client.messages.create(
        model=ANALYST_MODEL,
        max_tokens=800,
        system=ANALYST_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    valid_fields = {f for f in CompanyIntel.model_fields if f != "name"}
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    return CompanyIntel(name=job.company, **filtered)


def enrich_company(job: JobLead) -> CompanyIntel:
    """
    Enrich a job lead with company intelligence.

    Checks the local cache first. Tries Crunchbase + web search,
    then falls back to Claude-only extraction from the job description.

    Args:
        job: The JobLead with company name and description.

    Returns:
        A CompanyIntel object with research findings.
    """
    t0 = time.time()
    cache = _load_cache()
    ck = _cache_key(job.company)

    if ck in cache:
        console.log(f"[dim]Enrich: {job.company} (cached)[/dim]")
        return CompanyIntel(**cache[ck])

    console.log(f"[blue]Enrich: {job.company}...[/blue]")

    # Gather research from free sources
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context, create a new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_cb = executor.submit(asyncio.run, _scrape_crunchbase(job.company))
                future_web = executor.submit(asyncio.run, _search_company_web(job.company))
                cb_data = future_cb.result(timeout=15)
                web_data = future_web.result(timeout=15)
        else:
            cb_data = loop.run_until_complete(_scrape_crunchbase(job.company))
            web_data = loop.run_until_complete(_search_company_web(job.company))
    except Exception:
        cb_data = ""
        web_data = ""

    raw_data = f"{cb_data}\n\n{web_data}".strip()

    if raw_data:
        try:
            intel = _claude_summarize(raw_data, job.description, job.company)
        except Exception as e:
            console.log(f"[yellow]Claude enrichment failed: {e}. Using minimal intel.[/yellow]")
            intel = _minimal_intel_from_job(job)
    else:
        console.log(f"[dim]  No external data found, inferring from job description[/dim]")
        intel = _minimal_intel_from_job(job)

    # Cache and return
    cache[ck] = intel.model_dump()
    _save_cache(cache)

    elapsed = time.time() - t0
    console.log(f"[green]  ✓ {job.company} enriched ({elapsed:.1f}s)[/green]")
    return intel
