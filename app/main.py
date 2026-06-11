from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.agent import CommentAgent
from app.db import AuditRecord, get_db, init_db
from app.feedback_collector import list_interactions, record_feedback
from app.instagram import InstagramClient
from app.memory_consolidator import consolidate_memories
from app.memory_store import load_active_memories
from app.policy import load_policy_text
from app.reflection_writer import write_manual_memory
from app.runner import AutoRunner
from app.schemas import AgentDecisionOut, AuditRecordOut, DecideRequest, FeedbackRequest, TeachMemoryRequest

app = FastAPI(title="Instagram Comment Agent", version="0.1.0")
agent = CommentAgent()
instagram = InstagramClient()
auto_runner = AutoRunner(agent, instagram)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse("app/static/dashboard.html")


@app.get("/policy")
def get_policy() -> dict[str, str]:
    return {"policy": load_policy_text()}


@app.get("/memory")
def get_memory():
    return {"data": load_active_memories()}


@app.get("/interactions")
def get_interactions(limit: int = 50):
    return {"data": list_interactions(limit=limit)}


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    try:
        return record_feedback(
            interaction_id=request.interaction_id,
            rating=request.rating,
            label=request.label,
            note=request.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/memory/teach")
def teach_memory(request: TeachMemoryRequest):
    return write_manual_memory(
        lesson=request.lesson,
        style=request.style,
        trigger=request.trigger,
    )


@app.post("/memory/consolidate")
def consolidate_memory():
    return consolidate_memories()


@app.post("/agent/decide")
async def decide(request: DecideRequest, db: Session = Depends(get_db)):
    decision = await agent.process_comment(db, request.comment, request.auto_apply)
    return AgentDecisionOut(**decision.model_dump())


@app.post("/instagram/sync-media")
async def sync_media():
    return {"data": await instagram.list_media()}


@app.post("/instagram/process-media/{media_id}")
async def process_media(media_id: str, auto_apply: bool = False, db: Session = Depends(get_db)):
    comments = await instagram.list_comments_with_replies(media_id)
    decisions = []
    skipped = 0
    for comment in comments:
        if not await agent.should_process_comment(db, comment):
            skipped += 1
            continue
        decision = await agent.process_comment(db, comment, auto_apply=auto_apply)
        decisions.append(AgentDecisionOut(**decision.model_dump()))
    return {
        "media_id": media_id,
        "seen": len(comments),
        "processed": len(decisions),
        "skipped_already_replied": skipped,
        "decisions": decisions,
    }


@app.post("/instagram/auto-run/{media_id}/start")
async def start_auto_run(media_id: str, auto_apply: bool = True, interval_seconds: Optional[int] = None):
    return auto_runner.start(media_id, auto_apply=auto_apply, interval_seconds=interval_seconds)


@app.post("/instagram/auto-run/stop")
async def stop_auto_run():
    return auto_runner.stop()


@app.get("/instagram/auto-run/status")
async def auto_run_status():
    return auto_runner.state.to_dict()


@app.get("/audit", response_model=list[AuditRecordOut])
def list_audit(db: Session = Depends(get_db)):
    return db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).limit(200).all()
