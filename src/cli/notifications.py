"""CLI commands for notification settings."""

import typer
from rich.console import Console
from rich.table import Table

from src.config import get_settings
from src.db.database import get_db
from src.db.models import NotificationSettings, User
from src.core.alerts.notifier import TelegramNotifier

console = Console()
app = typer.Typer(help="Manage notification settings")
settings = get_settings()


def _get_or_create_settings(db, user_id: str) -> NotificationSettings:
    """Get or create notification settings for a user."""
    ns = db.query(NotificationSettings).filter_by(user_id=user_id).first()
    if not ns:
        ns = NotificationSettings(user_id=user_id)
        db.add(ns)
        db.flush()  # Make visible in session, commit handled by context manager
    return ns


def _get_default_user(db) -> User:
    """Get or create the default user."""
    user = db.query(User).filter_by(email=settings.default_user_email).first()
    if not user:
        user = User(email=settings.default_user_email)
        db.add(user)
        db.flush()  # Make visible in session, commit handled by context manager
    return user


@app.command("status")
def show_status():
    """Show current notification settings."""
    with get_db() as db:
        user = _get_default_user(db)
        ns = _get_or_create_settings(db, user.id)

        table = Table(title="Notification Settings")
        table.add_column("Channel", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")

        # Console
        table.add_row(
            "Console",
            "[green]Enabled[/green]" if ns.console_enabled else "[red]Disabled[/red]",
            "Always prints to terminal",
        )

        # Telegram
        telegram_status = "[green]Enabled[/green]" if ns.telegram_enabled else "[red]Disabled[/red]"
        telegram_details = ""
        if ns.telegram_chat_id:
            telegram_details = f"Chat ID: {ns.telegram_chat_id}"
        elif settings.telegram_chat_id:
            telegram_details = f"Chat ID: {settings.telegram_chat_id} (from .env)"
        else:
            telegram_details = "[yellow]No chat ID configured[/yellow]"

        table.add_row("Telegram", telegram_status, telegram_details)

        console.print(table)

        # Check if bot token is configured
        if not settings.telegram_bot_token:
            console.print("\n[yellow]Note:[/yellow] TELEGRAM_BOT_TOKEN not set in .env")
            console.print("Get one from @BotFather on Telegram")


@app.command("telegram-setup")
def telegram_setup(
    chat_id: str = typer.Option(None, "--chat-id", "-c", help="Your Telegram chat ID"),
):
    """Set up Telegram notifications.

    To get your chat_id:
    1. Create a bot with @BotFather and get the token
    2. Add TELEGRAM_BOT_TOKEN to your .env file
    3. Send any message to your bot
    4. Run: invest notifications telegram-get-chat-id
    """
    if not settings.telegram_bot_token:
        console.print("[red]Error:[/red] TELEGRAM_BOT_TOKEN not set in .env")
        console.print("\nTo set up Telegram:")
        console.print("1. Message @BotFather on Telegram")
        console.print("2. Send /newbot and follow the prompts")
        console.print("3. Copy the token and add to .env:")
        console.print("   TELEGRAM_BOT_TOKEN=your_token_here")
        raise typer.Exit(1)

    with get_db() as db:
        user = _get_default_user(db)
        ns = _get_or_create_settings(db, user.id)

        if chat_id:
            ns.telegram_chat_id = chat_id
            ns.telegram_enabled = True
            db.commit()
            console.print(f"[green]Telegram configured with chat ID: {chat_id}[/green]")
        elif settings.telegram_chat_id:
            ns.telegram_enabled = True
            db.commit()
            console.print(f"[green]Telegram enabled using chat ID from .env[/green]")
        else:
            console.print("[yellow]No chat ID provided.[/yellow]")
            console.print("\nTo get your chat ID:")
            console.print("1. Send any message to your bot")
            console.print("2. Run: invest notifications telegram-get-chat-id")
            raise typer.Exit(1)

        # Test the connection
        console.print("\nTesting Telegram connection...")
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=chat_id or settings.telegram_chat_id,
        )
        if notifier.send_test_message():
            console.print("[green]Test message sent successfully![/green]")
        else:
            console.print("[red]Failed to send test message. Check your token and chat ID.[/red]")


