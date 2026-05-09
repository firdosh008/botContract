"""Data models for the client sourcing pipeline."""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# High-paying countries Firdosh targets
TARGET_COUNTRIES = ["US", "USA", "United States", "UK", "United Kingdom", "Canada", "Australia",
                    "Germany", "France", "Netherlands", "Sweden", "Switzerland", "Ireland",
                    "Denmark", "Norway", "Finland", "Belgium", "Austria", "New Zealand"]

def is_target_country(location: str) -> bool:
    """Check if a location string matches a target high-paying country."""
    loc_lower = location.lower()
    for country in TARGET_COUNTRIES:
        if country.lower() in loc_lower:
            return True
    # Also match "Remote (EU)", "Remote (Europe)", "Remote US", etc.
    for region in ["eu", "europe", "americas", "emea", "worldwide", "global"]:
        if region in loc_lower:
            return True
    return False


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
                "salary_range": "$80k–$120k or $60–$100/hr",
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
    is_contract: bool = Field(default=False, description="True if contract/freelance role")
    country: str = Field(default="", description="Detected country (US, UK, etc.)")
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
    """Enriched company context for personalization — focused on actionable contact info."""

    name: str
    website: Optional[str] = None
    size_estimate: Optional[str] = None
    funding_stage: Optional[str] = None
    tech_stack: list[str] = Field(default_factory=list)
    recent_news: Optional[str] = None
    # Contact info — the key fields for outreach
    contact_name: Optional[str] = None          # Founder, CTO, or hiring manager
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None         # Best guess email
    contact_linkedin: Optional[str] = None
    company_email: Optional[str] = None         # General contact or careers email
    pain_point_hypothesis: str = Field(
        description="1-sentence hypothesis of what AI problem they're trying to solve"
    )


class OutreachDraft(BaseModel):
    """Generated outreach content ready for review."""

    lead_id: str
    company: str
    channel: Literal["email", "linkedin_dm"]
    subject: Optional[str] = None
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
    logged: bool = False
