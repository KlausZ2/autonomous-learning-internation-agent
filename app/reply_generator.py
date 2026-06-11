import json
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.llm import _json_from_text
from app.policy import load_policy_text


ReplyStyle = Literal["professional", "humorous"]


class ReplyGenerationInput(BaseModel):
    target_comment: str
    post_caption: str = ""
    post_topic: str = ""
    thread_context: list[str] = []
    other_user_comments: list[str] = []
    developer_instruction: str = ""
    developer_files_summary: str = ""
    chosen_style: ReplyStyle
    inside_jokes: list[dict[str, Any]] = []


class ReplyGenerationResult(BaseModel):
    reply_text: str
    style: ReplyStyle
    used_inside_joke_ids: list[str] = []
    reason: str = ""


class ReplyGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None

    def generate_reply(
        self,
        target_comment: str,
        context: dict[str, Any],
        chosen_style: ReplyStyle,
        inside_jokes: list[dict[str, Any]],
    ) -> ReplyGenerationResult:
        generation_input = ReplyGenerationInput(
            target_comment=target_comment,
            post_caption=context.get("post_caption", ""),
            post_topic=context.get("post_topic", ""),
            thread_context=context.get("thread_context", []),
            other_user_comments=context.get("other_user_comments", []),
            developer_instruction=context.get("developer_instruction", ""),
            developer_files_summary=context.get("developer_files_summary", ""),
            chosen_style=chosen_style,
            inside_jokes=inside_jokes,
        )
        return self.generate_reply_from_input(generation_input)

    def generate_reply_from_input(self, generation_input: ReplyGenerationInput) -> ReplyGenerationResult:
        if not self.client:
            return self._fallback_reply(generation_input)

        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._build_prompt(generation_input)},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        payload = _json_from_text(response.choices[0].message.content or "{}")
        payload.setdefault("style", generation_input.chosen_style)
        payload.setdefault("used_inside_joke_ids", [])
        payload.setdefault("reason", "")
        if not payload.get("reply_text"):
            payload["reply_text"] = self._fallback_reply(generation_input).reply_text
        return ReplyGenerationResult(**payload)

    def _system_prompt(self) -> str:
        policy = load_policy_text()
        return f"""
You generate Instagram comment replies for a controlled agent testing project.
Use the chosen_style exactly as provided.
The custom policy file below is authoritative for wording, tone, priorities, and boundaries.
You must follow this policy when writing the final reply. If the style and policy conflict, the policy wins.

<policy_for_context>
{policy}
</policy_for_context>

Professional replies should be factual, helpful, and clear.
Humorous replies should be short, light, friendly, context-aware, and may use relevant inside jokes.
Only use inside jokes when they naturally fit.
Do not add new inside jokes to the inside joke database.
Return only valid JSON.
""".strip()

    def _build_prompt(self, generation_input: ReplyGenerationInput) -> str:
        return f"""
Generate one public Instagram reply.

Context:
{json.dumps(generation_input.model_dump(), ensure_ascii=False, indent=2)}

Return JSON:
{{
  "reply_text": "string",
  "style": "{generation_input.chosen_style}",
  "used_inside_joke_ids": [],
  "reason": "string"
}}
""".strip()

    def _fallback_reply(self, generation_input: ReplyGenerationInput) -> ReplyGenerationResult:
        if generation_input.chosen_style == "professional":
            reply = "Thanks for asking. I can share more details soon."
        else:
            reply = self.settings.default_reply_text
        return ReplyGenerationResult(
            reply_text=reply,
            style=generation_input.chosen_style,
            used_inside_joke_ids=[],
            reason="Fallback reply generator was used.",
        )
