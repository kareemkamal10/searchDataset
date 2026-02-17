"""Project configuration constants for Maqam-Matcher.

Keep only small, safe defaults here (no secrets).
All strings are UTF-8 friendly to support Arabic titles.
"""

from typing import List, Dict

# Keywords used by the matcher / filters (case-insensitive patterns)
SEARCH_PATTERNS: Dict[str, List[str]] = {
    "COVER_KEYWORDS": ["cover", "piano cover", "piano", "solo piano", "arrangement"],
    "EXCLUDE_KEYWORDS": ["violin", "orchestra", "karaoke", "backing track", "saxophone", "guitar"],
}

# If any of these words appear in the title/description we consider the video as NOT piano-only
STRICT_FILTER_KEYWORDS: List[str] = ["violin", "orchestra", "vocals", "singer", "karaoke"]

# Default yt-dlp options used by the YouTube client (safe and metadata-only)
DEFAULT_YTDLP_OPTS: dict = {
    "quiet": True,
    "skip_download": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "extract_flat": "in_playlist",
    "no_warnings": True,
}

# CSV output path
DATASET_OUTPUT_PATH = "data/dataset_output.csv"
