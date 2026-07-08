from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

FIELDNAMES = [
    "run_duration_sec",
    "writers",
    "batch_size",
    "rows_written",
    # "writer_errors",
    "ingestion_throughput_per_sec",
    "readers",
    "queries_executed",
    # "reader_errors",
    "avg_agg_query_time",
    "p95_agg_query_time",
    "max_agg_query_time",
]


def create_run_report(results_root: str, metadata: Mapping[str, object]) -> Path:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_dir = Path(results_root) / "write_read" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = run_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    target = run_dir / "profile.csv"
    with target.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
    return target


def append_result_row(target: Path, row: Mapping[str, object]) -> None:
    with target.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writerow(row)


def save_results_to_csv(
    results_root: str,
    rows: list[Mapping[str, object]],
    metadata: Mapping[str, object] | None = None,
) -> str:
    target = create_run_report(results_root, metadata=metadata or {})
    for row in rows:
        append_result_row(target, row)
    return str(target)
