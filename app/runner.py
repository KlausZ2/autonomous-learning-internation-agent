import asyncio
from datetime import datetime
from typing import Optional

from app.agent import CommentAgent
from app.config import get_settings
from app.db import SessionLocal
from app.instagram import InstagramClient


class AutoRunState:
    def __init__(self) -> None:
        self.media_id: Optional[str] = None
        self.auto_apply: bool = True
        self.interval_seconds: int = get_settings().comment_poll_interval_seconds
        self.running: bool = False
        self.last_started_at: Optional[datetime] = None
        self.last_run_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.total_runs: int = 0
        self.total_comments_seen: int = 0

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "media_id": self.media_id,
            "auto_apply": self.auto_apply,
            "interval_seconds": self.interval_seconds,
            "last_started_at": self.last_started_at.isoformat() if self.last_started_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_error": self.last_error,
            "total_runs": self.total_runs,
            "total_comments_seen": self.total_comments_seen,
        }


class AutoRunner:
    def __init__(self, agent: CommentAgent, instagram: InstagramClient) -> None:
        self.agent = agent
        self.instagram = instagram
        self.state = AutoRunState()
        self._task: Optional[asyncio.Task] = None

    def start(self, media_id: str, auto_apply: bool = True, interval_seconds: Optional[int] = None) -> dict:
        if self._task and not self._task.done():
            self.stop()

        self.state.media_id = media_id
        self.state.auto_apply = auto_apply
        self.state.interval_seconds = max(10, interval_seconds or get_settings().comment_poll_interval_seconds)
        self.state.running = True
        self.state.last_started_at = datetime.utcnow()
        self.state.last_error = None
        self._task = asyncio.create_task(self._loop())
        return self.state.to_dict()

    def stop(self) -> dict:
        self.state.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        return self.state.to_dict()

    async def run_once(self) -> None:
        if not self.state.media_id:
            return

        db = SessionLocal()
        try:
            comments = await self.instagram.list_comments_with_replies(self.state.media_id)
            self.state.total_comments_seen += len(comments)
            for comment in comments:
                if not await self.agent.should_process_comment(db, comment):
                    continue
                await self.agent.process_comment(db, comment, auto_apply=self.state.auto_apply)
            self.state.total_runs += 1
            self.state.last_run_at = datetime.utcnow()
            self.state.last_error = None
        except Exception as exc:
            self.state.last_error = str(exc)
        finally:
            db.close()

    async def _loop(self) -> None:
        while self.state.running:
            await self.run_once()
            await asyncio.sleep(self.state.interval_seconds)
