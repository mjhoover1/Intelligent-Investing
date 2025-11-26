"""Scheduler for running periodic monitoring cycles."""

from __future__ import annotations

import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import get_settings
from .monitor import run_monitor_cycle

logger = logging.getLogger(__name__)
settings = get_settings()


class MonitorScheduler:
    """Scheduler for periodic monitoring cycles."""

    def __init__(
        self,
        interval_seconds: Optional[int] = None,
        use_ai: bool = False,
        ignore_cooldown: bool = False,
    ):
        """Initialize the scheduler.

        Args:
            interval_seconds: Seconds between cycles (defaults to settings)
            use_ai: Whether to generate AI context
            ignore_cooldown: Whether to ignore cooldowns
        """
        self.interval = interval_seconds or settings.monitor_interval_seconds
        self.use_ai = use_ai
        self.ignore_cooldown = ignore_cooldown
        self.scheduler = BlockingScheduler()
        self._cycle_count = 0

    def _run_cycle(self) -> None:
        """Execute a single monitoring cycle."""
        self._cycle_count += 1
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        logger.info(f"[Cycle {self._cycle_count}] Starting at {timestamp}")

        try:
            alerts = run_monitor_cycle(
                use_ai=self.use_ai,
                ignore_cooldown=self.ignore_cooldown,
            )

            if alerts:
                logger.info(f"[Cycle {self._cycle_count}] Created {len(alerts)} alert(s)")
            else:
                logger.info(f"[Cycle {self._cycle_count}] No alerts triggered")

        except Exception as e:
            logger.error(f"[Cycle {self._cycle_count}] Error: {e}")

    def start(self) -> None:
        """Start the scheduler (blocking)."""
        # Set up signal handlers for graceful shutdown
        def handle_signal(signum, frame):
            logger.info("Received shutdown signal, stopping scheduler...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Add the monitoring job
        self.scheduler.add_job(
            self._run_cycle,
            trigger=IntervalTrigger(seconds=self.interval),
            id="monitor_cycle",
            name="Portfolio Monitor",
            replace_existing=True,
        )

        logger.info(f"Starting scheduler with {self.interval}s interval (AI={'enabled' if self.use_ai else 'disabled'})")
        logger.info("Press Ctrl+C to stop")

        # Run first cycle immediately
        self._run_cycle()

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown complete")


def start_scheduler(
    interval_seconds: Optional[int] = None,
    use_ai: bool = False,
    ignore_cooldown: bool = False,
) -> None:
    """Start the monitoring scheduler (convenience function).

    Args:
        interval_seconds: Seconds between cycles
        use_ai: Whether to generate AI context
        ignore_cooldown: Whether to ignore cooldowns
    """
    scheduler = MonitorScheduler(
        interval_seconds=interval_seconds,
        use_ai=use_ai,
        ignore_cooldown=ignore_cooldown,
    )
    scheduler.start()
