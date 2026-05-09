"""Configuration loader — reads env vars and provides constants for the pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- LinkedIn ---
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# --- Agent behavior ---
MAX_LEADS_PER_DAY = int(os.getenv("MAX_LEADS_PER_DAY", "10"))
MIN_FIT_SCORE = int(os.getenv("MIN_FIT_SCORE", "7"))
OUTREACH_MODE = os.getenv("OUTREACH_MODE", "local")  # "local" | "auto_send"
DAILY_DIGEST_EMAIL = os.getenv("DAILY_DIGEST_EMAIL", "f.ahmad.job@gmail.com")

# --- SMTP (only used when OUTREACH_MODE=auto_send) ---
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
CACHE_PATH = BASE_DIR / ".enrichment_cache.json"
FAILED_LEADS_PATH = BASE_DIR / "failed_leads.jsonl"
PIPELINE_CSV = BASE_DIR / "pipeline.csv"
DRAFTS_DIR = BASE_DIR / "outreach_drafts"
LINKEDIN_SESSION = BASE_DIR / ".linkedin_session.json"

# --- Model selection (cost-optimized) ---
SCORER_MODEL = "claude-haiku-4-5-20251001"
WRITER_MODEL = "claude-sonnet-4-20250514"
ANALYST_MODEL = "claude-haiku-4-5-20251001"

# --- FIRDOSH'S PROFILE (inlined for prompt assembly) ---
FIRDOSH_PROFILE = {
    "name": "Firdosh Ahmad",
    "email": "f.ahmad.job@gmail.com",
    "location": "India (IST — available 6am–2pm IST)",
    "rate": "$35–60/hr USD",
    "core_skills": [
        "RAG pipeline design and implementation",
        "Multi-agent system orchestration (FastAPI, LLM APIs)",
        "AI observability and evaluation (MLflow, prompt eval)",
        "LLM-powered workflow automation",
        "Full-stack engineering (React, Next.js, FastAPI, PostgreSQL)",
        "Frontend performance optimization",
    ],
    "certifications": ["Anthropic Claude Certification (2026)"],
    "projects": {
        "rag": {
            "name": "Objs.ai",
            "period": "Feb–Apr 2026",
            "summary": "AI document processing with RAG, event-driven webhooks, dynamic UI",
        },
        "agents": {
            "name": "Zemuria Venture Studio",
            "period": "Apr 2025–Jan 2026",
            "summary": "Multi-agent FastAPI system, RAG pipelines, MLflow observability, RFP automation",
        },
        "fullstack": {
            "name": "The Crazy Mountaineer",
            "period": "Mar–Aug 2023",
            "summary": "Full-stack travel booking platform (React, FastAPI, PostgreSQL)",
        },
    },
    "achievements": [
        "Reduced API latency by ~6.6s in production",
        "LeetCode: 950+ problems solved, Rating 1852, Top 5.96% globally",
        "IEEE GCAT Conference: multi-object tracking (MOTA 78.1) using YOLOv4 + Deep SORT",
    ],
}
