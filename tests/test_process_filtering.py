import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import CommentAgent
from app.db import AuditRecord, SessionLocal, init_db
from app.schemas import AgentAction, AgentDecision, AgentDecisionOut, CommentCategory, InstagramComment


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
    agent.instagram = FakeInstagram(has_own_reply=True)
    agent._log = lambda db, comment, decision, applied, apply_error: None
    agent.llm.decide = lambda comment: AgentDecision(
        comment_id=comment.id,
        category=CommentCategory.other,
        action=AgentAction.reply_public,
        confidence=0.9,
        reply_text="reply",
        policy_summary="policy",
        reasoning="reason",
    )

    db = SessionLocal()
    try:
        db.add(
            AuditRecord(
                comment_id="old-comment",
                media_id="media",
                username="tester",
                text="old",
                category="other",
                action="reply_public",
                confidence=0.9,
                reply_text="reply",
                reasoning="reason",
                applied=True,
            )
        )
        db.commit()
        old_comment = InstagramComment(id="old-comment", text="old", media_id="media")
        new_comment = InstagramComment(id="new-comment", text="new", media_id="media")

        filtered = []
        for comment in [old_comment, new_comment]:
            if await agent.should_process_comment(db, comment):
                filtered.append(comment.id)

        assert filtered == ["new-comment"]

        agent.instagram = FakeInstagram(has_own_reply=False)
        filtered_after_deleted_reply = []
        for comment in [old_comment, new_comment]:
            if await agent.should_process_comment(db, comment):
                filtered_after_deleted_reply.append(comment.id)

        assert filtered_after_deleted_reply == ["old-comment", "new-comment"]

        output = AgentDecisionOut(
            **AgentDecision(
                comment_id="new-comment",
                category=CommentCategory.other,
                action=AgentAction.reply_public,
                confidence=0.9,
                reply_text="reply",
                policy_summary="policy",
                reasoning="reason",
            ).model_dump()
        ).model_dump()
        assert "category" not in output
    finally:
        db.close()

    print("process filtering tests passed")


if __name__ == "__main__":
    asyncio.run(main())
