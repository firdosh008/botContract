"""Outreach delivery — saves drafts as local .md files, or sends via SMTP."""

import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from rich.console import Console
from models.schemas import OutreachDraft
from agent.config import (
    OUTREACH_MODE, DRAFTS_DIR, SMTP_HOST, SMTP_PORT,
    SMTP_EMAIL, SMTP_APP_PASSWORD, DAILY_DIGEST_EMAIL,
)

console = Console()


def save_draft_locally(draft: OutreachDraft):
    """
    Save an outreach draft as a local Markdown file in outreach_drafts/.

    Args:
        draft: The OutreachDraft to save.
    """
    DRAFTS_DIR.mkdir(exist_ok=True)

    channel_label = "email" if draft.channel == "email" else "dm"
    safe_company = "".join(c for c in draft.company if c.isalnum() or c in " _-").rstrip()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{date_str}_{safe_company}_{channel_label}.md"
    filepath = DRAFTS_DIR / filename

    content = f"""# Outreach Draft: {draft.company}

**Channel:** {draft.channel}
**Status:** {draft.status}
**Personalization Score:** {draft.personalization_score}/10
**Word Count:** {draft.word_count}
**Created:** {draft.created_at.isoformat()}

{f"## Subject: {draft.subject}" if draft.subject else ""}

---

{draft.body}
"""
    filepath.write_text(content, encoding="utf-8")
    console.log(f"[green]  ✓ Draft saved: {filepath.name}[/green]")


def send_via_smtp(draft: OutreachDraft) -> bool:
    """
    Send an outreach email via SMTP.

    Only called when OUTREACH_MODE is 'auto_send'.

    Args:
        draft: The OutreachDraft with subject and body.

    Returns:
        True if sent successfully.
    """
    if draft.channel != "email":
        return False

    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        console.log("[red]SMTP not configured. Set SMTP_EMAIL and SMTP_APP_PASSWORD in .env[/red]")
        return False

    t0 = time.time()
    console.log(f"[bold yellow]Sending: {draft.company} via SMTP...[/bold yellow]")

    msg = MIMEText(draft.body)
    msg["Subject"] = draft.subject or f"Proposal: {draft.company}"
    msg["From"] = SMTP_EMAIL
    msg["To"] = DAILY_DIGEST_EMAIL  # Sent to Firdosh for review/BCC the actual recipient

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.send_message(msg)
        server.quit()

        elapsed = time.time() - t0
        console.log(f"[green]  ✓ Email sent ({elapsed:.1f}s)[/green]")
        return True
    except Exception as e:
        console.log(f"[red]SMTP send failed: {e}[/red]")
        return False
