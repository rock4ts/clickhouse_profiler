from __future__ import annotations

import random
import threading
import time
from itertools import product
from typing import Any

import structlog

from app.clickhouse.client import (
    create_client,
    get_table_row_count,
    insert_batch,
    ping,
    select,
)
from app.clickhouse.reset import clear_clickhouse_caches, reset_benchmark_table
from app.clickhouse.operations import READ_QUERIES, build_insert_rows
from app.config import ClickHouseConfig, ProfilerConfig, WriteReadConfig
from app.metrics import compute_rate, summarize_latency
from app.scenarios.write_read.reporter import append_result_row, create_run_report


def _build_experiment_row(
    run_result: dict[str, Any],
    writers: int,
    batch: int,
    readers: int,
) -> dict[str, Any]:
    return {
        "writers": writers,
        "batch_size": batch,
        "readers": readers,
        "run_duration_sec": run_result["duration_sec"],
        "ingestion_throughput_per_sec": run_result["ingestion_throughput_per_sec_rows_sec"],
        # "writer_errors": run_result["writer_errors"],
        "rows_written": run_result["total_transfered"],
        "avg_agg_query_time": run_result["avg_agg_query_time_ms"],
        "p95_agg_query_time": run_result["p95_agg_query_time_ms"],
        "max_agg_query_time": run_result["max_agg_query_time_ms"],
        "queries_executed": run_result["queries_executed"],
        # "reader_errors": run_result["reader_errors"],
    }


def run(
    scenario_config: WriteReadConfig,
    clickhouse_config: ClickHouseConfig,
    profiler_config: ProfilerConfig,
) -> str:
    logger = structlog.get_logger("profiler.scenarios.write_read")
    metadata = {
        "clickhouse_container": {
            "cpus": float(profiler_config.clickhouse_container_cpus),
            "ram_limit": profiler_config.clickhouse_container_ram_limit,
        },
        "scenario_config": scenario_config.model_dump(by_alias=True),
    }
    results_file = create_run_report(profiler_config.results_dir, metadata=metadata)
    readers = int(scenario_config.reader_threads)
    logger.info(
        "scenario_started",
        scenario="write_read",
        metadata=metadata,
    )
    for writers, batch in product(
        scenario_config.writer_thread_list, scenario_config.insert_batch_size_list
    ):
        reset_benchmark_table(clickhouse_config)
        clear_clickhouse_caches(clickhouse_config)
        run_result = _run_instance(
            scenario_config=scenario_config,
            clickhouse_config=clickhouse_config,
            writer_threads=int(writers),
            insert_batch_size=int(batch),
        )
        logger.info(
            "scenario_instance_finished",
            scenario="write_read",
            writers=int(writers),
            batch=int(batch),
            readers=readers,
            duration_sec=run_result.get("duration_sec"),
            failed_writes=run_result.get("failed_writes"),
            write_retries=run_result.get("write_retries"),
        )
        append_result_row(
            target=results_file,
            row=_build_experiment_row(
                run_result=run_result,
                writers=int(writers),
                batch=int(batch),
                readers=readers,
            ),
        )

    return "success"


