"""Rules CLI commands."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.db.database import get_db
from src.db.models import User
from src.core.rules.models import RuleType
from src.core.rules.repository import RuleRepository
from src.core.rules.engine import RuleEngine
from src.core.portfolio.repository import HoldingRepository
from src.data.market.provider import market_data
from src.config import get_settings

console = Console()
app = typer.Typer()
settings = get_settings()


def get_rule_type_choices() -> str:
    """Get formatted list of rule type choices."""
    return ", ".join([rt.value for rt in RuleType])


@app.command("add")
def add_rule(
    name: str = typer.Argument(..., help="Rule name"),
    rule_type: str = typer.Argument(
        ..., help=f"Rule type: {get_rule_type_choices()}"
    ),
    threshold: float = typer.Argument(..., help="Threshold value (% or $ depending on rule type)"),
    symbol: Optional[str] = typer.Option(
        None, "--symbol", "-s", help="Apply to specific symbol (default: all holdings)"
    ),
    cooldown: int = typer.Option(
        60, "--cooldown", "-c", help="Cooldown minutes between triggers"
    ),
):
    """Add a new rule to monitor holdings."""
    # Validate rule type
    try:
        rt = RuleType(rule_type)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid rule type: {rule_type}")
        console.print(f"Valid types: {get_rule_type_choices()}")
        raise typer.Exit(1)

    # Validate threshold based on rule type
    if rt in (RuleType.RSI_BELOW_VALUE, RuleType.RSI_ABOVE_VALUE):
        if not (0 <= threshold <= 100):
            console.print("[red]Error:[/red] RSI threshold must be between 0 and 100")
            raise typer.Exit(1)
    elif rt in (RuleType.PRICE_BELOW_VALUE, RuleType.PRICE_ABOVE_VALUE):
        if threshold < 0:
            console.print("[red]Error:[/red] Price threshold cannot be negative")
            raise typer.Exit(1)

    # Validate cooldown
    if cooldown < 0:
        console.print("[red]Error:[/red] Cooldown cannot be negative")
        raise typer.Exit(1)

    with get_db() as db:
        repo = RuleRepository(db)

        # Check if rule name already exists
        existing = repo.get_by_name(name)
        if existing:
            console.print(
                f"[yellow]Warning:[/yellow] Rule '{name}' already exists. "
                f"Use a different name or delete the existing rule."
            )
            raise typer.Exit(1)

        rule = repo.create(
            name=name,
            rule_type=rt,
            threshold=threshold,
            symbol=symbol.upper() if symbol else None,
            cooldown_minutes=cooldown,
        )

        # Format threshold display
        if rt in (RuleType.PRICE_BELOW_COST_PCT, RuleType.PRICE_ABOVE_COST_PCT):
            threshold_str = f"{threshold}%"
        else:
            threshold_str = f"${threshold:.2f}"

        scope = f"[cyan]{symbol.upper()}[/cyan]" if symbol else "[dim]all holdings[/dim]"
        console.print(
            f"[green]Added rule:[/green] {rule.name}\n"
            f"  Type: {rt.value}\n"
            f"  Threshold: {threshold_str}\n"
            f"  Applies to: {scope}\n"
            f"  Cooldown: {cooldown} minutes"
        )


@app.command("list")
def list_rules(
    all_rules: bool = typer.Option(False, "--all", "-a", help="Show disabled rules too"),
):
    """List all rules."""
    with get_db() as db:
        repo = RuleRepository(db)
        rules = repo.get_all() if all_rules else repo.get_active()

        if not rules:
            console.print("[yellow]No rules found.[/yellow] Use 'add' to create some.")
            return

        table = Table(title="Rules")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Threshold", justify="right")
        table.add_column("Symbol")
        table.add_column("Cooldown", justify="right")
        table.add_column("Enabled")
        table.add_column("Last Triggered")

        for r in rules:
            # Format threshold
            rt = RuleType(r.rule_type)
            if rt in (RuleType.PRICE_BELOW_COST_PCT, RuleType.PRICE_ABOVE_COST_PCT):
                threshold_str = f"{r.threshold}%"
            else:
                threshold_str = f"${r.threshold:.2f}"

            enabled_str = "[green]Yes[/green]" if r.enabled else "[red]No[/red]"
            symbol_str = r.symbol if r.symbol else "[dim]All[/dim]"
            triggered_str = (
                r.last_triggered_at.strftime("%Y-%m-%d %H:%M")
                if r.last_triggered_at
                else "[dim]Never[/dim]"
            )

            table.add_row(
                r.name,
                r.rule_type,
                threshold_str,
                symbol_str,
                f"{r.cooldown_minutes}m",
                enabled_str,
                triggered_str,
            )

        console.print(table)
        console.print(f"\n[dim]Total rules: {len(rules)}[/dim]")


@app.command("evaluate")
def evaluate_rules(
    ignore_cooldown: bool = typer.Option(
        False, "--ignore-cooldown", "-i", help="Ignore cooldown periods"
    ),
):
    """Evaluate all rules against current prices."""
    with get_db() as db:
        # Get default user
        user = db.query(User).filter_by(email=settings.default_user_email).first()
        if not user:
            console.print("[yellow]No user found.[/yellow] Add some holdings first.")
            raise typer.Exit(1)

        # Check holdings exist
        holding_repo = HoldingRepository(db)
        holdings = holding_repo.get_all()
        if not holdings:
            console.print("[yellow]No holdings found.[/yellow] Add some holdings first.")
            raise typer.Exit(1)

        # Check rules exist
        rule_repo = RuleRepository(db)
        rules = rule_repo.get_active()
        if not rules:
            console.print("[yellow]No active rules found.[/yellow] Add some rules first.")
            raise typer.Exit(1)

        console.print(f"Evaluating {len(rules)} rules against {len(holdings)} holdings...\n")

        # Create engine and evaluate
        engine = RuleEngine(
            market_provider=market_data,
            cooldown_enabled=not ignore_cooldown,
        )

        results = engine.evaluate_all(db, user.id)

        if not results:
            console.print("[green]No rules triggered.[/green] All conditions are within thresholds.")
            return

        # Display triggered rules
        console.print(f"[bold red]TRIGGERED: {len(results)} rule(s)[/bold red]\n")

        for result in results:
            console.print(f"[bold yellow][TRIGGERED][/bold yellow] {result.rule_name}")
            console.print(f"  Symbol: [cyan]{result.symbol}[/cyan]")
            console.print(f"  {result.reason}")
            if result.cost_basis:
                console.print(f"  Cost basis: ${result.cost_basis:.2f}")
            console.print()


@app.command("remove")
def remove_rule(
    name: str = typer.Argument(..., help="Rule name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a rule."""
    with get_db() as db:
        repo = RuleRepository(db)
        rule = repo.get_by_name(name)

        if not rule:
            console.print(f"[red]Error:[/red] Rule '{name}' not found.")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Remove rule '{name}'?")
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        repo.delete_by_name(name)
        console.print(f"[green]Removed:[/green] {name}")


