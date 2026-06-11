import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adaptive_style_selector import AdaptiveStyleSelector, StyleSelectorInput


class FakeSelector(AdaptiveStyleSelector):
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.prompts = []

    def _call_llm(self, selector_input: StyleSelectorInput) -> dict[str, Any]:
        self.prompts.append(self._build_prompt(selector_input))
        return self.payload


def sample_input(**overrides):
    data = {
        "post_caption": "A chaotic cafeteria lunch post.",
        "post_topic": "school lunch",
        "target_comment": "what is that mystery meat",
        "thread_context": ["someone said it looked like a science project"],
        "other_user_comments": ["bro that tray fought back"],
        "developer_instruction": "Prefer a humorous style for this test.",
        "developer_files_summary": "The project is testing adaptive style selection.",
        "inside_jokes": [
            {
                "joke_id": "joke_001",
                "trigger_phrases": ["mystery meat"],
                "preferred_style": "humorous",
            }
        ],
        "memories": [
            {
                "memory_id": "mem_001",
                "style": "humorous",
                "lesson": "Cafeteria jokes worked well before.",
            }
        ],
    }
    data.update(overrides)
    return StyleSelectorInput(**data)


def test_empty_memory_and_inside_jokes_still_returns_valid_decision():
    selector = FakeSelector(
        {
            "chosen_style": "professional",
            "confidence": 0.7,
            "estimated_reward": {"professional": 0.7, "humorous": 0.3},
            "reason": "Developer context asks for a clean response.",
            "risk_flags": [],
            "used_memory_ids": [],
            "used_inside_joke_ids": [],
        }
    )
    decision = selector.select_style_from_input(sample_input(inside_jokes=[], memories=[]))
    assert decision.chosen_style == "professional"
    assert decision.estimated_reward.professional == 0.7


def test_prompt_contains_full_context_fields():
    selector = FakeSelector(
        {
            "chosen_style": "humorous",
            "confidence": 0.8,
            "estimated_reward": {"professional": 0.2, "humorous": 0.8},
            "reason": "The thread is playful.",
            "risk_flags": [],
            "used_memory_ids": ["mem_001"],
            "used_inside_joke_ids": ["joke_001"],
        }
    )
    selector.select_style_from_input(sample_input())
    prompt = selector.prompts[0]
    assert "post_caption" in prompt
    assert "target_comment" in prompt
    assert "thread_context" in prompt
    assert "other_user_comments" in prompt
    assert "developer_instruction" in prompt
    assert "developer_files_summary" in prompt
    assert "inside_jokes" in prompt
    assert "memories" in prompt


def test_style_output_is_normalized_and_validated():
    selector = FakeSelector(
        {
            "chosen_style": "humor",
            "confidence": 0.9,
            "estimated_reward": {"professional": 0.1, "humorous": 0.9},
            "reason": "The comment is playful.",
        }
    )
    decision = selector.select_style_from_input(sample_input())
    assert decision.chosen_style == "humorous"
    assert decision.risk_flags == []


def test_system_prompt_includes_custom_policy():
    selector = AdaptiveStyleSelector()
    system_prompt = selector._system_prompt()
    assert "<policy_for_context>" in system_prompt
    policy_body = system_prompt.split("<policy_for_context>", 1)[1].split("</policy_for_context>", 1)[0].strip()
    assert len(policy_body) > 0


if __name__ == "__main__":
    test_empty_memory_and_inside_jokes_still_returns_valid_decision()
    test_prompt_contains_full_context_fields()
    test_style_output_is_normalized_and_validated()
    test_system_prompt_includes_custom_policy()
    print("adaptive style selector tests passed")
