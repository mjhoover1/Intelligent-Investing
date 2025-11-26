"""Portfolio CLI commands."""

from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.db.database import get_db
from src.db.models import User
from src.core.portfolio.repository import HoldingRepository
from src.core.portfolio.importers import import_schwab_csv, parse_schwab_csv
from src.data.market.provider import market_data
from src.config import get_settings

settings = get_settings()

console = Console()
app = typer.Typer()


@app.command("add")
def add_holding(
    symbol: str = typer.Argument(..., help="Stock ticker symbol (e.g., AAPL)"),
    shares: float = typer.Argument(..., help="Number of shares"),
    cost_basis: float = typer.Argument(..., help="Cost basis per share"),
    purchase_date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Purchase date (YYYY-MM-DD)"
    ),
):
    """Add a new holding to the portfolio."""
    with get_db() as db:
        repo = HoldingRepository(db)

        # Check if symbol already exists
        existing = repo.get_by_symbol(symbol)
        if existing:
            console.print(
                f"[yellow]Warning:[/yellow] {symbol.upper()} already exists. "
                f"Use 'update' to modify it."
            )
            raise typer.Exit(1)

        # Parse purchase date if provided
        parsed_date = None
        if purchase_date:
            try:
                parsed_date = date.fromisoformat(purchase_date)
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid date format: {purchase_date}")
                raise typer.Exit(1)

        holding = repo.create(
            symbol=symbol,
            shares=shares,
            cost_basis=cost_basis,
            purchase_date=parsed_date,
        )

        total_cost = shares * cost_basis
        console.print(
            f"[green]Added:[/green] {holding.symbol} - "
            f"{shares} shares @ ${cost_basis:.2f} = ${total_cost:,.2f}"
        )


@app.command("list")
def list_holdings():
    """List all holdings in the portfolio."""
    with get_db() as db:
        repo = HoldingRepository(db)
        holdings = repo.get_all()

        if not holdings:
            console.print("[yellow]No holdings found.[/yellow] Use 'add' to add some.")
            return

        table = Table(title="Portfolio Holdings")
        table.add_column("Symbol", style="cyan")
        table.add_column("Shares", justify="right")
        table.add_column("Cost Basis", justify="right", style="green")
        table.add_column("Total Cost", justify="right")
        table.add_column("Purchase Date")

        for h in holdings:
            total_cost = h.shares * h.cost_basis
            table.add_row(
                h.symbol,
                f"{h.shares:,.2f}",
                f"${h.cost_basis:,.2f}",
                f"${total_cost:,.2f}",
                str(h.purchase_date) if h.purchase_date else "-",
            )

        console.print(table)
        console.print(f"\n[dim]Total holdings: {len(holdings)}[/dim]")


@app.command("price")
def get_price(
    symbol: str = typer.Argument(..., help="Stock ticker symbol"),
):
    """Get current price for a symbol."""
    with get_db() as db:
        price = market_data.get_price(symbol, db)

        if price is None:
            console.print(f"[red]Error:[/red] Could not fetch price for {symbol.upper()}")
            raise typer.Exit(1)

        console.print(f"[cyan]{symbol.upper()}[/cyan]: [green]${price:,.2f}[/green]")


