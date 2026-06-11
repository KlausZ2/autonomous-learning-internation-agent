from typing import Any, Optional

from app.config import get_settings
from app.jsonl_store import read_jsonl


def load_active_memories(path: Optional[str] = None) -> list[dict[str, Any]]:
    settings = get_settings()
    records = read_jsonl(path or settings.memory_store_file)
    return [record for record in records if record.get("status", "active") == "active"]
