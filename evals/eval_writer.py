"""
Evaluate outreach quality — checks generated emails and DMs for:
- Banned phrases
- Word limits
- Personalization score minimum
- Subject line length
- Company-specific references
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from models.schemas import OutreachDraft

console = Console()

BANNED_PHRASES = [
    "hope this finds you",
    "I wanted to reach out",
    "leverage",
    "passionate about",
    "synergies",
    "circle back",
    "touch base",
    "I am passionate",
]

EMAIL_MAX_WORDS = 150
DM_MAX_WORDS = 100
SUBJECT_MAX_WORDS = 8
MIN_PERSONALIZATION_SCORE = 7


def check_draft(draft: OutreachDraft) -> list[str]:
    """
    Run all quality checks on a single draft.

    Args:
        draft: The OutreachDraft to evaluate.

    Returns:
        List of issue descriptions (empty = clean).
    """
    issues = []
    body_lower = draft.body.lower()

    # Banned phrases
    for phrase in BANNED_PHRASES:
        if phrase.lower() in body_lower:
            issues.append(f"Banned phrase: '{phrase}'")

    # Word limits
    word_count = len(draft.body.split())
    if draft.channel == "email" and word_count > EMAIL_MAX_WORDS:
        issues.append(f"Email too long: {word_count} words (max {EMAIL_MAX_WORDS})")
    if draft.channel == "linkedin_dm" and word_count > DM_MAX_WORDS:
        issues.append(f"DM too long: {word_count} words (max {DM_MAX_WORDS})")

    # Subject line
    if draft.subject:
        subject_words = len(draft.subject.split())
        if subject_words > SUBJECT_MAX_WORDS:
            issues.append(f"Subject too long: {subject_words} words (max {SUBJECT_MAX_WORDS})")

    # Personalization score
    if draft.personalization_score < MIN_PERSONALIZATION_SCORE:
        issues.append(f"Personalization score too low: {draft.personalization_score} (min {MIN_PERSONALIZATION_SCORE})")

    # Company mention
    if draft.company.lower() not in body_lower:
        issues.append(f"Company name '{draft.company}' not found in body")

    return issues


def evaluate_drafts(drafts: list[OutreachDraft]) -> dict:
    """
    Evaluate a batch of outreach drafts and print a report.

    Args:
        drafts: List of OutreachDraft objects to evaluate.

    Returns:
        Dict with summary statistics.
    """
    console.rule("[bold blue]🧪 Outreach Quality Evaluation[/bold blue]")

    if not drafts:
        console.print("[yellow]No drafts to evaluate.[/yellow]")
        return {"total": 0, "passed": 0, "issues": []}

    results = []
    for draft in drafts:
        issues = check_draft(draft)
        passed = len(issues) == 0
        results.append({
            "company": draft.company,
            "channel": draft.channel,
            "passed": passed,
            "issues": issues,
            "word_count": len(draft.body.split()),
            "personalization_score": draft.personalization_score,
        })

    # Print results
    table = Table("Company", "Channel", "Words", "Score", "Status", "Issues")
    for r in results:
        status = "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]"
        issues_str = "; ".join(r["issues"]) if r["issues"] else "—"
        table.add_row(
            r["company"],
            r["channel"],
            str(r["word_count"]),
            str(r["personalization_score"]),
            status,
            issues_str,
        )
    console.print(table)

    # Summary
    total = len(drafts)
    passed = sum(1 for r in results if r["passed"])
    pass_rate = passed / total * 100 if total else 0

    console.rule("[bold]Summary[/bold]")
    summary = Table("Metric", "Value")
    summary.add_row("Total drafts", str(total))
    summary.add_row("Passed all checks", f"{passed}/{total} ({pass_rate:.0f}%)")
    summary.add_row("With banned phrases", str(sum(1 for r in results if any("Banned phrase" in i for i in r["issues"]))))
    summary.add_row("Over word limit", str(sum(1 for r in results if any("too long" in i for i in r["issues"]))))
    summary.add_row("Missing company mention", str(sum(1 for r in results if any("Company name" in i for i in r["issues"]))))
    console.print(summary)

    return {
        "total": total,
        "passed": passed,
        "pass_rate": pass_rate,
        "results": results,
    }


if __name__ == "__main__":
    # When run directly, demonstrate with a placeholder
    console.print("[yellow]Run this via agent.main — it evaluates real generated drafts.[/yellow]")
    console.print("[dim]Example usage:[/dim]")
    console.print("[dim]  from evals.eval_writer import evaluate_drafts[/dim]")
    console.print("[dim]  evaluate_drafts([lead.email_draft for lead in enriched if lead.email_draft])[/dim]")