@app.command("value")
def portfolio_value():
    """Show portfolio value with current prices and P&L."""
    with get_db() as db:
        repo = HoldingRepository(db)
        holdings = repo.get_all()

        if not holdings:
            console.print("[yellow]No holdings found.[/yellow] Use 'add' to add some.")
            return

        # Fetch all prices
        symbols = [h.symbol for h in holdings]
        prices = market_data.get_prices(symbols, db)

        table = Table(title="Portfolio Value")
        table.add_column("Symbol", style="cyan")
        table.add_column("Shares", justify="right")
        table.add_column("Cost Basis", justify="right")
        table.add_column("Current Price", justify="right")
        table.add_column("Current Value", justify="right")
        table.add_column("P&L", justify="right")
        table.add_column("P&L %", justify="right")

        total_cost = 0.0
        total_value = 0.0

        for h in holdings:
            cost = h.shares * h.cost_basis
            total_cost += cost

            current_price = prices.get(h.symbol)
            if current_price is None:
                table.add_row(
                    h.symbol,
                    f"{h.shares:,.2f}",
                    f"${h.cost_basis:,.2f}",
                    "[red]N/A[/red]",
                    "[red]N/A[/red]",
                    "-",
                    "-",
                )
                continue

            value = h.shares * current_price
            total_value += value
            pnl = value - cost
            pnl_pct = (pnl / cost) * 100 if cost > 0 else 0

            pnl_color = "green" if pnl >= 0 else "red"
            table.add_row(
                h.symbol,
                f"{h.shares:,.2f}",
                f"${h.cost_basis:,.2f}",
                f"${current_price:,.2f}",
                f"${value:,.2f}",
                f"[{pnl_color}]${pnl:+,.2f}[/{pnl_color}]",
                f"[{pnl_color}]{pnl_pct:+.2f}%[/{pnl_color}]",
            )

        console.print(table)

        # Summary
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
        pnl_color = "green" if total_pnl >= 0 else "red"

        console.print()
        console.print(f"[bold]Total Cost:[/bold]    ${total_cost:,.2f}")
        console.print(f"[bold]Total Value:[/bold]   ${total_value:,.2f}")
        console.print(
            f"[bold]Total P&L:[/bold]     [{pnl_color}]${total_pnl:+,.2f} "
            f"({total_pnl_pct:+.2f}%)[/{pnl_color}]"
        )


