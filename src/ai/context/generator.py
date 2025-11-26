"""AI context generator using OpenAI."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.config import get_settings
from src.core.alerts.models import AlertContextData
from .prompts import build_alert_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


class ContextGenerator(ABC):
    """Abstract base class for context generators."""

    @abstractmethod
    def generate(self, data: AlertContextData) -> Optional[str]:
        """Generate context for alert data.

        Args:
            data: Alert context data

        Returns:
            Generated context string or None
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the generator is available/configured.

        Returns:
            True if generator can be used
        """
        ...


class OpenAIContextGenerator(ContextGenerator):
    """OpenAI-based context generator."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 200,
        temperature: float = 0.3,
    ):
        """Initialize the OpenAI generator.

        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = None

    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("OpenAI package not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                return None
        return self._client

    def is_available(self) -> bool:
        """Check if OpenAI is configured and available."""
        return bool(self.api_key and self.client is not None)

    def generate(self, data: AlertContextData) -> Optional[str]:
        """Generate context using OpenAI.

        Args:
            data: Alert context data

        Returns:
            Generated context or None on failure
        """
        if not self.is_available():
            logger.warning("OpenAI not available, skipping context generation")
            return None

        try:
            # Build the prompt with enriched context
            prompt = build_alert_prompt(
                symbol=data.symbol,
                rule_name=data.rule_name,
                rule_type=data.rule_type,
                threshold=data.threshold,
                current_price=data.current_price,
                message=data.message,
                cost_basis=data.cost_basis,
                percent_change=data.percent_change,
                rsi=data.rsi,
                indicator_value=data.indicator_value,
                high_52_week=data.high_52_week,
                low_52_week=data.low_52_week,
            )

            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            content = response.choices[0].message.content
            return content.strip() if content else None

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return None


class MockContextGenerator(ContextGenerator):
    """Mock context generator for testing."""

    def __init__(self, response: Optional[str] = None):
        """Initialize mock generator.

        Args:
            response: Fixed response to return (or generates a default)
        """
        self.response = response

    def is_available(self) -> bool:
        """Always available."""
        return True

    def generate(self, data: AlertContextData) -> Optional[str]:
        """Generate mock context.

        Args:
            data: Alert context data

        Returns:
            Mock context string
        """
        if self.response:
            return self.response

        # Generate a simple mock response
        direction = "rose" if (data.percent_change or 0) > 0 else "fell"
        return (
            f"{data.symbol} {direction} to ${data.current_price:.2f}. "
            f"This triggered your '{data.rule_name}' rule. "
            f"The stock is currently trading based on market conditions. "
            f"Consider reviewing your investment thesis. "
            f"This is not financial advice."
        )


def get_context_generator() -> ContextGenerator:
    """Get the appropriate context generator based on configuration.

    Returns:
        Context generator instance
    """
    if settings.openai_api_key:
        generator = OpenAIContextGenerator()
        if generator.is_available():
            return generator

    # Fall back to mock
    logger.info("Using mock context generator (no OpenAI API key configured)")
    return MockContextGenerator()
