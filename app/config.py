from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-nano"

    meta_access_token: str = ""
    ig_business_account_id: str = ""
    ig_username: str = ""
    fb_page_id: str = ""
    meta_graph_version: str = "v25.0"

    database_url: str = "sqlite:///./instagram_agent.db"
    policy_file: str = "policy/policy_for_context.txt"
    memory_store_file: str = "memory_store.jsonl"
    inside_jokes_file: str = "inside_jokes_database.jsonl"
    interactions_file: str = "interactions.jsonl"
    auto_apply_actions: bool = False
    allow_delete_comments: bool = False
    allow_hide_comments: bool = False
    allow_ignore_comments: bool = False
    min_delete_confidence: float = 0.95
    min_hide_confidence: float = 0.80
    comment_poll_interval_seconds: int = 60
    default_reply_tone: str = "casual, playful, irreverent, and mildly edgy"
    default_reply_text: str = "lol noted"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
