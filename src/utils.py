"""Helper functions: time formatting, regex patterns, and shared constants.

This module centralises reusable utilities so that fetcher, classifier, and
matcher can remain focused on their single responsibilities.
"""
from __future__ import annotations

import re
from typing import Pattern


# ---------------------------------------------------------------------------
# Regex patterns (compiled once for performance)
# ---------------------------------------------------------------------------

# Matches anything inside parentheses or square brackets, e.g. "(Piano Cover)"
BRACKETED: Pattern[str] = re.compile(r"\[.*?\]|\(.*?\)")

# Noise keywords commonly found in cover titles — case-insensitive word boundary
NOISE_KEYWORDS: Pattern[str] = re.compile(
    r"(?i)\b("
    r"piano\s*cover|cover|piano|synthesia|tutorial|instrumental|by\b.*"
    r"|arabic|music|lyrics|hq|hd|live|karaoke|official|audio|version"
    r"|arrangement|solo\s*piano|feat\.?|ft\.?"
    r")\b"
)

# Separators to normalise into spaces
SEPARATORS: Pattern[str] = re.compile(r"[-–—|_:]+")

# Stray punctuation to remove
PUNCTUATION: Pattern[str] = re.compile(r"[\"'\®\™\•\·,?!]+")

# Collapse multiple spaces
MULTI_SPACE: Pattern[str] = re.compile(r"\s{2,}")


# ---------------------------------------------------------------------------
# Title cleaning
# ---------------------------------------------------------------------------

def clean_cover_title(title: str) -> str:
    """Strip noise from a cover title to produce a clean search query.

    Pipeline:
        1. Remove bracketed content  →  "(Sad Piano Cover)" is gone
        2. Remove noise keywords      →  "Cover", "Synthesia", "Tutorial", etc.
        3. Normalise separators       →  dashes / pipes become spaces
        4. Strip punctuation          →  quotes, commas, etc.
        5. Collapse whitespace

    Example:
        >>> clean_cover_title("Amr Diab - Tamally Maak (Sad Piano Cover) by UserX")
        'Amr Diab Tamally Maak'
    """
    if not title:
        return ""
    s = BRACKETED.sub(" ", title)
    s = NOISE_KEYWORDS.sub(" ", s)
    s = SEPARATORS.sub(" ", s)
    s = PUNCTUATION.sub("", s)
    s = MULTI_SPACE.sub(" ", s)
    return s.strip()


# ---------------------------------------------------------------------------
# Duration formatting
# ---------------------------------------------------------------------------

def format_duration(seconds: int | float | None) -> str:
    """Convert seconds to a human-friendly MM:SS string.

    Returns ``"--:--"`` when *seconds* is ``None`` or negative.
    """
    if seconds is None or seconds < 0:
        return "--:--"
    seconds = int(seconds)
    mins, secs = divmod(seconds, 60)
    return f"{mins}:{secs:02d}"


def youtube_watch_url(video_id: str) -> str:
    """Build a canonical YouTube watch URL from a video id."""
    return f"https://www.youtube.com/watch?v={video_id}"
