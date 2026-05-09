"""Outreach writer — generates personalized emails and LinkedIn DMs for each lead."""

import json
import time
import anthropic
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt
from rich.console import Console
from models.schemas import JobLead, FitScore, CompanyIntel, OutreachDraft
from agent.config import ANTHROPIC_API_KEY, WRITER_MODEL, PROMPTS_DIR, FIRDOSH_PROFILE

console = Console()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
EMAIL_PROMPT = (PROMPTS_DIR / "email_writer.txt").read_text(encoding="utf-8")
DM_PROMPT = (PROMPTS_DIR / "dm_writer.txt").read_text(encoding="utf-8")

BANNED_PHRASES = [
    "hope this finds you",
    "I wanted to reach out",
    "leverage",
    "passionate about",
    "synergies",
    "circle back",
    "touch base",
]


def _pick_relevant_project(fit: FitScore, job_description: str) -> dict:
    """
    Select the most relevant project from Firdosh's profile for this job.

    Returns:
        The project dict with name and summary.
    """
    text = (job_description + " " + " ".join(fit.matched_skills)).lower()
    if "rag" in text or "document process" in text or "semantic search" in text:
        return FIRDOSH_PROFILE["projects"]["rag"]
    if "agent" in text or "multi-agent" in text or "orchestrat" in text or "rfp" in text:
        return FIRDOSH_PROFILE["projects"]["agents"]
    return FIRDOSH_PROFILE["projects"]["fullstack"]


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(3))
def _call_claude_writer(system_prompt: str, user_message: str) -> str:
    """Call Claude for outreach content generation."""
    response = client.messages.create(
        model=WRITER_MODEL,
        max_tokens=800,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


def _parse_json_response(raw: str) -> dict:
    """Parse Claude's JSON, stripping any markdown fences."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    return json.loads(cleaned)


def _check_quality(draft: OutreachDraft, company: str) -> list[str]:
    """Run quality checks on a generated draft. Returns list of issues."""
    issues = []
    body_lower = draft.body.lower()

    for phrase in BANNED_PHRASES:
        if phrase.lower() in body_lower:
            issues.append(f"Banned phrase found: '{phrase}'")

    words = draft.body.split()
    if draft.channel == "email" and len(words) > 150:
        issues.append(f"Email body exceeds 150 words ({len(words)} words)")

    if draft.channel == "linkedin_dm" and len(words) > 100:
        issues.append(f"DM body exceeds 100 words ({len(words)} words)")

    if draft.subject:
        subject_words = draft.subject.split()
        if len(subject_words) > 8:
            issues.append(f"Subject exceeds 8 words ({len(subject_words)} words)")

    if company.lower() not in body_lower:
        issues.append(f"Company name '{company}' not mentioned in body")

    if draft.personalization_score < 7:
        issues.append(f"Personalization score below 7: {draft.personalization_score}")

    return issues


def _generate_email(job: JobLead, fit: FitScore, intel: CompanyIntel) -> OutreachDraft:
    """Generate a cold email draft for a specific lead."""
    project = _pick_relevant_project(fit, job.description)

    user_message = f"""
JOB TITLE: {job.title}
COMPANY: {job.company}
FIT SCORE: {fit.score}/10
OUTREACH ANGLE: {fit.outreach_angle}
MATCHED SKILLS: {', '.join(fit.matched_skills)}

COMPANY INTEL:
- Size: {intel.size_estimate or 'Unknown'}
- Funding: {intel.funding_stage or 'Unknown'}
- Key person: {intel.key_person_name or 'Unknown'} ({intel.key_person_title or 'Unknown'})
- Pain point: {intel.pain_point_hypothesis}
- Recent news: {intel.recent_news or 'None'}

MOST RELEVANT PROJECT: {project['name']} ({project['period']})
{project['summary']}
"""

    raw = _call_claude_writer(EMAIL_PROMPT, user_message)
    data = _parse_json_response(raw)

    return OutreachDraft(
        lead_id=job.id,
        company=job.company,
        channel="email",
        subject=data.get("subject", f"Re: {job.title} at {job.company}"),
        body=data["body"],
        word_count=data.get("word_count", len(data["body"].split())),
        personalization_score=data.get("personalization_score", 7),
    )


def _generate_dm(job: JobLead, fit: FitScore, intel: CompanyIntel) -> OutreachDraft:
    """Generate a LinkedIn DM draft for a specific lead."""
    project = _pick_relevant_project(fit, job.description)

    user_message = f"""
JOB TITLE: {job.title}
COMPANY: {job.company}
FIT SCORE: {fit.score}/10
OUTREACH ANGLE: {fit.outreach_angle}
KEY PERSON: {intel.key_person_name or 'Hiring Manager'}
TITLE: {intel.key_person_title or 'Unknown'}
PAIN POINT: {intel.pain_point_hypothesis}
RELEVANT PROJECT: {project['name']} — {project['summary']}
"""

    raw = _call_claude_writer(DM_PROMPT, user_message)
    data = _parse_json_response(raw)

    body = data.get("followup_dm", "")
    connection = data.get("connection_note", "")
    full_body = f"CONNECTION NOTE:\n{connection}\n\nFOLLOW-UP DM:\n{body}"

    return OutreachDraft(
        lead_id=job.id,
        company=job.company,
        channel="linkedin_dm",
        body=full_body,
        word_count=len(body.split()),
        personalization_score=data.get("personalization_score", 7),
    )


def generate_outreach(
    job: JobLead,
    fit: FitScore,
    intel: CompanyIntel,
) -> dict:
    """
    Generate outreach content for a lead.

    Produces email and/or LinkedIn DM drafts based on the fit score's
    recommended channel. Each draft is quality-checked and regenerated
    if the initial attempt scores below 7 for personalization.

    Args:
        job: The raw job lead.
        fit: The fit assessment.
        intel: Enriched company data.

    Returns:
        Dict with optional 'email_draft' and 'dm_draft' keys.
    """
    t0 = time.time()
    console.log(f"[blue]Writing outreach for: {job.company}[/blue]")

    result = {}

    if fit.recommended_channel in ("email", "both"):
        for attempt in range(2):
            draft = _generate_email(job, fit, intel)
            issues = _check_quality(draft, job.company)
            if not issues:
                result["email_draft"] = draft
                break
            console.log(f"[yellow]  Email attempt {attempt+1} quality issues: {issues}[/yellow]")
            if attempt == 0:
                # Add stricter instruction implicitly by flagging the issue
                intel.pain_point_hypothesis += f" (Be specific about {job.company}'s exact problem — previous draft was too generic.)"
        if "email_draft" not in result:
            result["email_draft"] = draft

    if fit.recommended_channel in ("linkedin_dm", "both"):
        for attempt in range(2):
            draft = _generate_dm(job, fit, intel)
            issues = _check_quality(draft, job.company)
            if not issues:
                result["dm_draft"] = draft
                break
            console.log(f"[yellow]  DM attempt {attempt+1} quality issues: {issues}[/yellow]")
        if "dm_draft" not in result:
            result["dm_draft"] = draft

    elapsed = time.time() - t0
    console.log(f"[green]  ✓ Outreach generated ({elapsed:.1f}s)[/green]")
    return result
