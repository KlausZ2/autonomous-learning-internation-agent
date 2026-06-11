import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.feedback_collector import list_interactions, record_feedback
from app.jsonl_store import append_jsonl, read_jsonl
from app.memory_consolidator import consolidate_memories
from app.reflection_writer import write_manual_memory
from app.reward_model import score_feedback


def sample_interaction(interaction_id: str = "int_test") -> dict:
    return {
        "interaction_id": interaction_id,
        "timestamp": "2026-06-01T00:00:00",
        "post_id": "media",
        "comment_id": "comment",
        "target_comment": "milk dragon?",
        "generated_reply": "only if it passes the vibe check",
        "chosen_style": "humorous",
        "used_inside_joke_ids": ["joke_001"],
        "feedback": None,
        "reward": None,
        "reflection_id": None,
    }


def test_score_feedback_maps_rating_and_label():
    assert score_feedback(rating=5) == 1.0
    assert score_feedback(rating=1) == -1.0
    assert score_feedback(label="good") == 0.6
    assert score_feedback(label="terrible") == -1.0
    assert score_feedback(label="unknown") == 0.0


def test_record_feedback_updates_interaction_and_writes_memory(tmp_path):
    interactions_path = tmp_path / "interactions.jsonl"
    memory_path = tmp_path / "memory_store.jsonl"
    append_jsonl(str(interactions_path), sample_interaction())

    result = record_feedback(
        "int_test",
        rating=5,
        note="This matched the desired tone.",
        path=str(interactions_path),
        memory_path=str(memory_path),
    )

    records = read_jsonl(str(interactions_path))
    memories = read_jsonl(str(memory_path))
    assert result["reward"] == 1.0
    assert records[0]["feedback"]["rating"] == 5
    assert records[0]["reflection_id"] == memories[0]["memory_id"]
    assert "repeat this pattern" in memories[0]["lesson"]


def test_neutral_feedback_does_not_write_memory(tmp_path):
    interactions_path = tmp_path / "interactions.jsonl"
    memory_path = tmp_path / "memory_store.jsonl"
    append_jsonl(str(interactions_path), sample_interaction())

    result = record_feedback(
        "int_test",
        rating=3,
        path=str(interactions_path),
        memory_path=str(memory_path),
    )

    assert result["reward"] == 0.0
    assert result["reflection"] is None
    assert read_jsonl(str(memory_path)) == []


def test_list_interactions_returns_newest_first(tmp_path):
    interactions_path = tmp_path / "interactions.jsonl"
    append_jsonl(str(interactions_path), sample_interaction("old"))
    append_jsonl(str(interactions_path), sample_interaction("new"))

    records = list_interactions(limit=2, path=str(interactions_path))
    assert [record["interaction_id"] for record in records] == ["new", "old"]


def test_manual_memory_writer(tmp_path):
    memory_path = tmp_path / "memory_store.jsonl"
    memory = write_manual_memory(
        "Use short Chinese replies for casual Chinese comments.",
        style="humorous",
        trigger="中文评论",
        path=str(memory_path),
    )
    saved = read_jsonl(str(memory_path))
    assert saved[0]["memory_id"] == memory["memory_id"]
    assert saved[0]["source"] == "manual_teaching"


def test_memory_consolidator_marks_duplicate_active_records(tmp_path):
    memory_path = tmp_path / "memory_store.jsonl"
    first = write_manual_memory("same lesson", style="humorous", trigger="same", path=str(memory_path))
    second = write_manual_memory("same lesson", style="humorous", trigger="same", path=str(memory_path))

    result = consolidate_memories(str(memory_path))
    saved = read_jsonl(str(memory_path))
    assert first["memory_id"] != second["memory_id"]
    assert result["superseded"] == 1
    assert [record["status"] for record in saved] == ["active", "superseded"]


if __name__ == "__main__":
    test_score_feedback_maps_rating_and_label()
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        test_record_feedback_updates_interaction_and_writes_memory(root / "positive")
        test_neutral_feedback_does_not_write_memory(root / "neutral")
        test_list_interactions_returns_newest_first(root / "list")
        test_manual_memory_writer(root / "manual")
        test_memory_consolidator_marks_duplicate_active_records(root / "consolidate")
    print("feedback learning tests passed")
