from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Envelope:
    msg_id: str
    type: str
    timestamp: int
    trace_id: str | None = None
    target_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
