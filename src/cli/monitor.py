"""Monitor CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console

from src.config import get_settings

console = Console()
app = typer.Typer()
settings = get_settings()


@app.command("run")
def run_once(
    with_ai: bool = typer.Option(False, "--ai", help="Generate AI context for alerts"),
    ignore_cooldown: bool = typer.Option(
        False, "--ignore-cooldown", "-i", help="Ignore rule cooldowns"
    ),
):
    """Run a single monitoring cycle."""
    from src.core.monitor import run_monitor_cycle

    console.print("[bold]Running monitoring cycle...[/bold]\n")

    alerts = run_monitor_cycle(use_ai=with_ai, ignore_cooldown=ignore_cooldown)

    if not alerts:
        console.print("[green]No rules triggered.[/green] All conditions within thresholds.")
    else:
        console.print(f"\n[bold green]Created {len(alerts)} alert(s)[/bold green]")


@app.command("start")
def start_daemon(
    interval: int = typer.Option(
        None,
        "--interval",
        "-n",
        help=f"Seconds between cycles (default: {settings.monitor_interval_seconds})",
    ),
    with_ai: bool = typer.Option(False, "--ai", help="Generate AI context for alerts"),
    ignore_cooldown: bool = typer.Option(
        False, "--ignore-cooldown", "-i", help="Ignore rule cooldowns"
    ),
):
    """Start the monitoring daemon (runs continuously)."""
    from src.core.scheduler import start_scheduler

    effective_interval = interval or settings.monitor_interval_seconds

    console.print("[bold]Starting Signal Sentinel Monitor[/bold]")
    console.print(f"  Interval: {effective_interval} seconds")
    console.print(f"  AI Context: {'enabled' if with_ai else 'disabled'}")
    console.print(f"  Cooldown: {'ignored' if ignore_cooldown else 'enabled'}")
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    start_scheduler(
        interval_seconds=effective_interval,
        use_ai=with_ai,
        ignore_cooldown=ignore_cooldown,
    )


@app.command("status")
def show_status():
    """Show current monitoring status and configuration."""
    from src.db.database import get_db
    from src.db.models import User
    from src.core.portfolio.repository import HoldingRepository
    from src.core.rules.repository import RuleRepository
    from src.core.alerts.repository import AlertRepository

    with get_db() as db:
        # Get default user
        user = db.query(User).filter_by(email=settings.default_user_email).first()
        if not user:
            console.print("[yellow]No user configured.[/yellow]")
            return

        # Get counts
        holding_repo = HoldingRepository(db)
        rule_repo = RuleRepository(db)
        alert_repo = AlertRepository(db)

        holdings = holding_repo.get_all()
        rules = rule_repo.get_all()
        active_rules = rule_repo.get_active()
        alerts = alert_repo.get_recent(limit=1)

        console.print("[bold]Monitor Status[/bold]\n")
        console.print(f"  Holdings: {len(holdings)}")
        console.print(f"  Rules: {len(rules)} ({len(active_rules)} active)")
        console.print(f"  Default interval: {settings.monitor_interval_seconds}s")

        if alerts:
            last_alert = alerts[0]
            console.print(f"  Last alert: {last_alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            console.print("  Last alert: [dim]None[/dim]")

        # Show symbols being monitored
        if holdings:
            symbols = sorted(set(h.symbol for h in holdings))
            console.print(f"\n  Monitoring: {', '.join(symbols)}")
