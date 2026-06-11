import json
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm import _json_from_text
from app.policy import load_policy_text


StyleName = Literal["professional", "humorous"]


class StyleSelectorInput(BaseModel):
    post_caption: str = ""
    post_topic: str = ""
    target_comment: str
    thread_context: list[str] = Field(default_factory=list)
    other_user_comments: list[str] = Field(default_factory=list)
    developer_instruction: str = ""
    developer_files_summary: str = ""
    inside_jokes: list[dict[str, Any]] = Field(default_factory=list)
    memories: list[dict[str, Any]] = Field(default_factory=list)


class EstimatedReward(BaseModel):
    professional: float = Field(ge=0.0, le=1.0)
    humorous: float = Field(ge=0.0, le=1.0)


class StyleDecision(BaseModel):
    chosen_style: StyleName
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_reward: EstimatedReward
    reason: str
    risk_flags: list[str] = Field(default_factory=list)
    used_memory_ids: list[str] = Field(default_factory=list)
    used_inside_joke_ids: list[str] = Field(default_factory=list)


def _normalize_style(value: Any) -> StyleName:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized == "humor":
        normalized = "humorous"
    if normalized not in {"professional", "humorous"}:
        normalized = "professional"
    return normalized  # type: ignore[return-value]


class AdaptiveStyleSelector:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None

    def select_style(
        self,
        post_caption: str,
        post_topic: str,
        target_comment: str,
        thread_context: list[str],
        other_user_comments: list[str],
        developer_instruction: str,
        developer_files_summary: str,
        inside_jokes: list[dict[str, Any]],
        memories: list[dict[str, Any]],
    ) -> StyleDecision:
        selector_input = StyleSelectorInput(
            post_caption=post_caption,
            post_topic=post_topic,
            target_comment=target_comment,
            thread_context=thread_context,
            other_user_comments=other_user_comments,
            developer_instruction=developer_instruction,
            developer_files_summary=developer_files_summary,
            inside_jokes=inside_jokes,
            memories=memories,
        )
        return self.select_style_from_input(selector_input)

    def select_style_from_input(self, selector_input: StyleSelectorInput) -> StyleDecision:
        payload = self._call_llm(selector_input)
        payload["chosen_style"] = _normalize_style(payload.get("chosen_style"))
        payload.setdefault("confidence", 0.5)
        payload.setdefault("estimated_reward", {"professional": 0.5, "humorous": 0.5})
        payload.setdefault("reason", "")
        payload.setdefault("risk_flags", [])
        payload.setdefault("used_memory_ids", [])
        payload.setdefault("used_inside_joke_ids", [])
        return StyleDecision(**payload)

    def _call_llm(self, selector_input: StyleSelectorInput) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is required for adaptive style selection")

        prompt = self._build_prompt(selector_input)
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return _json_from_text(response.choices[0].message.content or "{}")

    def _system_prompt(self) -> str:
        policy = load_policy_text()
        return f"""
You are an adaptive style selector for an Instagram agent testing project.
Your only job is to choose one reply style: professional or humorous.
Do not generate the final reply.
Do not use hard-coded style rules.
Use the full context provided by the developer.
The custom policy file below is authoritative. Choose the style that best follows this policy.

<policy_for_context>
{policy}
</policy_for_context>

Developer instruction has the highest priority.
Inside jokes are human-edited trusted context.
Memories are evidence, not hard rules.
Return only valid JSON.
""".strip()

    def _build_prompt(self, selector_input: StyleSelectorInput) -> str:
        context_json = selector_input.model_dump()
        return f"""
Choose the best style for the target comment.

Full context:
{json.dumps(context_json, ensure_ascii=False, indent=2)}

Return JSON with exactly these fields:
{{
  "chosen_style": "professional | humorous",
  "confidence": 0.0,
  "estimated_reward": {{
    "professional": 0.0,
    "humorous": 0.0
  }},
  "reason": "string",
  "risk_flags": [],
  "used_memory_ids": [],
  "used_inside_joke_ids": []
}}
""".strip()


def select_style(
    post_caption: str,
    post_topic: str,
    target_comment: str,
    thread_context: list[str],
    other_user_comments: list[str],
    developer_instruction: str,
    developer_files_summary: str,
    inside_jokes: list[dict[str, Any]],
    memories: list[dict[str, Any]],
) -> StyleDecision:
    return AdaptiveStyleSelector().select_style(
        post_caption=post_caption,
        post_topic=post_topic,
        target_comment=target_comment,
        thread_context=thread_context,
        other_user_comments=other_user_comments,
        developer_instruction=developer_instruction,
        developer_files_summary=developer_files_summary,
        inside_jokes=inside_jokes,
        memories=memories,
    )
