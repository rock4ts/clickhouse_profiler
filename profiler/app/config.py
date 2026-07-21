from __future__ import annotations

from pydantic import Field, NonNegativeInt, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProfilerConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    results_dir: str = "results"
    clickhouse_node_count: PositiveInt = 4
    clickhouse_node_cpus: PositiveFloat = 2.0
    clickhouse_node_ram_gb: PositiveFloat = 2.0
    profiler_warmup_enabled: bool = True
    profiler_warmup_duration_seconds: PositiveInt = 15

    @property
    def clickhouse_cluster_cpus(self) -> float:
        return float(self.clickhouse_node_count) * float(self.clickhouse_node_cpus)

    @property
    def clickhouse_cluster_ram_limit(self) -> str:
        cluster_ram_gb = float(self.clickhouse_node_count) * float(self.clickhouse_node_ram_gb)
        # Keep integer formatting for clean metadata (e.g. "8g" instead of "8.0g").
        if cluster_ram_gb.is_integer():
            return f"{int(cluster_ram_gb)}g"
        return f"{cluster_ram_gb}g"


class ClickHouseConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_prefix="CLICKHOUSE_")

    host: str = "localhost"
    port: PositiveInt = 9000
    user: str = "profiler"
    password: str = "profiler"
    database: str = "profiler"
    table: str = "events"
    initial_table: str = "initial_events"
    local_table: str = "events_local"
    initial_local_table: str = "initial_events_local"
    cluster: str = "ugc_cluster"


class WriteReadConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_prefix="WR_")

    duration_seconds: PositiveFloat = Field(120.0, serialization_alias="duration_per_instance_sec")
    insert_batch_size_list: list[PositiveInt] = [3000, 5000, 8000]
    writer_thread_list: list[PositiveInt] = [3, 4, 5]
    reader_threads: PositiveInt = 10
    max_retries: NonNegativeInt = 3
    insert_request_timeout_seconds: PositiveFloat = 10.0
    read_request_timeout_seconds: PositiveFloat = 20.0
