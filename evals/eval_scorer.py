"""
Evaluate job fit scorer accuracy against 20 synthetic test cases.

Each test case has an expected minimum score. The eval runs all 20,
computes mean score deviation, and prints pass/fail for each.
Target: >85% of cases within ±1.5 of expected score.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from models.schemas import JobLead
from agent.scorer import score_job_fit
from agent.config import MIN_FIT_SCORE

console = Console()


def load_test_cases() -> list[dict]:
    """Load the synthetic test cases from JSON."""
    path = Path(__file__).parent / "test_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run_eval() -> dict:
    """
    Run the full evaluation suite.

    Returns:
        Dict with summary statistics and per-case results.
    """
    console.rule("[bold blue]🧪 Fit Scorer Evaluation[/bold blue]")

    test_cases = load_test_cases()
    results = []
    total_deviation = 0
    within_tolerance = 0

    for case in test_cases:
        expected_min = case["expected_min_score"]
        category = case["category"]

        job_data = case["job"]
        job = JobLead(**job_data)

        console.print(f"\n[bold]Testing: {case['id']} ({category})[/bold]")
        console.print(f"  Title: {job.title}")
        console.print(f"  Expected min score: {expected_min}")

        try:
            fit = score_job_fit(job)
            if fit is None:
                actual = 0  # Discarded — below threshold
                deviation = actual - expected_min
                passed = expected_min <= MIN_FIT_SCORE  # Expected discard
            else:
                actual = fit.score
                deviation = actual - expected_min
                passed = deviation >= -1.5  # Within 1.5 below expected

            within_tolerance += 1 if abs(deviation) <= 1.5 else 0
            total_deviation += abs(deviation)

            symbol = "[green]✓[/green]" if passed else "[red]✗[/red]"
            console.print(
                f"  {symbol} Actual: {actual} | Deviation: {deviation:+.1f} | "
                f"Matched: {fit.matched_skills if fit else 'N/A'}"
            )

        except Exception as e:
            console.print(f"  [red]✗ Error: {e}[/red]")
            actual = -1
            deviation = -99
            passed = False

        results.append({
            "id": case["id"],
            "category": category,
            "expected_min": expected_min,
            "actual": actual,
            "deviation": deviation,
            "passed": passed,
        })

    # Summary
    total = len(test_cases)
    pass_rate = sum(1 for r in results if r["passed"]) / total * 100
    within_rate = within_tolerance / total * 100
    mean_deviation = total_deviation / total

    console.rule("[bold]Summary[/bold]")
    table = Table("Metric", "Value")
    table.add_row("Total cases", str(total))
    table.add_row("Passed", f"{sum(1 for r in results if r['passed'])}/{total} ({pass_rate:.0f}%)")
    table.add_row("Within ±1.5 tolerance", f"{within_tolerance}/{total} ({within_rate:.0f}%)")
    table.add_row("Mean absolute deviation", f"{mean_deviation:.2f}")
    table.add_row("Target", ">85% within ±1.5")
    table.add_row(
        "Status",
        "[green]PASS[/green]" if within_rate >= 85 else "[red]FAIL[/red]"
    )
    console.print(table)

    # Per-category breakdown
    console.rule("[bold]By Category[/bold]")
    cat_table = Table("Category", "Count", "Passed", "Rate")
    for cat in ["perfect_match", "good_match", "mediocre", "hard_reject"]:
        cat_results = [r for r in results if r["category"] == cat]
        cat_pass = sum(1 for r in cat_results if r["passed"])
        cat_table.add_row(cat, str(len(cat_results)), str(cat_pass), f"{cat_pass / len(cat_results) * 100:.0f}%")
    console.print(cat_table)

    return {
        "pass_rate": pass_rate,
        "within_tolerance_rate": within_rate,
        "mean_deviation": mean_deviation,
        "results": results,
    }


if __name__ == "__main__":
    run_eval()
