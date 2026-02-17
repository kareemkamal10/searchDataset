"""Title and string cleaning utilities for matching logic.

Provides deterministic, UTF-8-safe cleaning for titles like:
'Amr Diab - Tamally Maak (Piano Cover by X)' -> 'Amr Diab Tamally Maak'
"""
from typing import Pattern
import re


# Patterns compiled once for performance
_BRACKETED: Pattern = re.compile(r"\[.*?\]|\(.*?\)")
_CLEAN_KEYWORDS: Pattern = re.compile(
    r"(?i)\b(cover|piano cover|piano|solo piano|official|audio|hd|hq|live|feat\.?|ft\.?|arrangement|version|lyrics|karaoke)\b"
)
_SEPARATORS: Pattern = re.compile(r"[-–—|_:]+")
_PUNCTUATION: Pattern = re.compile(r"[\"'\®\™\•\·,?]+")
_MULTI_SPACE: Pattern = re.compile(r"\s{2,}")


def clean_cover_title(title: str) -> str:
    """Clean a cover video title into a compact search-friendly string.

    Steps:
      - remove bracketed content (e.g. parentheses / square brackets)
      - remove common noise keywords (cover, piano, HQ, official, etc.)
      - normalize separators to spaces and collapse whitespace

    Args:
        title: raw video title (UTF-8)

    Returns:
        Cleaned string suitable as a search query for finding originals.
    """
    if not title:
        return ""
    s = title
    s = _BRACKETED.sub(" ", s)
    s = _CLEAN_KEYWORDS.sub(" ", s)
    s = _SEPARATORS.sub(" ", s)
    s = _PUNCTUATION.sub("", s)
    s = _MULTI_SPACE.sub(" ", s)
    return s.strip()
