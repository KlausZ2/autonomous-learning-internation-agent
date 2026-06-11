from typing import Any, Optional

from app.config import get_settings
from app.jsonl_store import read_jsonl


def load_active_inside_jokes(path: Optional[str] = None) -> list[dict[str, Any]]:
    settings = get_settings()
    records = read_jsonl(path or settings.inside_jokes_file)
    return [record for record in records if record.get("status", "active") == "active"]
