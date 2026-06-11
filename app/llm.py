import json
import re
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.policy import load_policy_text
from app.schemas import AgentAction, AgentDecision, CommentCategory, InstagramComment


def _json_from_text(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(text[start : end + 1])


def _normalize_enum(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    aliases = {
        "question": "genuine_question",
        "genuine_question": "genuine_question",
        "product_question": "product_question",
        "compliment": "generic_compliment",
        "generic_praise": "generic_compliment",
        "praise": "generic_compliment",
        "generic_compliment": "generic_compliment",
        "spam_scam": "spam",
        "suspicious_link": "suspicious_link",
        "negative_feedback": "ambiguous_negative_feedback",
        "ambiguous_negative_feedback": "ambiguous_negative_feedback",
        "reply": "reply_public",
        "public_reply": "reply_public",
        "reply_public": "reply_public",
        "no_action": "ignore",
        "ignore": "ignore",
        "hide": "hide",
        "delete": "delete",
    }
    return aliases.get(normalized, normalized)


def _normalize_decision_payload(payload: dict) -> dict:
    if "comment_id" in payload:
        payload["comment_id"] = str(payload["comment_id"])
    payload["category"] = _normalize_enum(payload.get("category"))
    payload["action"] = _normalize_enum(payload.get("action"))
    if payload["category"] not in {item.value for item in CommentCategory}:
        payload["category"] = CommentCategory.other.value
    if payload["action"] not in {item.value for item in AgentAction}:
        payload["action"] = AgentAction.ignore.value
    if payload.get("action") != AgentAction.reply_public.value:
        payload["reply_text"] = None
    return payload


def _system_prompt() -> str:
    policy = load_policy_text()
    return f"""
You are an Instagram comment response agent for a controlled agent testing project.

This is not a production brand account. It is a test environment for evaluating an Instagram agent.
Replies may be casual, playful, irreverent, and mildly to moderately offensive when the context fits.
Avoid sounding corporate, overly serious, or sanitized.
Do not make explicit threats or target protected classes.

The custom policy below is authoritative and must be included in every decision:

<policy>
{policy}
</policy>

Allowed actions are exactly:
- reply_public
- ignore
- hide
- delete

Return only valid JSON.
""".strip()


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def decide(self, comment: InstagramComment) -> AgentDecision:
        if not self.client:
            return self._baseline_decide(comment)

        user_prompt = f"""
Classify this Instagram comment, choose one automatic action, and generate a reply when the action is reply_public.

Comment ID: {comment.id}
Username: {comment.username or "unknown"}
Text: {comment.text}

Tone for public replies: {self.settings.default_reply_tone}

Return JSON with:
comment_id, category, action, confidence, reply_text, policy_summary, reasoning, should_apply.
reply_text must be null unless action is reply_public.
""".strip()

        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        payload = _json_from_text(response.choices[0].message.content or "{}")
        payload = _normalize_decision_payload(payload)
        return AgentDecision(**payload)

    def _baseline_decide(self, comment: InstagramComment) -> AgentDecision:
        text = comment.text.lower()
        policy = load_policy_text()

        if any(word in text for word in ["http://", "https://", "free money", "crypto", "giveaway", "dm me"]):
            category = CommentCategory.spam
            action = AgentAction.reply_public
            confidence = 0.88
            reply = self.settings.default_reply_text
            reason = "Keyword baseline detected link or promo-like language and generated a reply."
        elif "?" in text or any(word in text for word in ["how", "what", "when", "where", "price", "cost"]):
            category = CommentCategory.genuine_question
            action = AgentAction.reply_public
            confidence = 0.78
            reply = "Thanks for asking! We will share more details soon."
            reason = "Keyword baseline detected a genuine question."
        elif any(word in text for word in ["love", "great", "nice", "awesome", "cool", "thanks"]):
            category = CommentCategory.generic_compliment
            action = AgentAction.reply_public
            confidence = 0.80
            reply = self.settings.default_reply_text
            reason = "Keyword baseline detected a generic compliment and generated a reply."
        else:
            category = CommentCategory.other
            action = AgentAction.reply_public
            confidence = 0.60
            reply = self.settings.default_reply_text
            reason = "Keyword baseline generated a default reply."

        return AgentDecision(
            comment_id=comment.id,
            category=category,
            action=action,
            confidence=confidence,
            reply_text=reply,
            policy_summary=policy[:500],
            reasoning=reason,
            should_apply=True,
        )