@app.command("enable")
def enable_rule(
    name: str = typer.Argument(..., help="Rule name to enable"),
):
    """Enable a disabled rule."""
    with get_db() as db:
        repo = RuleRepository(db)
        rule = repo.get_by_name(name)

        if not rule:
            console.print(f"[red]Error:[/red] Rule '{name}' not found.")
            raise typer.Exit(1)

        if rule.enabled:
            console.print(f"[yellow]Rule '{name}' is already enabled.[/yellow]")
            return

        repo.update(rule.id, enabled=True)
        console.print(f"[green]Enabled:[/green] {name}")


@app.command("disable")
def disable_rule(
    name: str = typer.Argument(..., help="Rule name to disable"),
):
    """Disable a rule without removing it."""
    with get_db() as db:
        repo = RuleRepository(db)
        rule = repo.get_by_name(name)

        if not rule:
            console.print(f"[red]Error:[/red] Rule '{name}' not found.")
            raise typer.Exit(1)

        if not rule.enabled:
            console.print(f"[yellow]Rule '{name}' is already disabled.[/yellow]")
            return

        repo.update(rule.id, enabled=False)
        console.print(f"[yellow]Disabled:[/yellow] {name}")


@app.command("types")
def list_types():
    """List available rule types with descriptions."""
    console.print("[bold]Available Rule Types[/bold]\n")

    for rt in RuleType:
        console.print(f"[cyan]{rt.value}[/cyan]")
        console.print(f"  {rt.description()}\n")
