"""Alert qualification, deduplication and expiry without delivery side effects."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Signal:
    decision_id: str
    evidence_hash: str
    net_profit: str
    expires_at: datetime
    audit_url: str

    @property
    def key(self) -> str:
        return hashlib.sha256(f"{self.decision_id}|{self.evidence_hash}".encode()).hexdigest()


class AlertGate:
    def __init__(self, cooldown: timedelta) -> None:
        self.cooldown = cooldown
        self._sent: dict[str, datetime] = {}

    def qualify(self, signal: Signal, now: datetime) -> tuple[bool, str]:
        if now >= signal.expires_at:
            return False, "EXPIRED"
        previous = self._sent.get(signal.key)
        if previous is not None and now - previous < self.cooldown:
            return False, "DEDUPLICATED"
        self._sent[signal.key] = now
        return True, "SEND"
