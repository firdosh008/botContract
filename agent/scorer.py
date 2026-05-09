"""Job fit scorer — evaluates each lead against Firdosh's profile using Claude."""

import json
import time
import anthropic
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt
from rich.console import Console
from models.schemas import JobLead, FitScore
from agent.config import ANTHROPIC_API_KEY, MIN_FIT_SCORE, SCORER_MODEL, PROMPTS_DIR

console = Console()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
SCORER_PROMPT = (PROMPTS_DIR / "fit_scorer.txt").read_text(encoding="utf-8")


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(3))
def _call_claude_scorer(user_message: str) -> str:
    """Call Claude with the scorer prompt and return raw JSON text."""
    response = client.messages.create(
        model=SCORER_MODEL,
        max_tokens=1000,
        system=SCORER_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


def _parse_scorer_response(raw: str) -> dict:
    """Parse Claude's JSON response, handling markdown fences."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    return json.loads(cleaned)


def score_job_fit(job: JobLead) -> FitScore | None:
    """
    Score a job posting against Firdosh's profile.

    Args:
        job: The raw JobLead to evaluate.

    Returns:
        FitScore if MIN_FIT_SCORE is met, None otherwise (lead discarded).

    Raises:
        ValueError: If Claude returns unparseable JSON after retries.
    """
    t0 = time.time()
    console.log(f"[dim]Scoring: {job.company} — {job.title[:60]}[/dim]")

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

    for attempt in range(3):
        try:
            raw = _call_claude_scorer(user_message)
            data = _parse_scorer_response(raw)
            fit = FitScore(**data)
            break
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == 2:
                raise
            console.log(f"[yellow]Scorer parse failed (attempt {attempt+1}): {e}[/yellow]")
            # Retry with stricter instruction
            user_message += "\n\nYour previous response was not valid JSON. Return ONLY the JSON object with no other text."

    elapsed = time.time() - t0
    if fit.score < MIN_FIT_SCORE:
        console.log(f"[dim]  ✗ Score {fit.score} — discarded (threshold: {MIN_FIT_SCORE})[/dim]")
        return None

    console.log(f"[green]  ✓ Score {fit.score} — keeping ({elapsed:.1f}s)[/green]")
    return fit
