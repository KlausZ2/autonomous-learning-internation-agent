from typing import Any, Optional

from app.config import get_settings
from app.jsonl_store import read_jsonl, write_jsonl


def consolidate_memories(path: Optional[str] = None) -> dict[str, Any]:
    settings = get_settings()
    memory_path = path or settings.memory_store_file
    records = read_jsonl(memory_path)
    seen = set()
    superseded = 0

    for record in records:
        if record.get("status", "active") != "active":
            continue
        key = (
            record.get("style", ""),
            record.get("trigger_comment", ""),
            record.get("lesson", ""),
        )
        if key in seen:
            record["status"] = "superseded"
            superseded += 1
            continue
        seen.add(key)

    write_jsonl(memory_path, records)
    active = sum(1 for record in records if record.get("status", "active") == "active")
    return {"total": len(records), "active": active, "superseded": superseded}
