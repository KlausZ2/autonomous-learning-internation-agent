from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CommentCategory(str, Enum):
    genuine_question = "genuine_question"
    product_question = "product_question"
    generic_compliment = "generic_compliment"
    spam = "spam"
    suspicious_link = "suspicious_link"
    scam = "scam"
    harassment = "harassment"
    severe_harassment = "severe_harassment"
    complaint = "complaint"
    ambiguous_negative_feedback = "ambiguous_negative_feedback"
    other = "other"


class AgentAction(str, Enum):
    reply_public = "reply_public"
    ignore = "ignore"
    hide = "hide"
    delete = "delete"


class InstagramComment(BaseModel):
    id: str
    text: str
    username: Optional[str] = None
    timestamp: Optional[datetime] = None
    like_count: Optional[int] = None
    media_id: Optional[str] = None
    parent_comment_id: Optional[str] = None


class AgentDecision(BaseModel):
    comment_id: str
    category: CommentCategory
    action: AgentAction
    confidence: float = Field(ge=0.0, le=1.0)
    reply_text: Optional[str] = None
    policy_summary: str
    reasoning: str
    should_apply: bool = True
    chosen_style: Optional[str] = None
    style_confidence: Optional[float] = None
    estimated_reward: Optional[dict[str, float]] = None
    style_selection_reason: Optional[str] = None
    used_memory_ids: list[str] = Field(default_factory=list)
    used_inside_joke_ids: list[str] = Field(default_factory=list)


class AgentDecisionOut(BaseModel):
    comment_id: str
    action: AgentAction
    confidence: float = Field(ge=0.0, le=1.0)
    reply_text: Optional[str] = None
    policy_summary: str
    reasoning: str
    should_apply: bool = True
    chosen_style: Optional[str] = None
    style_confidence: Optional[float] = None
    estimated_reward: Optional[dict[str, float]] = None
    style_selection_reason: Optional[str] = None
    used_memory_ids: list[str] = Field(default_factory=list)
    used_inside_joke_ids: list[str] = Field(default_factory=list)


class DecideRequest(BaseModel):
    comment: InstagramComment
    auto_apply: Optional[bool] = None


class FeedbackRequest(BaseModel):
    interaction_id: str
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    label: Optional[str] = None
    note: str = ""


class TeachMemoryRequest(BaseModel):
    lesson: str
    style: str = "humorous"
    trigger: str = ""


class AuditRecordOut(BaseModel):
    id: int
    comment_id: str
    media_id: Optional[str]
    username: Optional[str]
    text: str
    category: str
    action: str
    confidence: float
    reply_text: Optional[str]
    reasoning: str
    applied: bool
    apply_error: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
