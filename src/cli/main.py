"""Main CLI entry point using Typer."""

import logging

import typer
from rich.console import Console

from src.db.database import init_db
from src.config import PRODUCT_NAME, PRODUCT_TAGLINE, PRODUCT_VERSION

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
    help=f"{PRODUCT_NAME} — {PRODUCT_TAGLINE}",
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
from src.cli.strategies import app as strategies_app
from src.cli.users import app as users_app
from src.cli.brokers import app as brokers_app

app.add_typer(portfolio_app, name="portfolio", help="Manage portfolio holdings")
app.add_typer(rules_app, name="rules", help="Manage alert rules")
app.add_typer(alerts_app, name="alerts", help="View and manage alerts")
app.add_typer(monitor_app, name="monitor", help="Run monitoring cycles")
app.add_typer(notifications_app, name="notifications", help="Manage notification settings")
app.add_typer(strategies_app, name="strategies", help="Strategy presets - one-click rule bundles")
app.add_typer(users_app, name="users", help="User management and authentication")
app.add_typer(brokers_app, name="brokers", help="Broker integrations and position sync")


ASCII_BANNER = """
[bold #4F46E5]███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗
██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║
███████╗██║██║  ███╗██╔██╗ ██║███████║██║
╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║
███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗
╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝

███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝[/]

[bold #14B8A6]        Your AI-powered market watchdog.[/]
"""


@app.command()
def version():
    """Show version information with ASCII banner."""
    console.print(ASCII_BANNER)
    console.print(f"[bold]Version:[/] {PRODUCT_VERSION}")
    console.print(f"[bold]Tagline:[/] {PRODUCT_TAGLINE}")


if __name__ == "__main__":
    app()