def _run_instance(
    scenario_config: WriteReadConfig,
    clickhouse_config: ClickHouseConfig,
    writer_threads: int,
    insert_batch_size: int,
) -> dict[str, Any]:
    logger = structlog.get_logger("profiler.scenarios.write_read")
    current_event_count = 0
    count_client = create_client(clickhouse_config)
    try:
        ping(count_client)
        current_event_count = get_table_row_count(count_client, clickhouse_config.table)
    except Exception:
        logger.warning(
            "failed_to_get_current_event_count",
            scenario="write_read",
            table=clickhouse_config.table,
        )
    finally:
        count_client.disconnect()

    logger.info(
        "scenario_instance_started",
        scenario="write_read",
        duration_seconds=float(scenario_config.duration_seconds),
        insert_batch_size=int(insert_batch_size),
        writer_threads=int(writer_threads),
        reader_threads=int(scenario_config.reader_threads),
        current_event_count=current_event_count,
    )

    started = time.perf_counter()
    deadline = started + float(scenario_config.duration_seconds)

    lock = threading.Lock()
    start_barrier = threading.Event()
    stop_event = threading.Event()
    remaining_readers = scenario_config.reader_threads

    writer_results: list[dict[str, int]] = []
    reader_results: list[dict[str, int]] = []
    latencies_ms: list[float] = []

    def writer_worker(worker_idx: int) -> None:
        inserted_rows = 0
        inserts = 0
        failed_writes = 0
        retries = 0
        randomizer = random.Random(random.randint(1, 5) * 100_000 + worker_idx)

        client = create_client(clickhouse_config)
        try:
            ping(client)
            start_barrier.wait()
            while not stop_event.is_set() and time.perf_counter() < deadline:
                rows = build_insert_rows(randomizer, insert_batch_size, offset=inserted_rows)
                attempt = 0
                while True:
                    try:
                        insert_batch(
                            client,
                            clickhouse_config.table,
                            rows,
                            settings={
                                "max_execution_time": int(
                                    scenario_config.insert_request_timeout_seconds
                                )
                            },
                        )
                        inserted_rows += len(rows)
                        inserts += 1
                        break
                    except Exception:
                        if attempt >= scenario_config.max_retries:
                            failed_writes += 1
                            break
                        attempt += 1
                        retries += 1
        finally:
            client.disconnect()

        with lock:
            writer_results.append(
                {
                    "thread": worker_idx,
                    "rows": inserted_rows,
                    "inserts": inserts,
                    "failed_writes": failed_writes,
                    "retries": retries,
                }
            )

    def reader_worker(worker_idx: int) -> None:
        nonlocal remaining_readers
        success = 0
        errors = 0
        timeouts = 0
        local_latencies_ms: list[float] = []

        client = create_client(clickhouse_config)
        try:
            ping(client)
            start_barrier.wait()
            query_idx = 0
            while not stop_event.is_set() and time.perf_counter() < deadline:
                query = READ_QUERIES[(worker_idx + query_idx) % len(READ_QUERIES)]
                query_started = time.perf_counter()
                try:
                    select(
                        client,
                        query.replace("test_data", clickhouse_config.table),
                        settings={
                            "max_execution_time": int(scenario_config.read_request_timeout_seconds),
                        },
                    )
                    elapsed_ms = (time.perf_counter() - query_started) * 1000
                    local_latencies_ms.append(elapsed_ms)
                    success += 1
                except Exception as exc:
                    errors += 1
                    if "TIMEOUT_EXCEEDED" in str(exc):
                        timeouts += 1
                finally:
                    query_idx += 1
        finally:
            client.disconnect()

        with lock:
            latencies_ms.extend(local_latencies_ms)
            reader_results.append(
                {
                    "thread": worker_idx,
                    "success_query_count": success,
                    "errors": errors,
                    "timeouts": timeouts,
                }
            )
            remaining_readers -= 1
            if remaining_readers == 0:
                stop_event.set()

    jobs: list[threading.Thread] = []
    for idx in range(writer_threads):
        jobs.append(threading.Thread(target=writer_worker, args=(idx,), daemon=False))
    for idx in range(scenario_config.reader_threads):
        jobs.append(threading.Thread(target=reader_worker, args=(idx,), daemon=False))

    for job in jobs:
        job.start()
    start_barrier.set()
    for job in jobs:
        job.join()

    duration = time.perf_counter() - started

    inserted_total = sum(int(result["rows"]) for result in writer_results)
    insert_count_total = sum(int(result["inserts"]) for result in writer_results)
    failed_writes_total = sum(int(result["failed_writes"]) for result in writer_results)
    retries_total = sum(int(result["retries"]) for result in writer_results)

    queries_total = sum(int(result["success_query_count"]) for result in reader_results)
    reader_errors = sum(int(result["errors"]) for result in reader_results)
    reader_timeouts = sum(int(result["timeouts"]) for result in reader_results)

    latency = summarize_latency(latencies_ms)

    return {
        "scenario": "write_read",
        "writer_threads": writer_threads,
        "reader_threads": scenario_config.reader_threads,
        "duration_sec": round(duration, 4),
        "insert_batch_size": insert_batch_size,
        "total_transfered": inserted_total,
        "queries_executed": queries_total,
        "ingestion_throughput_per_sec_rows_sec": round(compute_rate(inserted_total, duration), 4),
        "failed_writes": failed_writes_total,
        "writer_errors": failed_writes_total,
        "reader_errors": reader_errors,
        "write_retries": retries_total,
        "avg_agg_query_time_ms": latency["avg_ms"],
        "p95_agg_query_time_ms": latency["p95_ms"],
        "max_agg_query_time_ms": latency["max_ms"],
        "agg_query_times_ms": [round(value, 4) for value in latencies_ms],
        "errors": failed_writes_total + reader_errors,
        "timeouts": reader_timeouts,
        "worker_results": {
            "writers": writer_results,
            "readers": reader_results,
        },
        "internal": {
            "insert_count": insert_count_total,
        },
    }
