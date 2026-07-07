from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Iterator

from app.models import TestDataRecord


def generate_batches(
    total_records: int,
    batch_size: int,
    seed: int | None = None,
) -> Iterator[list[TestDataRecord]]:
    if total_records <= 0:
        return

    randomizer = random.Random(seed)
    categories: tuple[str, ...] = ("A", "B", "C", "D", "E")
    statuses: tuple[str, ...] = ("success", "failed", "pending")
    regions: tuple[str, ...] = ("North", "South", "East", "West")
    base_ts = datetime.utcnow()

    generated = 0
    while generated < total_records:
        remaining = total_records - generated
        current_batch_size = batch_size if remaining > batch_size else remaining
        batch: list[TestDataRecord] = []

        for _ in range(current_batch_size):
            batch.append(
                TestDataRecord(
                    user_id=randomizer.randint(1, 10_000),
                    category=randomizer.choice(categories),
                    amount=round(randomizer.gauss(1000, 200), 4),
                    status=randomizer.choice(statuses),
                    region=randomizer.choice(regions),
                    timestamp=base_ts + timedelta(seconds=generated),
                )
            )
            generated += 1

        yield batch
