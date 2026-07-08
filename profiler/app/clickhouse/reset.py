from __future__ import annotations

import time

import structlog

from app.clickhouse.client import create_client, get_table_row_count
from app.config import ClickHouseConfig


def clear_clickhouse_caches(config: ClickHouseConfig) -> None:
    logger = structlog.get_logger("profiler.clickhouse.reset")
    logger.info("clear_clickhouse_caches_started")
    commands = (
        "SYSTEM DROP MARK CACHE",
        "SYSTEM DROP UNCOMPRESSED CACHE",
        "SYSTEM DROP QUERY CACHE",
    )
    client = create_client(config)
    try:
        for command in commands:
            try:
                client.execute(command)
                logger.info(
                    "cache_clear_command_succeeded",
                    command=command,
                )
            except Exception:
                logger.warning("cache_clear_command_failed", command=command)
    finally:
        client.disconnect()
    logger.info("clear_clickhouse_caches_finished")


def reset_benchmark_table(config: ClickHouseConfig) -> int:
    logger = structlog.get_logger("profiler.clickhouse.reset")
    started_at = time.perf_counter()
    logger.info(
        "benchmark_reset_started",
        benchmark_table=config.table,
        initial_table=config.initial_table,
    )

    client = create_client(config)
    try:
        client.execute(f"TRUNCATE TABLE {config.table}")
        client.execute(f"INSERT INTO {config.table} SELECT * FROM {config.initial_table}")
        restored_rows = get_table_row_count(client, config.table)
    finally:
        client.disconnect()

    elapsed = time.perf_counter() - started_at
    logger.info(
        "benchmark_reset_finished",
        benchmark_table=config.table,
        initial_table=config.initial_table,
        rows_restored=restored_rows,
        elapsed_seconds=round(elapsed, 4),
    )
    return restored_rows
