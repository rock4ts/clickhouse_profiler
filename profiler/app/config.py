from __future__ import annotations

from pydantic import Field, NonNegativeInt, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProfilerConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    results_dir: str = "results"
    clickhouse_container_cpus: PositiveFloat = 6.0
    clickhouse_container_ram_limit: str = "8g"


class ClickHouseConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_prefix="CLICKHOUSE_")

    host: str = "localhost"
    port: PositiveInt = 9000
    user: str = "profiler"
    password: str = "profiler"
    database: str = "profiler"
    table: str = "events"
    initial_table: str = "initial_events"


class WriteReadConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_prefix="WR_")

    duration_seconds: PositiveFloat = Field(120.0, serialization_alias="duration_per_instance_sec")
    insert_batch_size_list: list[PositiveInt] = [3000, 5000, 8000]
    writer_thread_list: list[PositiveInt] = [3, 4, 5]
    reader_threads: PositiveInt = 10
    max_retries: NonNegativeInt = 3
    insert_request_timeout_seconds: PositiveFloat = 10.0
    read_request_timeout_seconds: PositiveFloat = 20.0
