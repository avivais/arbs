"""Read-only health and quality metrics represented as deterministic JSON."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ScanMetrics:
    adapter_requests: int
    adapter_errors: int
    latency_ms_max: int
    raw_catalog_records: int
    normalized_records: int
    unsupported_records: int
    review_decisions: int
    exact_decisions: int
    stale_books: int
    policy_version: str
    parser_version: str

    def as_dict(self) -> dict[str, int | float | str]:
        total = max(1, self.raw_catalog_records)
        candidates = max(1, self.review_decisions + self.exact_decisions)
        return {
            **asdict(self),
            "parser_coverage": self.normalized_records / total,
            "unsupported_rate": self.unsupported_records / total,
            "exact_rate": self.exact_decisions / candidates,
        }
