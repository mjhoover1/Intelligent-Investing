"""Alert notifiers for different channels."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import requests
from rich.console import Console
from rich.panel import Panel

from src.db.models import Alert

logger = logging.getLogger(__name__)


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


class TelegramNotifier(BaseNotifier):
    """Telegram-based notifier using Bot API."""

    TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id

    def notify(self, alert: Alert, ai_summary: Optional[str] = None) -> bool:
        """Send alert via Telegram.

        Args:
            alert: Alert to send
            ai_summary: Optional AI-generated context

        Returns:
            True if message sent successfully
        """
        message = self._format_message(alert, ai_summary)

        try:
            response = requests.post(
                self.TELEGRAM_API_URL.format(token=self.bot_token),
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )

            if response.status_code == 200:
                logger.debug(f"Telegram notification sent for {alert.symbol}")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False

        except requests.RequestException as e:
            logger.error(f"Telegram request failed: {e}")
            return False

    def _format_message(self, alert: Alert, ai_summary: Optional[str] = None) -> str:
        """Format alert as Telegram message.

        Args:
            alert: Alert to format
            ai_summary: Optional AI summary

        Returns:
            Formatted message string
        """
        summary = ai_summary or alert.ai_summary

        lines = [
            f"<b>[ALERT] {alert.symbol}</b>",
            "",
            alert.message,
        ]

        if summary:
            # Truncate long summaries
            if len(summary) > 200:
                summary = summary[:197] + "..."
            lines.extend(["", f"<i>AI: {summary}</i>"])

        return "\n".join(lines)

    def notify_batch(self, alerts: list[Alert]) -> None:
        """Send multiple alerts (each as separate message).

        Args:
            alerts: List of alerts to send
        """
        for alert in alerts:
            self.notify(alert)

    def send_test_message(self) -> bool:
        """Send a test message to verify configuration.

        Returns:
            True if test message sent successfully
        """
        try:
            response = requests.post(
                self.TELEGRAM_API_URL.format(token=self.bot_token),
                json={
                    "chat_id": self.chat_id,
                    "text": "Intelligent Investing bot connected successfully!",
                },
                timeout=10,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False


class MultiNotifier(BaseNotifier):
    """Notifier that sends to multiple channels."""

    def __init__(self, notifiers: list[BaseNotifier]):
        """Initialize with multiple notifiers.

        Args:
            notifiers: List of notifiers to use
        """
        self.notifiers = notifiers

    def notify(self, alert: Alert, ai_summary: Optional[str] = None) -> bool:
        """Send alert to all configured notifiers.

        Args:
            alert: Alert to send
            ai_summary: Optional AI summary

        Returns:
            True if at least one notifier succeeded
        """
        results = []
        for notifier in self.notifiers:
            try:
                results.append(notifier.notify(alert, ai_summary))
            except Exception as e:
                logger.error(f"Notifier {type(notifier).__name__} failed: {e}")
                results.append(False)

        return any(results)

    def notify_batch(self, alerts: list[Alert]) -> None:
        """Send multiple alerts to all notifiers.

        Args:
            alerts: List of alerts to send
        """
        for alert in alerts:
            self.notify(alert)


# Singleton instance for convenience
console_notifier = ConsoleNotifier()
