"""User management CLI commands."""

import typer
from rich.console import Console
from rich.table import Table

from src.db.database import get_db
from src.db.models import User, UserApiKey
from src.core.auth import AuthService, get_password_hash

app = typer.Typer()
console = Console()


@app.command("register")
def register(
    email: str = typer.Argument(..., help="User email address"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="User password"),
    admin: bool = typer.Option(False, "--admin", help="Create as admin user"),
):
    """Register a new user."""
    with get_db() as db:
        auth = AuthService(db)

        # Check if email exists
        existing = auth.get_user_by_email(email)
        if existing:
            console.print(f"[red]Error: Email '{email}' is already registered[/red]")
            raise typer.Exit(1)

        try:
            user, token = auth.register(email=email, password=password, is_admin=admin)
            console.print(f"[green]User registered successfully![/green]")
            console.print(f"  Email: {user.email}")
            console.print(f"  ID: {user.id}")
            console.print(f"  Admin: {user.is_admin}")
            console.print(f"\n[yellow]Access Token (for API):[/yellow]")
            console.print(f"  {token}")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@app.command("list")
def list_users():
    """List all users."""
    with get_db() as db:
        users = db.query(User).all()

        if not users:
            console.print("[yellow]No users found.[/yellow]")
            return

        table = Table(title="Users")
        table.add_column("ID", style="dim")
        table.add_column("Email")
        table.add_column("Active", justify="center")
        table.add_column("Admin", justify="center")
        table.add_column("Created")
        table.add_column("Last Login")

        for user in users:
            table.add_row(
                user.id[:8] + "...",
                user.email,
                "[green]Yes[/green]" if user.is_active else "[red]No[/red]",
                "[yellow]Yes[/yellow]" if user.is_admin else "No",
                user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "-",
                user.last_login_at.strftime("%Y-%m-%d %H:%M") if user.last_login_at else "Never",
            )

        console.print(table)


@app.command("set-password")
def set_password(
    email: str = typer.Argument(..., help="User email address"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, confirmation_prompt=True, help="New password"),
):
    """Set or reset a user's password (admin function)."""
    with get_db() as db:
        auth = AuthService(db)
        user = auth.get_user_by_email(email)

        if not user:
            console.print(f"[red]Error: User '{email}' not found[/red]")
            raise typer.Exit(1)

        auth.set_password(user, password)
        console.print(f"[green]Password updated for {email}[/green]")


@app.command("deactivate")
def deactivate(
    email: str = typer.Argument(..., help="User email address"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Deactivate a user account."""
    with get_db() as db:
        user = db.query(User).filter_by(email=email).first()

        if not user:
            console.print(f"[red]Error: User '{email}' not found[/red]")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Deactivate user '{email}'? They will no longer be able to log in.")
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        user.is_active = False
        db.commit()
        console.print(f"[green]User {email} deactivated[/green]")


@app.command("activate")
def activate(
    email: str = typer.Argument(..., help="User email address"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Activate a user account."""
    with get_db() as db:
        user = db.query(User).filter_by(email=email).first()

        if not user:
            console.print(f"[red]Error: User '{email}' not found[/red]")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Activate user '{email}'?")
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        user.is_active = True
        db.commit()
        console.print(f"[green]User {email} activated[/green]")


@app.command("make-admin")
def make_admin(
    email: str = typer.Argument(..., help="User email address"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Grant admin privileges to a user."""
    with get_db() as db:
        user = db.query(User).filter_by(email=email).first()

        if not user:
            console.print(f"[red]Error: User '{email}' not found[/red]")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Grant admin privileges to '{email}'? Admins have full system access.")
            if not confirm:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        user.is_admin = True
        db.commit()
        console.print(f"[green]User {email} is now an admin[/green]")


@app.command("create-api-key")
def create_api_key(
    email: str = typer.Argument(..., help="User email address"),
    name: str = typer.Option("CLI Key", "--name", "-n", help="Friendly name for the key"),
):
    """Create an API key for a user."""
    with get_db() as db:
        auth = AuthService(db)
        user = auth.get_user_by_email(email)

        if not user:
            console.print(f"[red]Error: User '{email}' not found[/red]")
            raise typer.Exit(1)

        api_key_record, plain_key = auth.create_api_key(user, name)

        console.print(f"[green]API key created![/green]")
        console.print(f"  Name: {name}")
        console.print(f"  Key ID: {api_key_record.id}")
        console.print(f"\n[bold yellow]API Key (save this - shown only once!):[/bold yellow]")
        console.print(f"  {plain_key}")


@app.command("list-api-keys")
def list_api_keys(
    email: str = typer.Argument(..., help="User email address"),
):
    """List API keys for a user."""
    with get_db() as db:
        auth = AuthService(db)
        user = auth.get_user_by_email(email)

        if not user:
            console.print(f"[red]Error: User '{email}' not found[/red]")
            raise typer.Exit(1)

        keys = auth.list_api_keys(user)

        if not keys:
            console.print(f"[yellow]No API keys for {email}[/yellow]")
            return

        table = Table(title=f"API Keys for {email}")
        table.add_column("ID", style="dim")
        table.add_column("Name")
        table.add_column("Active", justify="center")
        table.add_column("Created")
        table.add_column("Last Used")
        table.add_column("Expires")

        for key in keys:
            table.add_row(
                key.id[:8] + "...",
                key.name,
                "[green]Yes[/green]" if key.is_active else "[red]No[/red]",
                key.created_at.strftime("%Y-%m-%d %H:%M"),
                key.last_used_at.strftime("%Y-%m-%d %H:%M") if key.last_used_at else "Never",
                key.expires_at.strftime("%Y-%m-%d") if key.expires_at else "Never",
            )

        console.print(table)


@app.command("revoke-api-key")
def revoke_api_key(
    email: str = typer.Argument(..., help="User email address"),
    key_id: str = typer.Argument(..., help="API key ID"),
):
    """Revoke an API key."""
    with get_db() as db:
        auth = AuthService(db)
        user = auth.get_user_by_email(email)

        if not user:
            console.print(f"[red]Error: User '{email}' not found[/red]")
            raise typer.Exit(1)

        # Try to find by partial ID
        key = db.query(UserApiKey).filter(
            UserApiKey.user_id == user.id,
            UserApiKey.id.like(f"{key_id}%")
        ).first()

        if not key:
            console.print(f"[red]Error: API key '{key_id}' not found[/red]")
            raise typer.Exit(1)

        if auth.revoke_api_key(user, key.id):
            console.print(f"[green]API key revoked[/green]")
        else:
            console.print(f"[red]Error: Failed to revoke key[/red]")
            raise typer.Exit(1)


@app.command("login")
def login(
    email: str = typer.Argument(..., help="User email address"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="User password"),
):
    """Login and get an access token."""
    with get_db() as db:
        auth = AuthService(db)

        try:
            user, token = auth.login(email=email, password=password)
            console.print(f"[green]Login successful![/green]")
            console.print(f"  Email: {user.email}")
            console.print(f"\n[yellow]Access Token:[/yellow]")
            console.print(f"  {token}")
            console.print(f"\n[dim]Use this token in Authorization header: Bearer <token>[/dim]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
