from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class TestDataRecord:
    user_id: int
    category: str
    amount: float
    status: str
    region: str
    timestamp: datetime

    def as_clickhouse_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "category": self.category,
            "amount": self.amount,
            "status": self.status,
            "region": self.region,
            "timestamp": self.timestamp,
        }
