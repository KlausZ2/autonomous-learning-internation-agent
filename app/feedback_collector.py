from datetime import datetime
from typing import Any, Optional

from app.config import get_settings
from app.jsonl_store import read_jsonl, write_jsonl
from app.reflection_writer import build_reflection_memory
from app.reward_model import score_feedback


def list_interactions(limit: int = 50, path: Optional[str] = None) -> list[dict[str, Any]]:
    settings = get_settings()
    records = read_jsonl(path or settings.interactions_file)
    return list(reversed(records[-limit:]))


def record_feedback(
    interaction_id: str,
    rating: Optional[int] = None,
    label: Optional[str] = None,
    note: str = "",
    path: Optional[str] = None,
    memory_path: Optional[str] = None,
) -> dict[str, Any]:
    settings = get_settings()
    interactions_path = path or settings.interactions_file
    records = read_jsonl(interactions_path)
    reward = score_feedback(rating=rating, label=label)

    for record in records:
        if record.get("interaction_id") != interaction_id:
            continue
        feedback = {
            "rating": rating,
            "label": label,
            "note": note,
            "updated_at": datetime.utcnow().isoformat(),
        }
        memory = build_reflection_memory(record, reward=reward, feedback_note=note, path=memory_path)
        record["feedback"] = feedback
        record["reward"] = reward
        record["reflection_id"] = memory["memory_id"] if memory else None
        write_jsonl(interactions_path, records)
        return {
            "interaction_id": interaction_id,
            "feedback": feedback,
            "reward": reward,
            "reflection": memory,
        }

    raise ValueError(f"Interaction not found: {interaction_id}")
