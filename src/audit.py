import json
from datetime import datetime, timezone
from threading import Lock

from config.settings import settings


_audit_lock = Lock()


def record_event(event: str, thread_id: str, **details: object) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "thread_id": thread_id,
        **details,
    }
    with _audit_lock:
        with settings.AUDIT_LOG_PATH.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(entry, default=str) + "\n")