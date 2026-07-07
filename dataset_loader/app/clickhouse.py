from __future__ import annotations

import time

import clickhouse_driver
import structlog

from app.config import ClickHouseConfig, LoaderConfig
from app.generator import generate_batches

_TABLE_SCHEMA_SQL = """
(
    user_id UInt32,
    category String,
    amount Float64,
    status String,
    region String,
    timestamp DateTime
) ENGINE = MergeTree()
ORDER BY (timestamp, category)
"""


def _create_client(config: ClickHouseConfig) -> clickhouse_driver.Client:
    return clickhouse_driver.Client(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
    )


def _table_exists(client: clickhouse_driver.Client, database: str, table: str) -> bool:
    result = client.execute(
        """
        SELECT count()
        FROM system.tables
        WHERE database = %(database)s AND name = %(table)s
        """,
        {"database": database, "table": table},
    )
    return bool(result[0][0])


def _get_row_count(client: clickhouse_driver.Client, table: str) -> int:
    result = client.execute(f"SELECT count() FROM {table}")
    return int(result[0][0])


def _create_table(client: clickhouse_driver.Client, table: str) -> None:
    client.execute(f"CREATE TABLE {table} {_TABLE_SCHEMA_SQL}")


def run(loader_config: LoaderConfig, db_config: ClickHouseConfig) -> int:
    logger = structlog.get_logger("dsloader.clickhouse").bind(
        db="clickhouse",
        initial_table=db_config.initial_table,
        benchmark_table=db_config.table,
    )

    client = _create_client(db_config)
    try:
        client.execute("SELECT 1")
    except Exception as exc:
        logger.info("databse_error", error=str(exc))
        raise Exception("failed to connect to clickhouse")

    started_at = time.monotonic()

    if loader_config.skip_if_populated and _table_exists(
        client, db_config.database, db_config.initial_table
    ):
        existing_rows = _get_row_count(client, db_config.initial_table)
        if existing_rows >= loader_config.records_count:
            logger.info(
                "load_skipped",
                reason="initial_table_already_populated",
                existing_rows=existing_rows,
                records_count=loader_config.records_count,
            )
            if not _table_exists(client, db_config.database, db_config.table):
                logger.info("create_benchmark_table_started")
                _create_table(client, db_config.table)
                logger.info("create_benchmark_table_finished")

            client.disconnect()
            return existing_rows

        logger.info(
            "load_required",
            reason="initial_table_not_populated",
            records_count=loader_config.records_count,
        )

    total_rows = 0

    logger.info("drop_tables_started")
    client.execute(f"DROP TABLE IF EXISTS {db_config.table}")
    client.execute(f"DROP TABLE IF EXISTS {db_config.initial_table}")
    logger.info("drop_tables_finished")

    logger.info("create_tables_started")
    _create_table(client, db_config.initial_table)
    _create_table(client, db_config.table)
    logger.info("create_tables_finished")

    for batch in generate_batches(loader_config.records_count, loader_config.batch_size):
        rows = [record.as_clickhouse_dict() for record in batch]
        client.execute(f"INSERT INTO {db_config.initial_table} VALUES", rows)
        total_rows += len(rows)
        logger.info("batch_inserted", batch_size=len(rows), total_rows=total_rows)

    client.disconnect()
    elapsed = time.monotonic() - started_at
    logger.info("load_completed", loaded_rows=total_rows, elapsed_seconds=round(elapsed, 3))
    return total_rows
