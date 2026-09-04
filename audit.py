from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LOG = Path("audit_log.jsonl")


def append_event(event_type: str, payload: dict) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        **payload,
    }
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_events() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
