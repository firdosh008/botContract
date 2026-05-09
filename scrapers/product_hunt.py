"""Scrape Product Hunt for recent AI launches — potential freelance clients."""

import asyncio
import json
import re
import time
from datetime import datetime, timezone
import httpx
from models.schemas import JobLead, is_target_country
from rich.console import Console

console = Console()

PH_URL = "https://www.producthunt.com/topics/artificial-intelligence"
MIN_UPVOTES = 30


async def scrape_product_hunt() -> list[JobLead]:
    """Scrape Product Hunt for AI products — founders may need freelance help."""
    console.log("[blue]Product Hunt: scanning AI launches...[/blue]")
    t0 = time.time()

    leads = []

    async with httpx.AsyncClient(
        timeout=30,
        headers={
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/125.0.0.0 Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml",
        },
    ) as client:
        try:
            resp = await client.get(PH_URL, follow_redirects=True)
            html = resp.text
        except Exception as e:
            console.log(f"[red]Product Hunt HTTP failed: {e}[/red]")
            return leads

        # Strategy 1: __APOLLO_STATE__ (most reliable)
        apollo_match = re.search(
            r'<script[^>]*>window\.__APOLLO_STATE__\s*=\s*({.*?});</script>',
            html, re.DOTALL,
        )
        if not apollo_match:
            # Try alternate formats
            apollo_match = re.search(r'__APOLLO_STATE__\s*=\s*({.*?});', html, re.DOTALL)

        if apollo_match:
            try:
                data = json.loads(apollo_match.group(1))
                products_found = 0

                for key, obj in data.items():
                    if not isinstance(obj, dict):
                        continue
                    if obj.get("__typename") == "Post" and obj.get("name"):
                        name = str(obj.get("name", ""))
                        tagline = str(obj.get("tagline", ""))
                        desc = str(obj.get("description", tagline))
                        url = str(obj.get("url", f"https://producthunt.com/posts/{obj.get('slug', '')}"))
                        try:
                            votes = int(obj.get("votesCount", 0))
                        except (ValueError, TypeError):
                            votes = 0

                        if votes < MIN_UPVOTES:
                            continue

                        # Get maker info
                        makers = []
                        maker_refs = obj.get("makers", [])
                        if isinstance(maker_refs, list):
                            for m in maker_refs:
                                if isinstance(m, dict):
                                    maker_name = m.get("name", "")
                                    maker_username = m.get("username", "")
                                    if maker_name:
                                        makers.append(f"{maker_name} (@{maker_username})" if maker_username else maker_name)

                        maker_str = ", ".join(makers[:3]) if makers else "Unknown"
                        description = f"Product: {name}\nTagline: {tagline}\nDescription: {desc}\nMakers: {maker_str}\nUpvotes: {votes}"

                        leads.append(JobLead(
                            id=f"ph-{hash(url or name)}",
                            title=f"AI Product Launch: {name}",
                            company=name,
                            location="Remote (assumed)",
                            source="product_hunt",
                            posted_at=datetime.now(timezone.utc),
                            description=description,
                            apply_url=url or f"https://producthunt.com/search?q={name.replace(' ', '+')}",
                            is_remote=True,
                            is_contract=True,
                            tech_stack=[],
                        ))
                        products_found += 1

                console.log(f"[dim]  Apollo cache: {products_found} products found[/dim]")
            except (json.JSONDecodeError, KeyError) as e:
                console.log(f"[dim]  Apollo parse error: {e}[/dim]")

        # Strategy 2: Fallback regex on HTML
        if not leads:
            # Look for product cards in the HTML
            card_pattern = r'<a[^>]*href="(/posts/[^"]+)"[^>]*>.*?<h3[^>]*>([^<]+)</h3>'
            matches = re.findall(card_pattern, html, re.DOTALL | re.IGNORECASE)
            for url_path, name in matches:
                leads.append(JobLead(
                    id=f"ph-{hash(url_path)}",
                    title=f"AI Product: {name.strip()}",
                    company=name.strip(),
                    location="Remote (assumed)",
                    source="product_hunt",
                    posted_at=datetime.now(timezone.utc),
                    description=f"Product Hunt launch: {name.strip()}",
                    apply_url=f"https://producthunt.com{url_path}",
                    is_remote=True,
                    is_contract=True,
                ))
            console.log(f"[dim]  Regex fallback: {len(leads)} products[/dim]")

    elapsed = time.time() - t0
    console.log(f"[green]Product Hunt: {len(leads)} leads ({elapsed:.1f}s)[/green]")
    return leads
