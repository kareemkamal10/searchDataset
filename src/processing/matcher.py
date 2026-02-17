"""Heuristic song matcher: clean titles and find probable originals on YouTube.

This implementation prefers `ytmusicapi` when available (searching YouTube
Music results) and falls back to `youtubesearchpython` when needed.
"""
from __future__ import annotations

from typing import Dict, Optional, Callable, Any
import logging

from src.processing.string_cleaner import clean_cover_title


class SongMatcher:
    """Provide cleaning + search helpers to map cover titles -> original tracks.

    The matcher cleans the cover title aggressively, searches a backend and
    scores the top candidates by preferring official channels and excluding
    other covers.
    """

    def __init__(self, search_client: Optional[Callable[..., Any]] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.search_client = search_client

    def clean_title(self, title: str) -> str:
        return clean_cover_title(title)

    def _score(self, query_tokens, cand_title: str, cand_channel: str) -> int:
        score = 0
        t = (cand_title or "").lower()
        ch = (cand_channel or "").lower()
        if any(k in t for k in ("official", "audio", "video")):
            score += 3
        if "vevo" in ch or "official" in ch:
            score += 2
        # token overlap
        tokens = set(self.clean_title(cand_title).lower().split())
        score += sum(1 for q in query_tokens if q in tokens)
        # reject covers
        if any(x in t for x in ("cover", "piano")):
            score -= 10
        return score

    def find_original(self, raw_title: str) -> Dict[str, Optional[str]]:
        cleaned = self.clean_title(raw_title)
        if not cleaned:
            return {"url": "", "title": "", "confidence": "Low"}

        # Prepare search client lazily
        results = []
        try:
            if self.search_client is None:
                try:
                    from ytmusicapi import YTMusic  # type: ignore
                    ytm = YTMusic()
                    # YTMusic.search returns a list of dicts
                    results = ytm.search(cleaned, limit=5)
                except Exception:
                    # fallback to youtubesearchpython
                    try:
                        from youtubesearchpython import VideosSearch  # type: ignore
                        vs = VideosSearch(cleaned, limit=5)
                        results = vs.result().get("result", [])
                    except Exception as imp_exc:
                        self.logger.exception("No search backend available: %s", imp_exc)
                        return {"url": "", "title": "", "confidence": "Low"}
            else:
                # user provided a custom search client
                client = self.search_client
                res = client(cleaned, limit=5)
                results = res.result().get("result", [])
        except Exception as exc:
            self.logger.exception("search failed for %s: %s", cleaned, exc)
            return {"url": "", "title": "", "confidence": "Low"}

        # Normalize results into a common shape and score top candidates
        best = None
        best_score = -999
        q_tokens = [t.lower() for t in cleaned.split() if t]
        for r in results[:5]:
            # ytmusicapi result shape differs; try to extract fields safely
            title = r.get("title") or r.get("videoTitle") or r.get("name") or ""
            channel = ""
            if "artists" in r and isinstance(r.get("artists"), list) and r.get("artists"):
                channel = r.get("artists")[0].get("name", "")
            channel = channel or r.get("channel") or (r.get("author") and r.get("author").get("name")) or ""
            # skip covers
            if any(x in (title or "").lower() for x in ("cover", "piano")):
                continue
            score = self._score(q_tokens, title, channel)
            if score > best_score:
                best_score = score
                best = {"title": title, "channel": channel, "raw": r}

        if not best:
            return {"url": "", "title": "", "confidence": "Low"}

        # attempt to extract a reliable URL
        url = ""
        raw = best.get("raw") or {}
        # ytmusicapi may have videoId or browseId
        vid = raw.get("videoId") or raw.get("videoId")
        if vid:
            url = f"https://www.youtube.com/watch?v={vid}"
        else:
            url = raw.get("link") or raw.get("url") or ""

        confidence = "High" if best_score >= 2 else "Low"
        return {"url": url or "", "title": best.get("title") or "", "confidence": confidence}
