from typing import Any, Optional

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.schemas import AgentAction, InstagramComment


class InstagramClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = f"https://graph.facebook.com/{self.settings.meta_graph_version}"

    def _params(self, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        params = {"access_token": self.settings.meta_access_token}
        if extra:
            params.update(extra)
        return params

    async def list_media(self) -> list[dict[str, Any]]:
        path = f"{self.base_url}/{self.settings.ig_business_account_id}/media"
        params = self._params({"fields": "id,caption,comments_count,media_type,permalink,timestamp"})
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(path, params=params)
            self._raise_graph_error(response)
            return response.json().get("data", [])

    async def list_comments(self, media_id: str) -> list[InstagramComment]:
        path = f"{self.base_url}/{media_id}/comments"
        params = self._params({"fields": "id,text,username,timestamp,like_count"})
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(path, params=params)
            self._raise_graph_error(response)
            comments = response.json().get("data", [])
        return [InstagramComment(**item, media_id=media_id) for item in comments]

    async def list_replies(self, comment_id: str, media_id: Optional[str] = None) -> list[InstagramComment]:
        path = f"{self.base_url}/{comment_id}/replies"
        params = self._params({"fields": "id,text,username,timestamp,like_count"})
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(path, params=params)
            self._raise_graph_error(response)
            replies = response.json().get("data", [])
        return [
            InstagramComment(**item, media_id=media_id, parent_comment_id=comment_id)
            for item in replies
        ]

    async def list_comments_with_replies(self, media_id: str) -> list[InstagramComment]:
        comments = await self.list_comments(media_id)
        all_comments = list(comments)
        for comment in comments:
            replies = await self.list_replies(comment.id, media_id=media_id)
            all_comments.extend(self._filter_own_comments(replies))
        return self._filter_own_comments(all_comments)

    def _filter_own_comments(self, comments: list[InstagramComment]) -> list[InstagramComment]:
        own_username = self.settings.ig_username.strip().lower()
        if not own_username:
            return comments
        return [
            comment
            for comment in comments
            if (comment.username or "").strip().lower() != own_username
        ]

    async def has_own_reply(self, comment_id: str) -> bool:
        own_username = self.settings.ig_username.strip().lower()
        if not own_username:
            return False
        try:
            replies = await self.list_replies(comment_id)
        except HTTPException:
            return False
        return any((reply.username or "").strip().lower() == own_username for reply in replies)

    async def apply_action(
        self,
        comment_id: str,
        action: AgentAction,
        reply_text: Optional[str] = None,
    ) -> None:
        if action == AgentAction.ignore:
            return
        if action == AgentAction.reply_public:
            if not reply_text:
                raise ValueError("reply_public requires reply_text")
            await self.reply_to_comment(comment_id, reply_text)
            return
        if action == AgentAction.hide:
            await self.hide_comment(comment_id)
            return
        if action == AgentAction.delete:
            await self.delete_comment(comment_id)
            return
        raise ValueError(f"Unsupported action: {action}")

    async def reply_to_comment(self, comment_id: str, message: str) -> None:
        path = f"{self.base_url}/{comment_id}/replies"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(path, data=self._params({"message": message}))
            self._raise_graph_error(response)

    async def hide_comment(self, comment_id: str) -> None:
        path = f"{self.base_url}/{comment_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(path, data=self._params({"hide": "true"}))
            self._raise_graph_error(response)

    async def delete_comment(self, comment_id: str) -> None:
        path = f"{self.base_url}/{comment_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(path, params=self._params())
            self._raise_graph_error(response)

    def _raise_graph_error(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            detail = response.json()
        except ValueError:
            detail = {"error": response.text}
        raise HTTPException(status_code=response.status_code, detail=detail)
