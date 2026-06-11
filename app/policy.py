from pathlib import Path

from app.config import get_settings


def load_policy_text() -> str:
    settings = get_settings()
    path = Path(settings.policy_file)
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")
    return path.read_text(encoding="utf-8").strip()

