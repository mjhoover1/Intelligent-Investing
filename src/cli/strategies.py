"""Strategy presets CLI commands."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config import get_settings
from src.db.database import get_db
from src.db.models import User, Rule
from src.core.strategies import list_presets, get_preset, StrategyPreset
from src.core.rules.repository import RuleRepository
from src.core.rules.models import RuleType

console = Console()
app = typer.Typer(help="Strategy presets - one-click rule bundles")
settings = get_settings()


def _get_default_user(db) -> User:
    """Get or create the default user."""
    user = db.query(User).filter_by(email=settings.default_user_email).first()
    if not user:
        user = User(email=settings.default_user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@app.command("list")
def list_strategies(
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by category (protection/profit/opportunity/balanced)"
    ),
):
    """List all available strategy presets."""
    presets = list_presets()

    if category:
        presets = [p for p in presets if p.category == category.lower()]

    if not presets:
        console.print("[yellow]No strategies found.[/yellow]")
        return

    table = Table(title="Available Strategy Presets")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Category")
    table.add_column("Risk")
    table.add_column("Rules")
    table.add_column("Description", max_width=40)

    for preset in presets:
        risk_style = {
            "conservative": "green",
            "medium": "yellow",
            "aggressive": "red",
        }.get(preset.risk_level, "white")

        table.add_row(
            preset.id,
            preset.name,
            preset.category,
            f"[{risk_style}]{preset.risk_level}[/{risk_style}]",
            str(len(preset.rules)),
            preset.description[:40] + ("..." if len(preset.description) > 40 else ""),
        )

    console.print(table)
    console.print("\n[dim]Use 'invest strategies show <id>' for details[/dim]")
    console.print("[dim]Use 'invest strategies apply <id>' to create rules[/dim]")


@app.command("show")
def show_strategy(
    preset_id: str = typer.Argument(..., help="Strategy preset ID"),
):
    """Show details of a strategy preset."""
    preset = get_preset(preset_id)

    if not preset:
        console.print(f"[red]Error:[/red] Strategy '{preset_id}' not found.")
        console.print("Run 'invest strategies list' to see available strategies.")
        raise typer.Exit(1)

    # Display strategy info
    risk_style = {
        "conservative": "green",
        "medium": "yellow",
        "aggressive": "red",
    }.get(preset.risk_level, "white")

    console.print(Panel(
        f"[bold]{preset.name}[/bold]\n\n"
        f"{preset.description}\n\n"
        f"Category: {preset.category}\n"
        f"Risk Level: [{risk_style}]{preset.risk_level}[/{risk_style}]",
        title=f"[cyan]{preset.id}[/cyan]",
    ))

    # Display rules
    table = Table(title="Rules in this Strategy")
    table.add_column("Rule Name")
    table.add_column("Type")
    table.add_column("Threshold")
    table.add_column("Cooldown")
    table.add_column("Description", max_width=35)

    for rule in preset.rules:
        # Format threshold based on rule type
        if rule.rule_type in (
            RuleType.PRICE_BELOW_COST_PCT,
            RuleType.PRICE_ABOVE_COST_PCT,
        ):
            threshold_str = f"{rule.threshold:+.0f}%"
        elif rule.rule_type in (
            RuleType.RSI_BELOW_VALUE,
            RuleType.RSI_ABOVE_VALUE,
        ):
            threshold_str = f"RSI {rule.threshold:.0f}"
        else:
            threshold_str = f"${rule.threshold:.2f}"

        cooldown_str = f"{rule.cooldown_minutes // 60}h" if rule.cooldown_minutes >= 60 else f"{rule.cooldown_minutes}m"

        table.add_row(
            rule.name.replace(f"[{preset.id}] ", ""),
            rule.rule_type.value,
            threshold_str,
            cooldown_str,
            rule.description[:35] + ("..." if len(rule.description) > 35 else ""),
        )

    console.print(table)

    console.print(f"\n[dim]Apply with: invest strategies apply {preset.id}[/dim]")


@app.command("apply")
def apply_strategy(
    preset_id: str = typer.Argument(..., help="Strategy preset ID to apply"),
    replace: bool = typer.Option(
        False, "--replace", "-r", help="Replace existing rules from this strategy"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be created without creating"
    ),
):
    """Apply a strategy preset, creating all its rules."""
    preset = get_preset(preset_id)

    if not preset:
        console.print(f"[red]Error:[/red] Strategy '{preset_id}' not found.")
        console.print("Run 'invest strategies list' to see available strategies.")
        raise typer.Exit(1)

    with get_db() as db:
        user = _get_default_user(db)
        repo = RuleRepository(db)

        # Check for existing rules from this strategy
        existing = db.query(Rule).filter(
            Rule.user_id == user.id,
            Rule.name.like(f"[{preset.id}]%")
        ).all()

        if existing and not replace and not dry_run:
            console.print(f"[yellow]Found {len(existing)} existing rules from this strategy.[/yellow]")
            console.print("Use --replace to remove them first, or --dry-run to preview.")
            raise typer.Exit(1)

        if replace and existing:
            if dry_run:
                console.print(f"[yellow]Would delete {len(existing)} existing rules[/yellow]")
            else:
                for rule in existing:
                    db.delete(rule)
                db.commit()
                console.print(f"[yellow]Deleted {len(existing)} existing rules[/yellow]")

        # Create rules
        created = []
        for rule_template in preset.rules:
            if dry_run:
                console.print(f"[dim]Would create:[/dim] {rule_template.name}")
            else:
                rule = repo.create(
                    name=rule_template.name,
                    rule_type=rule_template.rule_type,
                    threshold=rule_template.threshold,
                    symbol=rule_template.symbol,
                    enabled=True,
                    cooldown_minutes=rule_template.cooldown_minutes,
                    user_id=user.id,
                )
                created.append(rule)
                console.print(f"[green]Created:[/green] {rule_template.name}")

        if dry_run:
            console.print(f"\n[cyan]Dry run complete. Would create {len(preset.rules)} rules.[/cyan]")
        else:
            console.print(f"\n[green]Successfully applied '{preset.name}' - {len(created)} rules created![/green]")


@app.command("remove")
def remove_strategy(
    preset_id: str = typer.Argument(..., help="Strategy preset ID to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove all rules from a strategy preset."""
    preset = get_preset(preset_id)

    if not preset:
        console.print(f"[red]Error:[/red] Strategy '{preset_id}' not found.")
        raise typer.Exit(1)

    with get_db() as db:
        user = _get_default_user(db)

        # Find existing rules from this strategy
        existing = db.query(Rule).filter(
            Rule.user_id == user.id,
            Rule.name.like(f"[{preset.id}]%")
        ).all()

        if not existing:
            console.print(f"[yellow]No rules found from strategy '{preset.name}'[/yellow]")
            return

        if not force:
            console.print(f"Found {len(existing)} rules from '{preset.name}':")
            for rule in existing:
                console.print(f"  - {rule.name}")

            confirm = typer.confirm("\nDelete these rules?")
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        for rule in existing:
            db.delete(rule)
        db.commit()

        console.print(f"[green]Removed {len(existing)} rules from '{preset.name}'[/green]")


@app.command("active")
def show_active():
    """Show which strategy presets are currently active (have rules applied)."""
    with get_db() as db:
        user = _get_default_user(db)

        # Check each preset
        active_presets = []
        for preset in list_presets():
            count = db.query(Rule).filter(
                Rule.user_id == user.id,
                Rule.name.like(f"[{preset.id}]%"),
                Rule.enabled == True,
            ).count()

            if count > 0:
                total = len(preset.rules)
                active_presets.append((preset, count, total))

        if not active_presets:
            console.print("[yellow]No strategy presets currently active.[/yellow]")
            console.print("\nApply one with: invest strategies apply <preset-id>")
            return

        table = Table(title="Active Strategy Presets")
        table.add_column("Strategy")
        table.add_column("Active Rules")
        table.add_column("Coverage")

        for preset, active, total in active_presets:
            pct = active / total * 100
            style = "green" if pct == 100 else "yellow"
            table.add_row(
                preset.name,
                f"{active}/{total}",
                f"[{style}]{pct:.0f}%[/{style}]",
            )

        console.print(table)
