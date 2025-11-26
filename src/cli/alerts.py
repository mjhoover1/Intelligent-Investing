"""Alerts CLI commands."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from sqlalchemy import Integer

from src.db.database import get_db
from src.db.models import User
from src.core.alerts.repository import AlertRepository
from src.core.alerts.service import AlertService
from src.core.alerts.notifier import console_notifier
from src.core.alerts.models import AlertContextData
from src.ai.context.generator import get_context_generator, MockContextGenerator
from src.config import get_settings

console = Console()
app = typer.Typer()
settings = get_settings()


@app.command("test")
def test_alert(
    symbol: str = typer.Option("TEST", "--symbol", "-s", help="Symbol for test alert"),
    message: str = typer.Option(
        "This is a test alert to verify the notification system is working.",
        "--message",
        "-m",
        help="Test message",
    ),
):
    """Create and display a test alert."""
    with get_db() as db:
        # Get default user
        user = db.query(User).filter_by(email=settings.default_user_email).first()
        if not user:
            user = User(email=settings.default_user_email)
            db.add(user)
            db.flush()

        service = AlertService(db, notifier=console_notifier)
        alert = service.create_test_alert(
            user_id=user.id,
            symbol=symbol,
            message=message,
            notify=True,
        )

        console.print(f"\n[green]Test alert created with ID:[/green] {alert.id}")


@app.command("history")
def alert_history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of alerts to show"),
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Filter by symbol"),
):
    """Show alert history."""
    with get_db() as db:
        repo = AlertRepository(db)

        if symbol:
            alerts = repo.get_by_symbol(symbol.upper(), limit=limit)
        else:
            alerts = repo.get_recent(limit=limit)

        if not alerts:
            console.print("[yellow]No alerts found.[/yellow]")
            return

        table = Table(title=f"Alert History (last {len(alerts)})")
        table.add_column("Time", style="dim")
        table.add_column("Symbol", style="cyan")
        table.add_column("Message")
        table.add_column("AI Summary", max_width=40)

        for alert in alerts:
            time_str = alert.triggered_at.strftime("%Y-%m-%d %H:%M")
            ai_summary = alert.ai_summary[:40] + "..." if alert.ai_summary and len(alert.ai_summary) > 40 else (alert.ai_summary or "[dim]-[/dim]")

            table.add_row(
                time_str,
                alert.symbol,
                alert.message[:50] + ("..." if len(alert.message) > 50 else ""),
                ai_summary,
            )

        console.print(table)


@app.command("context")
def generate_context(
    symbol: str = typer.Argument(..., help="Stock symbol"),
    message: str = typer.Argument(..., help="Alert message/reason"),
    price: float = typer.Option(None, "--price", "-p", help="Current price (fetches if not provided)"),
    cost_basis: float = typer.Option(None, "--cost", "-c", help="Cost basis"),
    use_mock: bool = typer.Option(False, "--mock", help="Use mock generator instead of OpenAI"),
):
    """Generate AI context for an alert scenario."""
    symbol = symbol.upper()

    # Get price if not provided
    if price is None:
        with get_db() as db:
            from src.data.market.provider import market_data
            price = market_data.get_price(symbol, db)
            if price is None:
                console.print(f"[red]Error:[/red] Could not fetch price for {symbol}")
                raise typer.Exit(1)
            console.print(f"[dim]Fetched current price: ${price:.2f}[/dim]\n")

    # Calculate percent change if we have cost basis
    percent_change = None
    if cost_basis and cost_basis > 0:
        percent_change = (price - cost_basis) / cost_basis * 100

    # Build context data
    context_data = AlertContextData(
        symbol=symbol,
        rule_name="Manual Test",
        rule_type="manual",
        threshold=0,
        current_price=price,
        cost_basis=cost_basis,
        percent_change=percent_change,
        message=message,
    )

    # Get generator
    if use_mock:
        generator = MockContextGenerator()
        console.print("[dim]Using mock generator[/dim]\n")
    else:
        generator = get_context_generator()
        if isinstance(generator, MockContextGenerator):
            console.print("[yellow]Warning:[/yellow] OpenAI not configured, using mock generator\n")
        else:
            console.print("[dim]Using OpenAI generator[/dim]\n")

    # Generate context
    console.print("[bold]Generating AI context...[/bold]\n")

    context = generator.generate(context_data)

    if context:
        console.print("[bold green]AI Context:[/bold green]")
        console.print(context)
    else:
        console.print("[red]Failed to generate context.[/red]")


@app.command("clear")
def clear_alerts(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear all alerts (for development)."""
    if not force:
        confirm = typer.confirm("Clear all alerts? This cannot be undone.")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    with get_db() as db:
        repo = AlertRepository(db)
        count = repo.clear_all()
        console.print(f"[green]Cleared {count} alert(s).[/green]")


@app.command("show")
def show_alert(
    alert_id: str = typer.Argument(..., help="Alert ID to show"),
):
    """Show details of a specific alert."""
    with get_db() as db:
        repo = AlertRepository(db)
        alert = repo.get_by_id(alert_id)

        if not alert:
            console.print(f"[red]Error:[/red] Alert {alert_id} not found.")
            raise typer.Exit(1)

        # Display alert details
        console_notifier.notify(alert)

        # Show additional details
        console.print(f"\n[dim]ID: {alert.id}[/dim]")
        console.print(f"[dim]Rule ID: {alert.rule_id}[/dim]")
        if alert.holding_id:
            console.print(f"[dim]Holding ID: {alert.holding_id}[/dim]")
        console.print(f"[dim]Notified: {'Yes' if alert.notified else 'No'}[/dim]")

        # Show feedback if present
        if alert.feedback:
            console.print(f"\n[bold]Feedback:[/bold] {alert.feedback}")
            if alert.feedback_notes:
                console.print(f"[dim]Notes: {alert.feedback_notes}[/dim]")
            if alert.price_at_alert:
                console.print(f"[dim]Price at alert: ${alert.price_at_alert:.2f}[/dim]")


