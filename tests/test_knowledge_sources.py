import json
import sys
from tempfile import TemporaryDirectory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.inside_jokes_loader import load_active_inside_jokes
from app.interaction_logger import log_interaction
from app.memory_store import load_active_memories
from app.schemas import AgentAction, AgentDecision, CommentCategory, InstagramComment


def test_empty_jsonl_sources_load_as_empty_lists(tmp_path):
    memory_path = tmp_path / "memory_store.jsonl"
    jokes_path = tmp_path / "inside_jokes_database.jsonl"
    memory_path.write_text("", encoding="utf-8")
    jokes_path.write_text("", encoding="utf-8")

    assert load_active_memories(str(memory_path)) == []
    assert load_active_inside_jokes(str(jokes_path)) == []


def test_inside_jokes_loader_reads_only_active_records(tmp_path):
    jokes_path = tmp_path / "inside_jokes_database.jsonl"
    jokes_path.write_text(
        "\n".join(
            [
                json.dumps({"joke_id": "joke_001", "status": "active"}),
                json.dumps({"joke_id": "joke_002", "status": "disabled"}),
            ]
        ),
        encoding="utf-8",
    )

    jokes = load_active_inside_jokes(str(jokes_path))
    assert [joke["joke_id"] for joke in jokes] == ["joke_001"]


def test_inside_jokes_loader_accepts_multiline_records(tmp_path):
    jokes_path = tmp_path / "inside_jokes_database.jsonl"
    jokes_path.write_text(
        """{
  "joke_id": "joke_001",
  "trigger_phrases": ["milk dragon"],
  "status": "active"
}

{
  "joke_id": "joke_002",
  "trigger_phrases": ["cafeteria"],
  "status": "active"
}
""",
        encoding="utf-8",
    )

    jokes = load_active_inside_jokes(str(jokes_path))
    assert [joke["joke_id"] for joke in jokes] == ["joke_001", "joke_002"]


def test_interaction_logger_writes_complete_jsonl_record(tmp_path):
    path = tmp_path / "interactions.jsonl"
    comment = InstagramComment(id="c1", media_id="m1", text="tell me more", username="tester")
    decision = AgentDecision(
        comment_id="c1",
        category=CommentCategory.genuine_question,
        action=AgentAction.reply_public,
        confidence=0.9,
        reply_text="sure",
        policy_summary="policy",
        reasoning="reason",
        chosen_style="humorous",
        style_confidence=0.8,
        estimated_reward={"professional": 0.2, "humorous": 0.8},
        style_selection_reason="thread is playful",
        used_memory_ids=["mem_001"],
        used_inside_joke_ids=["joke_001"],
    )
    context = {
        "post_caption": "caption",
        "post_topic": "topic",
        "thread_context": ["thread"],
        "other_user_comments": ["other"],
        "developer_instruction": "instruction",
        "developer_files_summary": "files",
    }

    record = log_interaction(comment, decision, context, applied=True, apply_error=None, path=str(path))
    saved = json.loads(path.read_text(encoding="utf-8").strip())

    assert saved["interaction_id"] == record["interaction_id"]
    assert saved["comment_id"] == "c1"
    assert saved["chosen_style"] == "humorous"
    assert saved["used_memory_ids"] == ["mem_001"]
    assert saved["used_inside_joke_ids"] == ["joke_001"]
    assert saved["feedback"] is None
    assert saved["reward"] is None


if __name__ == "__main__":
    with TemporaryDirectory() as temp_dir:
        test_empty_jsonl_sources_load_as_empty_lists(Path(temp_dir))
    with TemporaryDirectory() as temp_dir:
        test_inside_jokes_loader_reads_only_active_records(Path(temp_dir))
    with TemporaryDirectory() as temp_dir:
        test_inside_jokes_loader_accepts_multiline_records(Path(temp_dir))
    with TemporaryDirectory() as temp_dir:
        test_interaction_logger_writes_complete_jsonl_record(Path(temp_dir))
    print("knowledge source tests passed")
