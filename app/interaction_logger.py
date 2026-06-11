from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from app.config import get_settings
from app.jsonl_store import append_jsonl
from app.schemas import AgentDecision, InstagramComment


def log_interaction(
    comment: InstagramComment,
    decision: AgentDecision,
    context: dict[str, Any],
    applied: bool,
    apply_error: Optional[str],
    path: Optional[str] = None,
) -> dict[str, Any]:
    settings = get_settings()
    record = {
        "interaction_id": f"int_{uuid4().hex}",
        "timestamp": datetime.utcnow().isoformat(),
        "post_id": comment.media_id,
        "comment_id": comment.id,
        "post_caption": context.get("post_caption", ""),
        "post_topic": context.get("post_topic", ""),
        "target_comment": comment.text,
        "thread_context": context.get("thread_context", []),
        "other_user_comments": context.get("other_user_comments", []),
        "developer_instruction_summary": context.get("developer_instruction", ""),
        "developer_files_summary": context.get("developer_files_summary", ""),
        "used_memory_ids": decision.used_memory_ids,
        "used_inside_joke_ids": decision.used_inside_joke_ids,
        "chosen_style": decision.chosen_style,
        "style_confidence": decision.style_confidence,
        "estimated_reward": decision.estimated_reward,
        "style_selection_reason": decision.style_selection_reason,
        "risk_flags": [],
        "generated_reply": decision.reply_text,
        "action_taken": decision.action.value,
        "applied": applied,
        "apply_error": apply_error,
        "feedback": None,
        "reward": None,
        "reflection_id": None,
    }
    append_jsonl(path or settings.interactions_file, record)
    return record
