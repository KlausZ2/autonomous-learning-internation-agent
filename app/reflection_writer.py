from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from app.config import get_settings
from app.jsonl_store import append_jsonl


def build_reflection_memory(
    interaction: dict[str, Any],
    reward: float,
    feedback_note: str = "",
    path: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if abs(reward) < 0.6:
        return None

    target_comment = interaction.get("target_comment", "")
    generated_reply = interaction.get("generated_reply", "")
    chosen_style = interaction.get("chosen_style") or "unknown"
    direction = "repeat this pattern" if reward > 0 else "avoid this pattern"
    lesson = (
        f"When a comment resembles '{target_comment}', {direction}: "
        f"style={chosen_style}, reply='{generated_reply}'."
    )
    if feedback_note:
        lesson += f" Human feedback: {feedback_note}"

    memory = {
        "memory_id": f"mem_{uuid4().hex}",
        "created_at": datetime.utcnow().isoformat(),
        "source": "feedback_reflection",
        "status": "active",
        "reward": reward,
        "style": chosen_style,
        "lesson": lesson,
        "trigger_comment": target_comment,
        "example_reply": generated_reply,
        "source_interaction_id": interaction.get("interaction_id"),
        "used_inside_joke_ids": interaction.get("used_inside_joke_ids", []),
    }
    settings = get_settings()
    append_jsonl(path or settings.memory_store_file, memory)
    return memory


def write_manual_memory(
    lesson: str,
    style: str = "humorous",
    trigger: str = "",
    path: Optional[str] = None,
) -> dict[str, Any]:
    memory = {
        "memory_id": f"mem_{uuid4().hex}",
        "created_at": datetime.utcnow().isoformat(),
        "source": "manual_teaching",
        "status": "active",
        "reward": 1.0,
        "style": style,
        "lesson": lesson,
        "trigger_comment": trigger,
    }
    settings = get_settings()
    append_jsonl(path or settings.memory_store_file, memory)
    return memory
