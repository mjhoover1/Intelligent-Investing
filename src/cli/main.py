"""Main CLI entry point using Typer."""

import logging

import typer
from rich.console import Console

from src.db.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Reduce noise from third-party libraries
logging.getLogger("yfinance").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

console = Console()
app = typer.Typer(
    name="invest",
    help="Intelligent Investing - AI Portfolio Copilot CLI",
    add_completion=False,
)


@app.callback()
def main_callback():
    """Initialize database on startup."""
    init_db()


# Import and add subcommands
from src.cli.portfolio import app as portfolio_app
from src.cli.rules import app as rules_app
from src.cli.alerts import app as alerts_app
from src.cli.monitor import app as monitor_app
from src.cli.notifications import app as notifications_app

app.add_typer(portfolio_app, name="portfolio", help="Manage portfolio holdings")
app.add_typer(rules_app, name="rules", help="Manage alert rules")
app.add_typer(alerts_app, name="alerts", help="View and manage alerts")
app.add_typer(monitor_app, name="monitor", help="Run monitoring cycles")
app.add_typer(notifications_app, name="notifications", help="Manage notification settings")


@app.command()
def version():
    """Show version information."""
    console.print("[bold]Intelligent Investing[/bold] v0.1.0")
    console.print("AI Portfolio Copilot - MVP")


if __name__ == "__main__":
    app()
