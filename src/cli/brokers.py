"""Broker integration CLI commands."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.db.database import get_db
from src.db.models import LinkedBrokerAccount, User
from src.core.brokers import BrokerSyncService, plaid_provider
from src.config import get_settings

settings = get_settings()
console = Console()
app = typer.Typer()


@app.command("status")
def broker_status():
    """Show broker integration status."""
    console.print("[bold]Broker Integration Status[/bold]\n")

    # Check Plaid configuration
    if plaid_provider.is_configured():
        console.print(f"[green]Plaid:[/green] Configured (env={settings.plaid_env})")
    else:
        console.print("[yellow]Plaid:[/yellow] Not configured")
        console.print("  Set PLAID_CLIENT_ID and PLAID_SECRET in .env")
        console.print("  Sign up at https://dashboard.plaid.com/")

    console.print()

    # Show linked accounts
    with get_db() as db:
        user = db.query(User).filter_by(email=settings.default_user_email).first()
        if not user:
            console.print("[dim]No user found[/dim]")
            return

        accounts = (
            db.query(LinkedBrokerAccount)
            .filter(LinkedBrokerAccount.user_id == user.id)
            .all()
        )

        if not accounts:
            console.print("[dim]No linked broker accounts[/dim]")
            return

        table = Table(title="Linked Accounts")
        table.add_column("ID", style="dim")
        table.add_column("Broker")
        table.add_column("Account")
        table.add_column("Sync", justify="center")
        table.add_column("Last Synced")
        table.add_column("Status")

        for acc in accounts:
            status = "[green]Active[/green]"
            if acc.needs_reauth:
                status = "[red]Needs Reauth[/red]"
            elif not acc.is_active:
                status = "[dim]Inactive[/dim]"

            table.add_row(
                acc.id[:8] + "...",
                acc.broker_type,
                f"{acc.broker_name or 'Unknown'} (...{acc.account_mask or ''})",
                "[green]Yes[/green]" if acc.sync_enabled else "[red]No[/red]",
                acc.last_synced_at.strftime("%Y-%m-%d %H:%M") if acc.last_synced_at else "Never",
                status,
            )

        console.print(table)


@app.command("list")
def list_accounts(
    user: Optional[str] = typer.Option(
        None,
        "--user",
        "-u",
        help="User email (default: default user)",
    ),
):
    """List linked broker accounts."""
    with get_db() as db:
        if user:
            user_obj = db.query(User).filter_by(email=user).first()
        else:
            user_obj = db.query(User).filter_by(email=settings.default_user_email).first()

        if not user_obj:
            console.print(f"[red]Error: User not found[/red]")
            raise typer.Exit(1)

        sync_service = BrokerSyncService(db)
        accounts = sync_service.get_linked_accounts(user_obj)

        if not accounts:
            console.print("[yellow]No linked broker accounts.[/yellow]")
            console.print("\nTo link a broker account:")
            console.print("  1. Configure Plaid (PLAID_CLIENT_ID, PLAID_SECRET)")
            console.print("  2. Use the web dashboard or API to initiate linking")
            return

        table = Table(title="Linked Broker Accounts")
        table.add_column("ID", style="dim")
        table.add_column("Broker")
        table.add_column("Name")
        table.add_column("Account")
        table.add_column("Sync Mode")
        table.add_column("Last Synced")
        table.add_column("Error")

        for acc in accounts:
            table.add_row(
                acc.id[:8] + "...",
                acc.broker_type,
                acc.broker_name or "-",
                f"...{acc.account_mask}" if acc.account_mask else "-",
                acc.sync_mode,
                acc.last_synced_at.strftime("%Y-%m-%d %H:%M") if acc.last_synced_at else "Never",
                (acc.last_sync_error[:30] + "...") if acc.last_sync_error else "-",
            )

        console.print(table)


@app.command("sync")
def sync_accounts(
    account_id: Optional[str] = typer.Option(
        None,
        "--account",
        "-a",
        help="Specific account ID to sync (default: all)",
    ),
    user: Optional[str] = typer.Option(
        None,
        "--user",
        "-u",
        help="User email (default: default user)",
    ),
):
    """Sync positions from linked broker accounts."""
    with get_db() as db:
        if user:
            user_obj = db.query(User).filter_by(email=user).first()
        else:
            user_obj = db.query(User).filter_by(email=settings.default_user_email).first()

        if not user_obj:
            console.print(f"[red]Error: User not found[/red]")
            raise typer.Exit(1)

        sync_service = BrokerSyncService(db)

        if account_id:
            # Sync specific account
            account = (
                db.query(LinkedBrokerAccount)
                .filter(
                    LinkedBrokerAccount.id.like(f"{account_id}%"),
                    LinkedBrokerAccount.user_id == user_obj.id,
                )
                .first()
            )

            if not account:
                console.print(f"[red]Error: Account {account_id} not found[/red]")
                raise typer.Exit(1)

            console.print(f"Syncing account: {account.broker_name}...")
            result = sync_service.sync_account(account)

            if result.success:
                console.print(f"[green]Sync complete![/green]")
                console.print(f"  Fetched: {result.positions_fetched}")
                console.print(f"  Created: {result.created}")
                console.print(f"  Updated: {result.updated}")
                console.print(f"  Skipped: {result.skipped}")
            else:
                console.print(f"[red]Sync failed:[/red]")
                for err in result.errors:
                    console.print(f"  - {err}")

        else:
            # Sync all accounts
            accounts = sync_service.get_linked_accounts(user_obj)

            if not accounts:
                console.print("[yellow]No linked accounts to sync.[/yellow]")
                return

            console.print(f"Syncing {len(accounts)} account(s)...\n")

            for account in accounts:
                console.print(f"[bold]{account.broker_name}[/bold]")
                result = sync_service.sync_account(account)

                if result.success:
                    console.print(f"  [green]OK[/green] - {result.created} created, {result.updated} updated")
                else:
                    console.print(f"  [red]Failed[/red] - {result.errors[0] if result.errors else 'Unknown error'}")

            console.print("\n[green]Sync complete![/green]")


@app.command("unlink")
def unlink_account(
    account_id: str = typer.Argument(..., help="Account ID to unlink"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Unlink a broker account."""
    with get_db() as db:
        account = (
            db.query(LinkedBrokerAccount)
            .filter(LinkedBrokerAccount.id.like(f"{account_id}%"))
            .first()
        )

        if not account:
            console.print(f"[red]Error: Account {account_id} not found[/red]")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(
                f"Unlink {account.broker_name} (...{account.account_mask})?"
            )
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        sync_service = BrokerSyncService(db)
        sync_service.unlink_account(account)

        console.print(f"[green]Account unlinked.[/green]")


