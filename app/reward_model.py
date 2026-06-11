from typing import Optional


def score_feedback(rating: Optional[int] = None, label: Optional[str] = None) -> float:
    if rating is not None:
        clamped = max(1, min(5, rating))
        return round((clamped - 3) / 2, 2)

    normalized = (label or "").strip().lower()
    scores = {
        "great": 1.0,
        "good": 0.6,
        "ok": 0.0,
        "neutral": 0.0,
        "bad": -0.6,
        "terrible": -1.0,
    }
    return scores.get(normalized, 0.0)
