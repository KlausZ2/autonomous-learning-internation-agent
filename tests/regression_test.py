import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import CommentAgent
from app.db import AuditRecord, SessionLocal, init_db
from app.adaptive_style_selector import EstimatedReward, StyleDecision
from app.reply_generator import ReplyGenerationResult
from app.schemas import AgentAction, AgentDecision, CommentCategory, InstagramComment


class FakeStyleSelector:
    def select_style(self, **kwargs):
        return StyleDecision(
            chosen_style="humorous",
            confidence=0.8,
            estimated_reward=EstimatedReward(professional=0.2, humorous=0.8),
            reason="fake style decision",
            used_memory_ids=[],
            used_inside_joke_ids=[],
        )


class FakeReplyGenerator:
    def generate_reply(self, target_comment, context, chosen_style, inside_jokes):
        return ReplyGenerationResult(
            reply_text="fake reply",
            style=chosen_style,
            used_inside_joke_ids=[],
            reason="fake reply generation",
        )


class FakeInstagram:
    def __init__(self, has_own_reply=True):
        self.has_own_reply_value = has_own_reply

    async def has_own_reply(self, comment_id):
        return self.has_own_reply_value

    async def apply_action(self, comment_id, action, reply_text):
        return None


async def main():
    init_db()
    agent = CommentAgent()
    agent.style_selector = FakeStyleSelector()
    agent.reply_generator = FakeReplyGenerator()
    agent.instagram = FakeInstagram(has_own_reply=True)
    agent._log = lambda db, comment, decision, applied, apply_error: None

    delete_sample = InstagramComment(id="regression-delete", text="roast me a little")
    agent.llm.decide = lambda comment: AgentDecision(
        comment_id=comment.id,
        category=CommentCategory.other,
        action=AgentAction.delete,
        confidence=0.99,
        reply_text=None,
        policy_summary="test",
        reasoning="test",
        should_apply=True,
    )
    delete_decision = await agent.decide(delete_sample)
    assert delete_decision.action == AgentAction.reply_public
    assert delete_decision.reply_text

    db = SessionLocal()
    try:
        db.add(
            AuditRecord(
                comment_id="already-replied",
                media_id="media",
                username="tester",
                text="Tell me more",
                category="genuine_question",
                action="reply_public",
                confidence=0.95,
                reply_text="Sure!",
                reasoning="Existing successful reply.",
                applied=True,
            )
        )
        db.commit()

        comment = InstagramComment(id="already-replied", text="Tell me more", username="tester")
        agent.llm.decide = lambda comment: AgentDecision(
            comment_id=comment.id,
            category=CommentCategory.genuine_question,
            action=AgentAction.reply_public,
            confidence=0.99,
            reply_text="Sure!",
            policy_summary="test",
            reasoning="test",
            should_apply=True,
        )
        decision = await agent.process_comment(db, comment, auto_apply=True)
        assert decision.action == AgentAction.reply_public
        assert decision.should_apply is False
        assert await agent.should_process_comment(db, comment) is False

        agent.instagram = FakeInstagram(has_own_reply=False)
        assert await agent.should_process_comment(db, comment) is True

        follow_up = InstagramComment(
            id="follow-up-new-id",
            text="One more question",
            username="tester",
            parent_comment_id="already-replied",
        )
        follow_up_decision = await agent.process_comment(db, follow_up, auto_apply=False)
        assert follow_up_decision.action == AgentAction.reply_public
        assert follow_up_decision.should_apply is True
    finally:
        db.close()

    print("regression tests passed")


if __name__ == "__main__":
    asyncio.run(main())
