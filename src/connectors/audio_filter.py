"""Simple heuristic-based audio filter helpers.

This module provides an optional metadata/title-based check to guess whether a
video is likely a "piano-only" cover. This is a lightweight first-pass filter
and should be complemented with an audio-analysis pipeline for production use.
"""
from typing import Iterable
import re


INSTRUMENT_KEYWORDS = [
    "violin",
    "guitar",
    "saxophone",
    "drum",
    "orchestra",
    "choir",
    "vocal",
    "singer",
    "flute",
]


def is_likely_piano_only(title: str, remove_case: bool = True) -> bool:
    """Heuristic: returns True when title does not mention other instruments.

    This is not authoritative — it looks for negative signals (instrument names,
    "feat.", "ft.", "vocals", etc.) in the title/description.
    """
    if not title:
        return False
    t = title.lower() if remove_case else title
    # If any excluded instrument appears, assume NOT piano-only
    for kw in INSTRUMENT_KEYWORDS:
        if kw in t:
            return False
    # If title explicitly contains "piano" or "piano cover", prefer True
    if "piano" in t:
        return True
    # fallback conservative decision
    return False
