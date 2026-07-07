from __future__ import annotations

import math


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    if ratio <= 0:
        return min(values)
    if ratio >= 1:
        return max(values)

    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * ratio
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return sorted_values[low]
    weight = position - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def summarize_latency(latencies_ms: list[float]) -> dict[str, float]:
    if not latencies_ms:
        return {
            "min_ms": 0.0,
            "avg_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "max_ms": 0.0,
        }
    total = sum(latencies_ms)
    return {
        "min_ms": round(min(latencies_ms), 4),
        "avg_ms": round(total / len(latencies_ms), 4),
        "p95_ms": round(percentile(latencies_ms, 0.95), 4),
        "p99_ms": round(percentile(latencies_ms, 0.99), 4),
        "max_ms": round(max(latencies_ms), 4),
    }


def compute_rate(total: float, duration_sec: float) -> float:
    if duration_sec <= 0:
        return 0.0
    return total / duration_sec

