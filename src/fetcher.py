"""YouTube metadata fetcher using yt-dlp.

Wraps ``yt_dlp.YoutubeDL`` to extract playlist/channel metadata **without**
downloading any media.  Returns lightweight, serialisable dictionaries that
the classifier and matcher can consume independently.
"""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from yt_dlp import YoutubeDL

from src.utils import youtube_watch_url, format_duration

logger = logging.getLogger("Fetcher")

# Safe, metadata-only yt-dlp defaults
_DEFAULT_OPTS: Dict[str, Any] = {
    "quiet": True,
    "skip_download": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "extract_flat": "in_playlist",
    "no_warnings": True,
}


@dataclass
class VideoMeta:
    """Minimal data-transfer object for a single YouTube video."""

    video_id: str
    url: str
    title: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    upload_date: Optional[str] = None


class Fetcher:
    """Playlist / channel metadata extractor.

    Usage::

        fetcher = Fetcher()
        items = fetcher.fetch("https://www.youtube.com/playlist?list=...")
        # items is a list[dict] ready for classification & matching
    """

    def __init__(self, extra_opts: Optional[Dict[str, Any]] = None) -> None:
        self.opts = {**_DEFAULT_OPTS, **(extra_opts or {})}

    def fetch(self, url: str) -> List[Dict[str, Any]]:
        """Return a list of video metadata dicts for *url*.

        Each dict contains: video_id, url, title, duration, thumbnail,
        upload_date, webpage_url, selected, manual_override.

        Private/removed entries and entries without an id are silently skipped.
        """
        logger.info("Starting playlist/channel extraction for: %s", url)
        t0 = time.perf_counter()
        videos: List[Dict[str, Any]] = []

        try:
            with YoutubeDL(self.opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    logger.warning("yt-dlp returned None for: %s", url)
                    return []

                entries = info.get("entries") or []
                total = len(list(entries))  # entries can be a generator
                # re-extract since we consumed the generator
                entries = info.get("entries") or []
                logger.info("Found %d entries in response", total)

                for i, entry in enumerate(entries, start=1):
                    if not entry:
                        logger.debug("[%d/%d] Skipping empty/removed entry", i, total)
                        continue

                    vid = entry.get("id") or entry.get("url")
                    if not vid:
                        logger.debug("[%d/%d] Skipping entry without id: %s", i, total, entry.get("title", "?"))
                        continue

                    title = entry.get("title") or entry.get("webpage_title") or "(no title)"
                    duration = entry.get("duration")
                    thumbnail = entry.get("thumbnail") or entry.get("thumbnails", [{}])[0].get("url") if entry.get("thumbnails") else None
                    upload_date = entry.get("upload_date")
                    webpage_url = entry.get("webpage_url") or entry.get("original_url") or ""
                    watch_url = youtube_watch_url(vid)

                    dur_str = format_duration(duration)
                    logger.info(
                        "[%d/%d] \"%s\" — duration: %s",
                        i, total, title[:60], dur_str,
                    )

                    videos.append({
                        "video_id": vid,
                        "url": watch_url,
                        "webpage_url": webpage_url,
                        "title": title,
                        "duration": duration,
                        "thumbnail": thumbnail,
                        "upload_date": upload_date,
                        "selected": True,
                        "manual_override": "",
                    })

        except Exception as exc:
            logger.exception("Failed to extract videos for %s: %s", url, exc)

        elapsed = time.perf_counter() - t0
        logger.info("Fetch complete — %d videos extracted in %.1fs", len(videos), elapsed)
        return videos