@app.command("enable-sync")
def enable_sync(
    account_id: str = typer.Argument(..., help="Account ID"),
    mode: str = typer.Option("upsert", "--mode", "-m", help="Sync mode: upsert or replace"),
):
    """Enable syncing for an account."""
    # Validate sync mode
    valid_modes = ("upsert", "replace")
    if mode not in valid_modes:
        console.print(f"[red]Error:[/red] Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}")
        raise typer.Exit(1)

    with get_db() as db:
        account = (
            db.query(LinkedBrokerAccount)
            .filter(LinkedBrokerAccount.id.like(f"{account_id}%"))
            .first()
        )

        if not account:
            console.print(f"[red]Error: Account {account_id} not found[/red]")
            raise typer.Exit(1)

        account.sync_enabled = True
        account.sync_mode = mode

        console.print(f"[green]Sync enabled for {account.broker_name} (mode={mode})[/green]")


@app.command("disable-sync")
def disable_sync(
    account_id: str = typer.Argument(..., help="Account ID"),
):
    """Disable syncing for an account."""
    with get_db() as db:
        account = (
            db.query(LinkedBrokerAccount)
            .filter(LinkedBrokerAccount.id.like(f"{account_id}%"))
            .first()
        )

        if not account:
            console.print(f"[red]Error: Account {account_id} not found[/red]")
            raise typer.Exit(1)

        account.sync_enabled = False

        console.print(f"[yellow]Sync disabled for {account.broker_name}[/yellow]")
