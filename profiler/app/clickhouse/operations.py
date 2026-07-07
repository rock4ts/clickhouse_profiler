from __future__ import annotations


import random
from datetime import datetime, timedelta
from typing import Any

READ_QUERIES: tuple[str, ...] = (
    """
    SELECT
        category,
        COUNT(*) AS count,
        AVG(amount) AS avg_amount
    FROM test_data
    GROUP BY category
    """,
    """
    SELECT
        region,
        COUNT(*) AS count,
        SUM(amount) AS total_amount
    FROM test_data
    GROUP BY region
    ORDER BY region
    """,
    """
    SELECT
        user_id,
        category,
        COUNT(*) AS transaction_count,
        AVG(amount) AS avg_amount,
        MIN(amount) AS min_amount,
        MAX(amount) AS max_amount
    FROM test_data
    WHERE status = 'success'
    GROUP BY user_id, category
    HAVING COUNT(*) > 10
    ORDER BY transaction_count DESC
    LIMIT 100
    """,
)


_CATEGORIES: tuple[str, ...] = ("A", "B", "C", "D", "E")
_STATUSES: tuple[str, ...] = ("success", "failed", "pending")
_REGIONS: tuple[str, ...] = ("North", "South", "East", "West")


def build_insert_rows(randomizer: random.Random, count: int, offset: int) -> list[dict[str, Any]]:
    base_ts = datetime.now() + timedelta(seconds=offset)
    rows: list[dict[str, Any]] = []
    for i in range(count):
        rows.append(
            {
                "user_id": randomizer.randint(1, 10_000),
                "category": randomizer.choice(_CATEGORIES),
                "amount": round(randomizer.gauss(1000, 200), 4),
                "status": randomizer.choice(_STATUSES),
                "region": randomizer.choice(_REGIONS),
                "timestamp": base_ts + timedelta(seconds=i),
            }
        )
    return rows