@app.command("feedback")
def add_feedback(
    alert_id: str = typer.Argument(..., help="Alert ID to add feedback to"),
    rating: str = typer.Argument(..., help="Feedback: useful, noise, or actionable"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Additional notes"),
):
    """Add feedback to an alert for signal quality tracking.

    Ratings:
    - useful: Alert provided valuable info
    - noise: Alert was not helpful
    - actionable: Alert led to a trade decision
    """
    valid_ratings = ["useful", "noise", "actionable"]
    if rating.lower() not in valid_ratings:
        console.print(f"[red]Error:[/red] Rating must be one of: {', '.join(valid_ratings)}")
        raise typer.Exit(1)

    from datetime import datetime

    with get_db() as db:
        repo = AlertRepository(db)
        alert = repo.get_by_id(alert_id)

        if not alert:
            console.print(f"[red]Error:[/red] Alert {alert_id} not found.")
            raise typer.Exit(1)

        # Update feedback
        alert.feedback = rating.lower()
        alert.feedback_notes = notes
        alert.feedback_at = datetime.utcnow()

        # Capture current price for comparison
        from src.data.market.provider import market_data
        current_price = market_data.get_price(alert.symbol, db)
        if current_price and not alert.price_at_alert:
            # If we don't have price_at_alert, use triggered price from message
            alert.price_at_alert = current_price

        db.commit()

        console.print(f"[green]Feedback recorded for {alert.symbol} alert[/green]")
        console.print(f"Rating: {rating}")
        if notes:
            console.print(f"Notes: {notes}")


@app.command("unrated")
def show_unrated(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of alerts to show"),
):
    """Show alerts without feedback (need review)."""
    with get_db() as db:
        from src.db.models import Alert

        alerts = (
            db.query(Alert)
            .filter(Alert.feedback.is_(None))
            .order_by(Alert.triggered_at.desc())
            .limit(limit)
            .all()
        )

        if not alerts:
            console.print("[green]All alerts have been reviewed![/green]")
            return

        table = Table(title=f"Unrated Alerts ({len(alerts)} need review)")
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Time", style="dim")
        table.add_column("Symbol", style="cyan")
        table.add_column("Rule")
        table.add_column("Message", max_width=40)

        for alert in alerts:
            time_str = alert.triggered_at.strftime("%m-%d %H:%M")
            rule_name = alert.rule.name if alert.rule else "?"

            table.add_row(
                alert.id[:8],
                time_str,
                alert.symbol,
                rule_name[:20],
                alert.message[:40] + ("..." if len(alert.message) > 40 else ""),
            )

        console.print(table)
        console.print("\n[dim]Use 'invest alerts feedback <id> <useful|noise|actionable>' to rate[/dim]")


@app.command("stats")
def feedback_stats():
    """Show signal quality statistics."""
    with get_db() as db:
        from src.db.models import Alert, Rule
        from sqlalchemy import func

        # Overall stats
        total = db.query(Alert).count()
        rated = db.query(Alert).filter(Alert.feedback.isnot(None)).count()
        unrated = total - rated

        console.print("[bold]Signal Quality Statistics[/bold]\n")
        console.print(f"Total alerts: {total}")
        console.print(f"Rated: {rated} ({rated/total*100:.0f}%)" if total > 0 else "Rated: 0")
        console.print(f"Unrated: {unrated}\n")

        if rated == 0:
            console.print("[yellow]No feedback data yet. Rate some alerts first![/yellow]")
            return

        # Feedback breakdown
        feedback_counts = (
            db.query(Alert.feedback, func.count(Alert.id))
            .filter(Alert.feedback.isnot(None))
            .group_by(Alert.feedback)
            .all()
        )

        table = Table(title="Feedback Breakdown")
        table.add_column("Rating")
        table.add_column("Count")
        table.add_column("Percentage")

        for feedback, count in feedback_counts:
            pct = count / rated * 100
            style = "green" if feedback == "useful" or feedback == "actionable" else "red"
            table.add_row(feedback, str(count), f"[{style}]{pct:.1f}%[/{style}]")

        console.print(table)

        # By rule type
        console.print("\n[bold]By Rule Type[/bold]")

        rule_stats = (
            db.query(
                Rule.name,
                Rule.rule_type,
                func.count(Alert.id).label("total"),
                func.sum(func.cast(Alert.feedback == "useful", Integer)).label("useful"),
                func.sum(func.cast(Alert.feedback == "actionable", Integer)).label("actionable"),
            )
            .join(Alert, Alert.rule_id == Rule.id)
            .filter(Alert.feedback.isnot(None))
            .group_by(Rule.id)
            .all()
        )

        if rule_stats:
            rule_table = Table(title="Signal Quality by Rule")
            rule_table.add_column("Rule")
            rule_table.add_column("Type")
            rule_table.add_column("Alerts")
            rule_table.add_column("Useful %")

            for name, rule_type, total, useful, actionable in rule_stats:
                useful = useful or 0
                actionable = actionable or 0
                good_pct = (useful + actionable) / total * 100 if total > 0 else 0
                style = "green" if good_pct >= 50 else "yellow" if good_pct >= 25 else "red"
                rule_table.add_row(
                    name[:25],
                    rule_type[:20],
                    str(total),
                    f"[{style}]{good_pct:.0f}%[/{style}]",
                )

            console.print(rule_table)
