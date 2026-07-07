from __future__ import annotations

import logging

import structlog

from app import clickhouse
from app.config import ClickHouseConfig, LoaderConfig


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def main() -> int:
    configure_logging()

    logger = structlog.get_logger("dsloader.main")
    loader_config = LoaderConfig()
    logger.info(
        "loader_started",
        records_count=loader_config.records_count,
        batch_size=loader_config.batch_size,
        skip_if_populated=loader_config.skip_if_populated,
    )

    try:
        loaded_rows = clickhouse.run(loader_config, ClickHouseConfig())
    except Exception as exc:
        logger.error("loader_failed", error=str(exc))
    logger.info("loader_finished", loaded_rows=loaded_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
