from __future__ import annotations

from typing import Any

import clickhouse_driver

from app.config import ClickHouseConfig


def create_client(config: ClickHouseConfig) -> clickhouse_driver.Client:
    return clickhouse_driver.Client(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
    )


def ping(client: clickhouse_driver.Client) -> None:
    client.execute("SELECT 1")


def insert_batch(
    client: clickhouse_driver.Client,
    table: str,
    rows: list[dict[str, Any]],
    settings: dict[str, Any] | None = None,
) -> None:
    if settings is None:
        client.execute(f"INSERT INTO {table} VALUES", rows)
        return
    client.execute(f"INSERT INTO {table} VALUES", rows, settings=settings)


def select(
    client: clickhouse_driver.Client,
    query: str,
    settings: dict[str, Any] | None = None,
) -> list[tuple[Any, ...]]:
    if settings is None:
        return client.execute(query)
    return client.execute(query, settings=settings)


def get_clickhouse_version(client: clickhouse_driver.Client) -> str:
    result = client.execute("SELECT version()")
    if not result:
        return "unknown"
    return str(result[0][0])


def get_table_row_count(client: clickhouse_driver.Client, table: str) -> int:
    result = client.execute(f"SELECT count() FROM {table}")
    if not result:
        return 0
    return int(result[0][0])

