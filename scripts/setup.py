"""
One-time setup script — validates environment, installs Playwright browser.

Usage:
    python scripts/setup.py
"""

import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

console = Console()


def check_env() -> dict:
    """Check all required environment variables are set."""
    load_dotenv()
    vars_to_check = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "LINKEDIN_EMAIL": os.getenv("LINKEDIN_EMAIL"),
        "LINKEDIN_PASSWORD": os.getenv("LINKEDIN_PASSWORD"),
    }

    results = {}
    for name, value in vars_to_check.items():
        if value:
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            results[name] = f"[green]Set ({masked})[/green]"
        else:
            results[name] = "[red]Missing — add to .env[/red]"

    return results


def check_files() -> dict:
    """Check that required files exist."""
    base = Path(__file__).resolve().parent.parent
    required = [
        ".env",
        "prompts/fit_scorer.txt",
        "prompts/email_writer.txt",
        "prompts/dm_writer.txt",
        "prompts/company_analyst.txt",
    ]

    results = {}
    for path in required:
        full = base / path
        if full.exists():
            results[path] = "[green]Found[/green]"
        else:
            results[path] = "[red]Missing[/red]"

    return results


def check_python_packages() -> dict:
    """Check that required Python packages are installed."""
    packages = [
        "anthropic",
        "pydantic",
        "httpx",
        "dotenv",
        "rich",
        "tenacity",
        "playwright",
    ]

    results = {}
    for pkg in packages:
        try:
            __import__(pkg.replace("-", "_"))
            results[pkg] = "[green]Installed[/green]"
        except ImportError:
            results[pkg] = "[red]Not installed — run: pip install -r requirements.txt[/red]"

    return results


def install_playwright_browser():
    """Ensure Playwright Chromium browser is installed."""
    console.rule("[bold]Playwright Browser[/bold]")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        console.print("[green]Playwright Chromium is ready[/green]")
    except Exception:
        console.print("[yellow]Installing Playwright Chromium browser...[/yellow]")
        try:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True, capture_output=True,
            )
            console.print("[green]Playwright Chromium installed[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to install Playwright: {e.stderr.decode() if e.stderr else e}[/red]")
            console.print("[yellow]Manually run: playwright install chromium[/yellow]")


def test_linkedin_login():
    """Quick test of LinkedIn login to validate credentials."""
    console.rule("[bold]LinkedIn Credentials Test[/bold]")

    linkedin_email = os.getenv("LINKEDIN_EMAIL")
    linkedin_password = os.getenv("LINKEDIN_PASSWORD")

    if not linkedin_email or not linkedin_password:
        console.print("[yellow]LinkedIn credentials not set — skipping test[/yellow]")
        return

    console.print("[blue]Testing LinkedIn login (headless)...[/blue]")
    console.print("[dim]If this hangs, you may need to solve a CAPTCHA manually first.[/dim]")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,  # LinkedIn blocks headless
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
            )
            page = context.new_page()
            page.goto("https://www.linkedin.com/login", timeout=30000)
            page.wait_for_timeout(2000)

            # LinkedIn's actual login field IDs
            page.fill("input#username", linkedin_email)
            page.wait_for_timeout(500)
            page.fill("input#password", linkedin_password)
            page.wait_for_timeout(500)
            page.click("button[type=submit]")
            page.wait_for_timeout(8000)

            if "login" in page.url or "checkpoint" in page.url or "challenge" in page.url:
                console.print("[red]LinkedIn login failed — check credentials or solve CAPTCHA manually[/red]")
                console.print("[yellow]A browser window opened — complete any security check, then re-run.[/yellow]")
            else:
                console.print("[green]LinkedIn login successful[/green]")
                # Save session for reuse
                storage = context.storage_state()
                import json
                Path(".linkedin_session.json").write_text(json.dumps(storage, indent=2))
                console.print("[green]Session saved to .linkedin_session.json[/green]")

            browser.close()
    except Exception as e:
        console.print(f"[red]LinkedIn test error: {e}[/red]")
        console.print("[yellow]LinkedIn may require manual CAPTCHA — try logging in via a real browser once.[/yellow]")


def main():
    """Run the full setup validation."""
    console.rule("[bold blue]Client Sourcing Agent — Setup[/bold blue]")

    # 1. Check env vars
    console.rule("[bold]Environment Variables[/bold]")
    env_table = Table("Variable", "Status")
    for name, status in check_env().items():
        env_table.add_row(name, status)
    console.print(env_table)

    # 2. Check files
    console.rule("[bold]Required Files[/bold]")
    file_table = Table("File", "Status")
    for name, status in check_files().items():
        file_table.add_row(name, status)
    console.print(file_table)

    # 3. Check packages
    console.rule("[bold]Python Packages[/bold]")
    pkg_table = Table("Package", "Status")
    for name, status in check_python_packages().items():
        pkg_table.add_row(name, status)
    console.print(pkg_table)

    # 4. Install Playwright browser
    install_playwright_browser()

    # 5. Test LinkedIn
    test_linkedin_login()

    console.rule("[bold green]Setup Complete[/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Fill in any missing .env values")
    console.print("  2. Run: python -m agent.main")
    console.print("  3. Check outreach_drafts/ for generated emails")
    console.print("  4. Open pipeline.csv in Excel to track your pipeline")


if __name__ == "__main__":
    main()
