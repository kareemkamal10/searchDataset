"""Heuristic song matcher: clean titles and find probable originals on YouTube.

Uses `youtubesearchpython.VideosSearch` as the default search backend for a
lightweight "no-API-key" experience. The class is small, testable and
dependency-injectable for easier unit testing/mocking.
"""
from __future__ import annotations

from typing import Dict, Optional, Callable, Any
import logging

# Import the search backend lazily inside `find_original` so unit tests can
# import this module without requiring `youtubesearchpython` to be installed.
from src.processing.string_cleaner import clean_cover_title


class SongMatcher:
    """Provide cleaning + search helpers to map cover titles -> original tracks.

    Example:
        >>> matcher = SongMatcher()
        >>> matcher.clean_title('Amr Diab - Tamally Maak (Piano Cover by X)')
        'Amr Diab Tamally Maak'
    """

    def __init__(self, search_client: Optional[Callable[..., Any]] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        # allow dependency injection; if None, we'll import the default at runtime
        self.search_client = search_client

    def clean_title(self, title: str) -> str:
        """Return a cleaned query string from a cover title.

        Delegates to `string_cleaner.clean_cover_title` to keep responsibilities
        separated and easily testable.
        """
        return clean_cover_title(title)

    def find_original(self, query: str) -> Dict[str, Optional[str]]:
        """Search YouTube for the most likely original recording.

        Args:
            query: raw cover title (will be cleaned first)

        Returns:
            Dict with keys `title` and `url`. If lookup fails, values are None.
        """
        cleaned = self.clean_title(query)
        if not cleaned:
            return {"title": None, "url": None}

        try:
            # Lazy-import the default search backend when needed so this module
            # can be imported in environments where `youtubesearchpython` is not present.
            if self.search_client is None:
                try:
                    from youtubesearchpython import VideosSearch  # type: ignore
                    self.search_client = VideosSearch
                except Exception as imp_exc:
                    self.logger.exception("Search backend unavailable: %s", imp_exc)
                    return {"title": None, "url": None}

            vs = self.search_client(cleaned, limit=5)
            results = vs.result().get("result", [])
            if not results:
                return {"title": None, "url": None}
            top = results[0]
            return {"title": top.get("title"), "url": top.get("link")}
        except Exception as exc:
            self.logger.exception("find_original failed for %s: %s", cleaned, exc)
            return {"title": None, "url": None}
