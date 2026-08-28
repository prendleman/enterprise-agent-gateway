"""Seed the database from synthetic JSON datasets."""

import asyncio
import sys

import structlog

from agent_gateway.config.settings import get_settings
from agent_gateway.logging_config import configure_logging
from agent_gateway.storage.seed import seed_database


async def main() -> int:
    settings = get_settings()
    configure_logging(settings)
    logger = structlog.get_logger(__name__)
    logger.info("seed_data_starting", demo_mode=settings.is_demo)
    counts = await seed_database(settings)
    logger.info("seed_data_finished", **counts)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
