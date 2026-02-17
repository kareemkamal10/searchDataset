"""The Brain: title sanitisation -> YouTube search -> heuristic scoring.

This is the most important module.  Its job is to take a raw cover title,
clean it, search YouTube for the probable original track, and return a
result with a confidence score.

Search backend: ``youtube-search-python`` (no API key required).
"""
from __future__ import annotations

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from youtubesearchpython import VideosSearch

from src.utils import clean_cover_title

logger = logging.getLogger("Matcher")


class Matcher:
    """Map cover titles to their probable original songs.

    Workflow per title:
        1. **Sanitise** — strip noise via :func:`~src.utils.clean_cover_title`.
        2. **Search**   — query YouTube using ``youtubesearchpython``.
        3. **Score**    — rank results with heuristic filters.
        4. **Return**   — ``{original_title, original_url, confidence_score}``.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_original(self, raw_title: str) -> Dict[str, Optional[str]]:
        """Find the most likely original song for *raw_title*.

        Returns:
            dict with keys ``original_title``, ``original_url``, ``confidence_score``.
        """
        cleaned = clean_cover_title(raw_title)
        logger.info("Cleaning: \"%s\" -> \"%s\"", raw_title[:60], cleaned)

        if not cleaned or len(cleaned) < 3:
            logger.warning("Cleaned title too short, skipping search")
            return {"original_title": "", "original_url": "", "confidence_score": "Low"}

        results = self._search(cleaned)
        if not results:
            logger.warning("No search results for: \"%s\"", cleaned)
            return {"original_title": "", "original_url": "", "confidence_score": "Low"}

        logger.info("Search returned %d candidates", len(results))

        # Score each candidate
        q_tokens = [t.lower() for t in cleaned.split() if len(t) > 1]
        best = None
        best_score = -999

        for r in results:
            title = r.get("title") or ""
            channel = r.get("channel", {}).get("name", "") if isinstance(r.get("channel"), dict) else str(r.get("channel", ""))
            link = r.get("link") or ""

            score = self._score(q_tokens, title, channel)

            logger.debug(
                "  Candidate: \"%s\" [%s] — score: %d",
                title[:50], channel[:30], score,
            )

            if score > best_score:
                best_score = score
                best = {"title": title, "url": link, "channel": channel}

        if not best or best_score < -5:
            logger.info("No suitable match found (best score: %d)", best_score)
            return {"original_title": "", "original_url": "", "confidence_score": "Low"}

        # Determine confidence tier
        if best_score >= 5:
            confidence = "High"
        elif best_score >= 2:
            confidence = "Medium"
        else:
            confidence = "Low"

        logger.info(
            "Best match: \"%s\" — confidence: %s (score: %d)",
            best["title"][:60], confidence, best_score,
        )

        return {
            "original_title": best["title"],
            "original_url": best["url"],
            "confidence_score": confidence,
        }

    def match_batch(
        self,
        videos: List[Dict[str, Any]],
        max_workers: int = 5,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        """Run :meth:`find_original` for every video **in parallel**.

        Mutates each video dict in-place by adding ``original_title``,
        ``original_url``, and ``confidence_score`` keys.

        Args:
            videos: list of video metadata dicts (must have ``"title"`` key).
            max_workers: number of concurrent threads (default 5).
            progress_callback: optional ``callable(done, total)`` for UI updates.

        Returns:
            The same list with match results attached.
        """
        total = len(videos)
        logger.info("Starting parallel matching for %d videos (workers: %d)", total, max_workers)
        t0 = time.perf_counter()

        def _process(idx_video):
            idx, video = idx_video
            tag = f"[{idx + 1}/{total}]"
            try:
                result = self.find_original(video.get("title", ""))
                video["original_title"] = result["original_title"]
                video["original_url"] = result["original_url"]
                video["confidence_score"] = result["confidence_score"]
                logger.info("%s Done — %s", tag, result["confidence_score"])
            except Exception as exc:
                logger.exception("%s Match failed: %s", tag, exc)
                video["original_title"] = ""
                video["original_url"] = ""
                video["confidence_score"] = "Low"
            return idx

        done_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_process, (i, v)): i for i, v in enumerate(videos)}
            for future in as_completed(futures):
                future.result()  # propagate exceptions
                done_count += 1
                if progress_callback:
                    progress_callback(done_count, total)

        elapsed = time.perf_counter() - t0
        logger.info("Matching complete — %d videos processed in %.1fs", total, elapsed)
        return videos

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query YouTube via ``youtubesearchpython`` and return raw results."""
        try:
            vs = VideosSearch(query, limit=limit)
            data = vs.result()
            return data.get("result", [])
        except Exception as exc:
            logger.exception("YouTube search failed for \"%s\": %s", query, exc)
            return []

    def _score(self, query_tokens: List[str], title: str, channel: str) -> int:
        """Score a candidate result.

        Positive signals:
            - Title/channel contains "official", "audio", "video", "vevo"
            - Query token overlap with candidate title
        Negative signals:
            - Candidate is itself a cover / piano / tutorial / synthesia
        """
        score = 0
        t = (title or "").lower()
        ch = (channel or "").lower()

        # Positive: official / VEVO channels are likely originals
        if any(kw in t for kw in ("official", "official audio", "official video")):
            score += 4
        if "vevo" in ch or "official" in ch:
            score += 3
        if any(kw in t for kw in ("audio", "video")):
            score += 1

        # Positive: token overlap between query and candidate
        title_tokens = set(clean_cover_title(title).lower().split())
        overlap = sum(1 for q in query_tokens if q in title_tokens)
        score += overlap

        # Negative: candidate is itself a cover
        cover_signals = ("cover", "piano", "tutorial", "synthesia", "karaoke", "instrumental")
        if any(kw in t for kw in cover_signals):
            score -= 10

        return score
