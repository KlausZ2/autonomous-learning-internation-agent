import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.reply_generator import ReplyGenerationInput, ReplyGenerator


class FakeReplyGenerator(ReplyGenerator):
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.prompts = []

    def generate_reply_from_input(self, generation_input: ReplyGenerationInput):
        self.prompts.append(self._build_prompt(generation_input))
        return super().generate_reply_from_input(generation_input)

    def _system_prompt(self) -> str:
        return super()._system_prompt()

    def _fallback_reply(self, generation_input: ReplyGenerationInput):
        return super()._fallback_reply(generation_input)


def test_fallback_professional_and_humorous_are_different():
    generator = ReplyGenerator()
    generator.client = None
    context = {
        "post_caption": "Test post",
        "thread_context": ["thread"],
        "developer_instruction": "test instruction",
    }
    professional = generator.generate_reply("What is this?", context, "professional", [])
    humorous = generator.generate_reply("What is this?", context, "humorous", [])
    assert professional.style == "professional"
    assert humorous.style == "humorous"
    assert professional.reply_text != humorous.reply_text


def test_prompt_includes_style_and_inside_jokes():
    generator = ReplyGenerator()
    generation_input = ReplyGenerationInput(
        target_comment="mystery meat?",
        chosen_style="humorous",
        inside_jokes=[{"joke_id": "joke_001", "meaning": "cafeteria joke"}],
        thread_context=["the tray fought back"],
        developer_instruction="use context",
    )
    prompt = generator._build_prompt(generation_input)
    assert '"chosen_style": "humorous"' in prompt
    assert "joke_001" in prompt
    assert "the tray fought back" in prompt


def test_system_prompt_includes_custom_policy():
    generator = ReplyGenerator()
    system_prompt = generator._system_prompt()
    assert "<policy_for_context>" in system_prompt
    assert "policy_for_context.txt" not in system_prompt
    policy_body = system_prompt.split("<policy_for_context>", 1)[1].split("</policy_for_context>", 1)[0].strip()
    assert len(policy_body) > 0


if __name__ == "__main__":
    test_fallback_professional_and_humorous_are_different()
    test_prompt_includes_style_and_inside_jokes()
    test_system_prompt_includes_custom_policy()
    print("reply generator tests passed")
