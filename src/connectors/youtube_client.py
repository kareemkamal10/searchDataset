"""YouTube metadata fetcher using yt-dlp.

Provides a clean, testable `YouTubeFetcher` class that extracts metadata
for playlists/channels without downloading media.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import logging

from yt_dlp import YoutubeDL


@dataclass
class VideoItem:
    """Data transfer object for a YouTube video (cover).

    Attributes:
        video_id: YouTube video id (e.g. 'dQw4w9WgXcQ')
        cover_url: Full watch URL
        title: Original upload title (UTF-8)
        duration: Duration in seconds (may be None)
        thumbnail: URL to thumbnail image (may be None)
        selected: Whether the item is selected for export
        proposed_original_url: Optional auto-matched original URL
        proposed_original_title: Optional auto-matched original title
    """

    video_id: str
    cover_url: str
    title: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    selected: bool = True
    proposed_original_url: Optional[str] = None
    proposed_original_title: Optional[str] = None


class YouTubeFetcher:
    """Wrapper around `yt-dlp` to extract playlist/channel metadata.

    The class purposefully extracts metadata only (fast) and returns
    serializable dictionaries so the UI and processing layers remain decoupled.
    """

    def __init__(self, ydl_opts: Optional[Dict[str, Any]] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        default_opts = {
            "quiet": True,
            "skip_download": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            # use a general flat extract to support playlists and channels
            "extract_flat": True,
            "no_warnings": True,
        }
        if ydl_opts:
            default_opts.update(ydl_opts)
        self.ydl_opts = default_opts

    def get_playlist_videos(self, url: str, matcher=None) -> List[Dict[str, Any]]:
        """Return a list of video metadata dicts for a playlist or channel URL.

        Args:
            url: YouTube playlist or channel URL.

        Returns:
            A list of serializable dicts with keys: video_id, cover_url, title,
            duration, thumbnail, selected (default True).

        The method handles common errors gracefully and logs them. Empty or
        private/removed entries are skipped.
        """
        videos: List[Dict[str, Any]] = []
        try:
            with YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = info.get("entries") or []
                for entry in entries:
                    if not entry:
                        # private/removed videos appear as None when using extract_flat
                        self.logger.debug("Skipping empty/removed entry in playlist.")
                        continue
                    vid = entry.get("id") or entry.get("url")
                    if not vid:
                        self.logger.debug("Skipping entry without id/url: %s", entry)
                        continue

                    cover_url = f"https://www.youtube.com/watch?v={vid}"
                    title = entry.get("title") or entry.get("webpage_title") or ""
                    duration = entry.get("duration")  # may be None for flat extract
                    thumbnail = entry.get("thumbnail")

                    # detect shorts: prefer explicit '/shorts/' in webpage_url, otherwise short duration
                    webpage = entry.get("webpage_url") or entry.get("original_url") or ""
                    is_short = False
                    if isinstance(webpage, str) and "/shorts/" in webpage:
                        is_short = True
                    elif duration is not None and isinstance(duration, (int, float)) and duration < 60:
                        is_short = True

                    item = VideoItem(
                        video_id=vid,
                        cover_url=cover_url,
                        title=title,
                        duration=duration,
                        thumbnail=thumbnail,
                    )
                    v = asdict(item)
                    # attach match suggestion if matcher provided
                    v.setdefault("manual_override", "")
                    v.setdefault("selected", True)
                    v["is_short"] = is_short
                    if matcher is not None:
                        try:
                            match = matcher.find_original(title)
                            v["proposed_original_url"] = match.get("url")
                            v["proposed_original_title"] = match.get("title")
                            v["proposed_confidence"] = match.get("confidence")
                        except Exception:
                            v["proposed_original_url"] = ""
                            v["proposed_original_title"] = ""
                            v["proposed_confidence"] = "Low"

                    videos.append(v)
        except Exception as exc:  # keep broad but logged
            self.logger.exception("Failed to extract playlist videos for %s: %s", url, exc)
        return videos

    def get_video_metadata(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Fetch full metadata for a single video (safe, non-downloading).

        This is intentionally separate from `get_playlist_videos` to keep the
        fast-path lightweight.
        """
        try:
            with YoutubeDL({**self.ydl_opts, "extract_flat": False}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if not info:
                    return None
                # Normalize to the same DTO-like dict
                return {
                    "video_id": info.get("id"),
                    "cover_url": f"https://www.youtube.com/watch?v={info.get('id')}",
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                }
        except Exception as exc:
            self.logger.exception("get_video_metadata failed for %s: %s", video_url, exc)
            return None
