"""Video classifier: Shorts vs Full Videos.

Encapsulates the heuristic that decides whether a fetched video is a
YouTube Short (<= 60 s **or** URL contains ``/shorts/``) vs a regular
full-length video.
"""
from __future__ import annotations

from typing import Any, Dict, List


# Duration threshold in seconds
SHORT_MAX_DURATION: int = 60


def classify(video: Dict[str, Any]) -> str:
    """Return ``"Short"`` or ``"Video"`` for a single video metadata dict.

    Classification rules (evaluated in order):
        1. If the URL / ``webpage_url`` contains ``/shorts/`` → **Short**.
        2. If ``duration`` is present and ``<= 60`` seconds    → **Short**.
        3. Otherwise                                           → **Video**.
    """
    url = video.get("webpage_url") or video.get("url") or ""
    if isinstance(url, str) and "/shorts/" in url:
        return "Short"

    duration = video.get("duration")
    if duration is not None and isinstance(duration, (int, float)) and duration <= SHORT_MAX_DURATION:
        return "Short"

    return "Video"


def classify_batch(videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add a ``"type"`` key (``"Short"`` / ``"Video"``) to every dict in *videos*.

    Returns the same list (mutated in-place for efficiency).

    TODO: implement full pipeline integration (Phase 2 — backend).
    """
    for v in videos:
        v["type"] = classify(v)
    return videos
