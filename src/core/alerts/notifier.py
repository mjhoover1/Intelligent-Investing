"""Alert notifiers for different channels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from src.db.models import Alert


class BaseNotifier(ABC):
    """Abstract base class for notifiers."""

    @abstractmethod
    def notify(self, alert: Alert, ai_summary: Optional[str] = None) -> bool:
        """Send notification for an alert.

        Args:
            alert: Alert to notify about
            ai_summary: Optional AI-generated context

        Returns:
            True if notification sent successfully
        """
        ...


class ConsoleNotifier(BaseNotifier):
    """Console-based notifier using Rich for formatting."""

    def __init__(self):
        self.console = Console()

    def notify(self, alert: Alert, ai_summary: Optional[str] = None) -> bool:
        """Print alert to console with rich formatting.

        Args:
            alert: Alert to display
            ai_summary: Optional AI-generated context

        Returns:
            True (always succeeds for console)
        """
        # Format timestamp
        timestamp = alert.triggered_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Build alert content
        content = f"[bold cyan]{alert.symbol}[/bold cyan]\n"
        content += f"[dim]{timestamp}[/dim]\n\n"
        content += f"{alert.message}"

        # Add AI summary if available
        summary = ai_summary or alert.ai_summary
        if summary:
            content += f"\n\n[bold]AI Context:[/bold]\n[italic]{summary}[/italic]"

        # Display in a panel
        self.console.print(
            Panel(
                content,
                title="[bold red]ALERT[/bold red]",
                border_style="red",
            )
        )

        return True

    def notify_batch(self, alerts: list[Alert]) -> None:
        """Print multiple alerts.

        Args:
            alerts: List of alerts to display
        """
        if not alerts:
            self.console.print("[green]No alerts to display.[/green]")
            return

        self.console.print(f"\n[bold red]🚨 {len(alerts)} ALERT(S) TRIGGERED[/bold red]\n")

        for alert in alerts:
            self.notify(alert)
            self.console.print()  # Spacing between alerts


# Singleton instance for convenience
console_notifier = ConsoleNotifier()
