"""Structured logging setup for observability."""

from __future__ import annotations

from agent_gateway.config.settings import Settings
from agent_gateway.logging_config import configure_logging as _configure_structlog


def configure_logging(settings: Settings) -> None:
    """Configure JSON/console structured logging."""
    _configure_structlog(settings)