@app.command("remove")
def remove_holding(
    symbol: str = typer.Argument(..., help="Stock ticker symbol to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a holding from the portfolio."""
    symbol = symbol.upper()

    with get_db() as db:
        repo = HoldingRepository(db)
        holding = repo.get_by_symbol(symbol)

        if not holding:
            console.print(f"[red]Error:[/red] Holding {symbol} not found.")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(
                f"Remove {symbol} ({holding.shares} shares @ ${holding.cost_basis:.2f})?"
            )
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        repo.delete_by_symbol(symbol)
        console.print(f"[green]Removed:[/green] {symbol}")


@app.command("update")
def update_holding(
    symbol: str = typer.Argument(..., help="Stock ticker symbol"),
    shares: Optional[float] = typer.Option(None, "--shares", "-s", help="New shares amount"),
    cost_basis: Optional[float] = typer.Option(
        None, "--cost", "-c", help="New cost basis per share"
    ),
):
    """Update an existing holding."""
    if shares is None and cost_basis is None:
        console.print("[red]Error:[/red] Provide --shares and/or --cost to update.")
        raise typer.Exit(1)

    symbol = symbol.upper()

    with get_db() as db:
        repo = HoldingRepository(db)
        holding = repo.get_by_symbol(symbol)

        if not holding:
            console.print(f"[red]Error:[/red] Holding {symbol} not found.")
            raise typer.Exit(1)

        repo.update(
            holding_id=holding.id,
            shares=shares,
            cost_basis=cost_basis,
        )

        # Refresh to show updated values
        holding = repo.get_by_symbol(symbol)
        total_cost = holding.shares * holding.cost_basis
        console.print(
            f"[green]Updated:[/green] {holding.symbol} - "
            f"{holding.shares} shares @ ${holding.cost_basis:.2f} = ${total_cost:,.2f}"
        )


@app.command("import-schwab")
def import_schwab(
    file_path: Path = typer.Argument(..., help="Path to Schwab positions CSV file"),
    mode: str = typer.Option(
        "upsert",
        "--mode",
        "-m",
        help="Import mode: upsert (update existing), replace (delete all first), add_only (skip existing)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Parse and show what would be imported without making changes",
    ),
    user: Optional[str] = typer.Option(
        None,
        "--user",
        "-u",
        help="User email to import for (default: default user)",
    ),
):
    """Import positions from a Schwab CSV export.

    Export your positions from Schwab:
    1. Log into schwab.com
    2. Go to Accounts > Positions
    3. Click "Export" button
    4. Save the CSV file

    Examples:
        invest portfolio import-schwab positions.csv
        invest portfolio import-schwab positions.csv --dry-run
        invest portfolio import-schwab positions.csv --mode replace
        invest portfolio import-schwab positions.csv --user user@example.com
    """
    # Validate file
    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(1)

    # Read CSV content
    try:
        csv_content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading file:[/red] {e}")
        raise typer.Exit(1)

    # Parse to preview
    positions, parse_errors = parse_schwab_csv(csv_content)

    if parse_errors:
        console.print("[red]Parse errors:[/red]")
        for err in parse_errors:
            console.print(f"  - {err}")
        raise typer.Exit(1)

    if not positions:
        console.print("[yellow]No positions found in CSV.[/yellow]")
        raise typer.Exit(0)

    # Show preview table
    table = Table(title="Positions to Import")
    table.add_column("Symbol", style="cyan")
    table.add_column("Shares", justify="right")
    table.add_column("Cost/Share", justify="right", style="green")
    table.add_column("Total Cost", justify="right")
    table.add_column("Description")

    for pos in positions:
        table.add_row(
            pos.symbol,
            f"{pos.shares:,.2f}",
            f"${pos.cost_basis_per_share:,.2f}",
            f"${pos.total_cost:,.2f}",
            (pos.description[:30] + "...") if pos.description and len(pos.description) > 30 else (pos.description or "-"),
        )

    console.print(table)
    console.print(f"\n[dim]Total positions: {len(positions)}[/dim]")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made.[/yellow]")
        return

    # Confirm import
    if mode == "replace":
        console.print(f"\n[yellow]Warning:[/yellow] Mode 'replace' will DELETE all existing positions first.")

    if not typer.confirm(f"\nImport {len(positions)} positions (mode={mode})?"):
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    # Do the import
    with get_db() as db:
        # Get user ID
        if user:
            user_obj = db.query(User).filter_by(email=user).first()
            if not user_obj:
                console.print(f"[red]Error:[/red] User '{user}' not found")
                raise typer.Exit(1)
            user_id = user_obj.id
        else:
            # Use default user
            user_obj = db.query(User).filter_by(email=settings.default_user_email).first()
            if not user_obj:
                user_obj = User(email=settings.default_user_email, is_active=True)
                db.add(user_obj)
                db.flush()
            user_id = user_obj.id

        result = import_schwab_csv(db, user_id, csv_content, mode)
        db.commit()

    # Show results
    console.print()
    if result.errors:
        console.print("[red]Errors during import:[/red]")
        for err in result.errors:
            console.print(f"  - {err}")

    console.print(f"[green]Import complete![/green]")
    console.print(f"  Created: {result.created}")
    console.print(f"  Updated: {result.updated}")
    console.print(f"  Skipped: {result.skipped}")


@app.command("export")
def export_positions(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: stdout)",
    ),
):
    """Export positions to CSV format."""
    with get_db() as db:
        repo = HoldingRepository(db)
        holdings = repo.get_all()

        if not holdings:
            console.print("[yellow]No holdings to export.[/yellow]")
            return

        # Build CSV content
        lines = ["symbol,shares,cost_basis,purchase_date"]
        for h in holdings:
            date_str = str(h.purchase_date) if h.purchase_date else ""
            lines.append(f"{h.symbol},{h.shares},{h.cost_basis},{date_str}")

        csv_content = "\n".join(lines)

        if output:
            output.write_text(csv_content)
            console.print(f"[green]Exported {len(holdings)} positions to {output}[/green]")
        else:
            console.print(csv_content)
