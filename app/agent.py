from sqlalchemy.orm import Session
from typing import Optional

from app.adaptive_style_selector import AdaptiveStyleSelector
from app.config import get_settings
from app.db import AuditRecord
from app.inside_jokes_loader import load_active_inside_jokes
from app.interaction_logger import log_interaction
from app.instagram import InstagramClient
from app.llm import LLMClient
from app.memory_store import load_active_memories
from app.reply_generator import ReplyGenerator
from app.schemas import AgentAction, AgentDecision, InstagramComment


class CommentAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = LLMClient()
        self.instagram = InstagramClient()
        self.style_selector = AdaptiveStyleSelector()
        self.reply_generator = ReplyGenerator()

    async def decide(self, comment: InstagramComment) -> AgentDecision:
        decision = self.llm.decide(comment)
        decision = self._apply_action_config(decision)
        if decision.action == AgentAction.reply_public:
            self._apply_adaptive_reply(comment, decision)
        return decision

    async def process_comment(
        self,
        db: Session,
        comment: InstagramComment,
        auto_apply: Optional[bool] = None,
    ) -> AgentDecision:
        decision = await self.decide(comment)
        should_apply = self.settings.auto_apply_actions if auto_apply is None else auto_apply
        applied = False
        apply_error = None

        if should_apply and decision.should_apply:
            if self._already_applied(db, comment.id, decision.action):
                decision.should_apply = False
                decision.reasoning += " This action was already applied to the same comment, so it was skipped."
            elif decision.action == AgentAction.reply_public and await self.instagram.has_own_reply(comment.id):
                decision.should_apply = False
                decision.reasoning += " This comment already has a reply from the configured Instagram account, so it was skipped."
            else:
                try:
                    await self.instagram.apply_action(comment.id, decision.action, decision.reply_text)
                    applied = True
                except Exception as exc:
                    apply_error = str(exc)

        self._log(db, comment, decision, applied, apply_error)
        return decision

    async def should_process_comment(self, db: Session, comment: InstagramComment) -> bool:
        if not self._already_applied(db, comment.id, AgentAction.reply_public):
            return True
        return not await self.instagram.has_own_reply(comment.id)

    def _apply_action_config(self, decision: AgentDecision) -> AgentDecision:
        if decision.action == AgentAction.delete and not self.settings.allow_delete_comments:
            self._force_reply(decision, "Delete is disabled by configuration.")
        if decision.action == AgentAction.delete and decision.confidence < self.settings.min_delete_confidence:
            self._force_reply(decision, "Delete confidence was below threshold.")
        if decision.action == AgentAction.hide and not self.settings.allow_hide_comments:
            self._force_reply(decision, "Hide is disabled by configuration.")
        if decision.action == AgentAction.hide and decision.confidence < self.settings.min_hide_confidence:
            self._force_reply(decision, "Hide confidence was below threshold.")
        if decision.action == AgentAction.ignore and not self.settings.allow_ignore_comments:
            self._force_reply(decision, "Ignore is disabled by configuration.")
        if decision.action == AgentAction.reply_public and not decision.reply_text:
            decision.reply_text = self.settings.default_reply_text
        return decision

    def _force_reply(self, decision: AgentDecision, reason: str) -> None:
        decision.action = AgentAction.reply_public
        if not decision.reply_text:
            decision.reply_text = self.settings.default_reply_text
        decision.reasoning += f" {reason} Reply-only mode converted the action to reply_public."

    def _apply_adaptive_reply(self, comment: InstagramComment, decision: AgentDecision) -> None:
        context = self._build_context(comment)
        inside_jokes = load_active_inside_jokes()
        memories = load_active_memories()
        style_decision = self.style_selector.select_style(
            post_caption=context["post_caption"],
            post_topic=context["post_topic"],
            target_comment=comment.text,
            thread_context=context["thread_context"],
            other_user_comments=context["other_user_comments"],
            developer_instruction=context["developer_instruction"],
            developer_files_summary=context["developer_files_summary"],
            inside_jokes=inside_jokes,
            memories=memories,
        )
        reply = self.reply_generator.generate_reply(
            target_comment=comment.text,
            context=context,
            chosen_style=style_decision.chosen_style,
            inside_jokes=inside_jokes,
        )
        decision.reply_text = reply.reply_text
        decision.chosen_style = style_decision.chosen_style
        decision.style_confidence = style_decision.confidence
        decision.estimated_reward = style_decision.estimated_reward.model_dump()
        decision.style_selection_reason = style_decision.reason
        decision.used_memory_ids = style_decision.used_memory_ids
        decision.used_inside_joke_ids = list(
            dict.fromkeys(style_decision.used_inside_joke_ids + reply.used_inside_joke_ids)
        )
        decision.reasoning += (
            f" Adaptive style selector chose {style_decision.chosen_style} "
            f"with confidence {style_decision.confidence:.2f}: {style_decision.reason}"
        )

    def _build_context(self, comment: InstagramComment) -> dict:
        return {
            "post_caption": "",
            "post_topic": "",
            "thread_context": [],
            "other_user_comments": [],
            "developer_instruction": self.settings.default_reply_tone,
            "developer_files_summary": "",
        }

    def _already_applied(self, db: Session, comment_id: str, action: AgentAction) -> bool:
        if action == AgentAction.ignore:
            return False
        return (
            db.query(AuditRecord)
            .filter(
                AuditRecord.comment_id == comment_id,
                AuditRecord.action == action.value,
                AuditRecord.applied.is_(True),
            )
            .first()
            is not None
        )

    def _log(
        self,
        db: Session,
        comment: InstagramComment,
        decision: AgentDecision,
        applied: bool,
        apply_error: Optional[str],
    ) -> None:
        record = AuditRecord(
            comment_id=comment.id,
            media_id=comment.media_id,
            username=comment.username,
            text=comment.text,
            category=decision.category.value,
            action=decision.action.value,
            confidence=decision.confidence,
            reply_text=decision.reply_text,
            reasoning=decision.reasoning,
            applied=applied,
            apply_error=apply_error,
        )
        db.add(record)
        db.commit()
        log_interaction(
            comment=comment,
            decision=decision,
            context=self._build_context(comment),
            applied=applied,
            apply_error=apply_error,
        )
