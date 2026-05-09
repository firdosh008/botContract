"""
Manual backfill script — reprocesses failed leads from failed_leads.jsonl into Notion.

Usage:
    python scripts/backfill.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from agent.logger import log_to_pipeline
from models.schemas import EnrichedLead

console = Console()


def backfill_failed_leads():
    """Read failed_leads.jsonl and retry Notion writes."""
    failed_path = Path("failed_leads.jsonl")
    if not failed_path.exists():
        console.print("[green]No failed leads to backfill.[/green]")
        return

    lines = failed_path.read_text(encoding="utf-8").strip().split("\n")
    if not lines or lines == [""]:
        console.print("[green]No failed leads to backfill.[/green]")
        return

    console.print(f"Found {len(lines)} failed leads to backfill.")

    success_count = 0
    remaining = []

    for line in lines:
        try:
            record = json.loads(line)
            lead = EnrichedLead(**record["data"])
            success = log_to_pipeline(lead)
            if success:
                success_count += 1
            else:
                remaining.append(line)
        except Exception as e:
            console.print(f"[red]Error processing record: {e}[/red]")
            remaining.append(line)

    # Rewrite the file with only the leads that still failed
    if remaining:
        failed_path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
    else:
        failed_path.unlink()

    console.print(f"[green]✅ Backfill complete: {success_count} succeeded, {len(remaining)} still failed[/green]")


if __name__ == "__main__":
    backfill_failed_leads()
