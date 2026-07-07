from __future__ import annotations

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoaderConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    records_count: PositiveInt
    batch_size: PositiveInt
    skip_if_populated: bool = True


class ClickHouseConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_prefix="CLICKHOUSE_")

    host: str
    port: PositiveInt = 9000
    user: str = "default"
    password: str = ""
    database: str = "default"
    table: str = "events"
    initial_table: str = "initial_events"