@app.command("telegram-get-chat-id")
def telegram_get_chat_id():
    """Fetch your chat ID from Telegram (after sending a message to your bot)."""
    import requests

    if not settings.telegram_bot_token:
        console.print("[red]Error:[/red] TELEGRAM_BOT_TOKEN not set in .env")
        raise typer.Exit(1)

    console.print("Fetching updates from Telegram bot...")

    try:
        response = requests.get(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates",
            timeout=10,
        )

        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            raise typer.Exit(1)

        try:
            data = response.json()
        except ValueError as e:
            console.print(f"[red]Error parsing response:[/red] {e}")
            raise typer.Exit(1)

        if not data.get("ok"):
            console.print(f"[red]Error:[/red] {data}")
            raise typer.Exit(1)

        updates = data.get("result", [])
        if not updates:
            console.print("[yellow]No messages found.[/yellow]")
            console.print("Please send a message to your bot first, then run this command again.")
            raise typer.Exit(1)

        # Get the most recent chat
        chat_ids = set()
        for update in updates:
            message = update.get("message", {})
            chat = message.get("chat", {})
            if chat.get("id"):
                chat_ids.add(chat["id"])
                chat_type = chat.get("type", "unknown")
                chat_name = chat.get("first_name") or chat.get("title") or "Unknown"
                console.print(f"\nFound chat: [cyan]{chat_name}[/cyan] (type: {chat_type})")
                console.print(f"Chat ID: [bold green]{chat['id']}[/bold green]")

        if chat_ids:
            console.print("\n[bold]Next steps:[/bold]")
            chat_id = list(chat_ids)[0]
            console.print(f"Run: invest notifications telegram-setup --chat-id {chat_id}")
            console.print("\nOr add to .env:")
            console.print(f"TELEGRAM_CHAT_ID={chat_id}")

    except requests.RequestException as e:
        console.print(f"[red]Request failed:[/red] {e}")
        raise typer.Exit(1)


@app.command("telegram-enable")
def telegram_enable():
    """Enable Telegram notifications."""
    with get_db() as db:
        user = _get_default_user(db)
        ns = _get_or_create_settings(db, user.id)

        chat_id = ns.telegram_chat_id or settings.telegram_chat_id
        if not chat_id:
            console.print("[red]Error:[/red] No chat ID configured")
            console.print("Run: invest notifications telegram-setup --chat-id YOUR_CHAT_ID")
            raise typer.Exit(1)

        ns.telegram_enabled = True
        db.commit()
        console.print("[green]Telegram notifications enabled[/green]")


@app.command("telegram-disable")
def telegram_disable():
    """Disable Telegram notifications."""
    with get_db() as db:
        user = _get_default_user(db)
        ns = _get_or_create_settings(db, user.id)

        ns.telegram_enabled = False
        db.commit()
        console.print("[yellow]Telegram notifications disabled[/yellow]")


@app.command("test")
def test_notification(
    telegram: bool = typer.Option(False, "--telegram", "-t", help="Test Telegram notification"),
):
    """Send a test notification."""
    from src.core.alerts.service import AlertService
    from src.core.alerts.notifier import console_notifier, TelegramNotifier, MultiNotifier

    with get_db() as db:
        user = _get_default_user(db)
        ns = _get_or_create_settings(db, user.id)

        notifiers = []

        # Console is always included for test
        notifiers.append(console_notifier)

        # Add Telegram if requested
        if telegram:
            chat_id = ns.telegram_chat_id or settings.telegram_chat_id
            if not settings.telegram_bot_token:
                console.print("[red]Error:[/red] TELEGRAM_BOT_TOKEN not set")
                raise typer.Exit(1)
            if not chat_id:
                console.print("[red]Error:[/red] No Telegram chat ID configured")
                raise typer.Exit(1)

            notifiers.append(TelegramNotifier(settings.telegram_bot_token, chat_id))
            console.print("Including Telegram in test...")

        multi = MultiNotifier(notifiers)
        service = AlertService(db=db, notifier=multi)

        alert = service.create_test_alert(
            user_id=user.id,
            symbol="TEST",
            message="This is a test alert from Signal Sentinel",
            notify=True,
        )

        console.print(f"\n[green]Test alert created: {alert.id}[/green]")
