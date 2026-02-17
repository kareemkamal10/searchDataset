"""Maqam-Matcher — Streamlit application entry point.

Run with:  ``streamlit run app.py``

Workflow:
    1. User pastes a YouTube Channel / Playlist URL in the sidebar.
    2. "Fetch Videos" extracts metadata and classifies Shorts vs Full Videos.
    3. The Matcher auto-detects the original song for each cover.
    4. The Review Grid lets the user verify, override, or deselect pairs.
    5. "Export Dataset" saves selected pairs to ``data/dataset_output.csv``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import streamlit as st
import pandas as pd

from src.fetcher import Fetcher
from src.classifier import classify_batch
from src.matcher import Matcher
from src.utils import format_duration

# ---------------------------------------------------------------------------
# Logging — visible in the terminal where `streamlit run app.py` is executed
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Maqam-Matcher")

# Quiet noisy third-party loggers so our logs stand out
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("streamlit").setLevel(logging.WARNING)
logging.getLogger("yt_dlp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATASET_OUTPUT_PATH = "data/dataset_output.csv"


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _ensure_state() -> None:
    if "videos" not in st.session_state:
        st.session_state["videos"] = []
        logger.debug("Session state initialised (empty video list)")
    if "log_messages" not in st.session_state:
        st.session_state["log_messages"] = []


def _log(msg: str, level: str = "INFO") -> None:
    """Write a message to BOTH the terminal logger and the in-app log panel."""
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"`{ts}` **{level}** — {msg}"
    st.session_state.setdefault("log_messages", []).append(entry)
    getattr(logger, level.lower(), logger.info)(msg)


def _set_videos(videos: List[Dict[str, Any]]) -> None:
    st.session_state["videos"] = videos
    _log(f"Stored {len(videos)} videos in session state")


def _get_videos() -> List[Dict[str, Any]]:
    _ensure_state()
    return st.session_state["videos"]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _export_dataset(videos: List[Dict[str, Any]]) -> str:
    """Build a CSV from selected video pairs and save to disk."""
    _log("Export started — scanning selected videos...")
    rows = []
    skipped = 0
    for v in videos:
        if not v.get("selected", True):
            skipped += 1
            continue
        rows.append({
            "cover_url": v.get("url", ""),
            "cover_title": v.get("title", ""),
            "original_url": v.get("manual_override") or v.get("original_url", ""),
            "original_title": (
                "(manual)" if v.get("manual_override") else v.get("original_title", "")
            ),
            "type": v.get("type", ""),
            "confidence": v.get("confidence_score", ""),
        })

    df = pd.DataFrame(rows)
    df.to_csv(DATASET_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    _log(f"Exported {len(rows)} pairs to {DATASET_OUTPUT_PATH} (skipped {skipped} unchecked)")
    return DATASET_OUTPUT_PATH


# ---------------------------------------------------------------------------
# UI — Review card (one row of the curation grid)
# ---------------------------------------------------------------------------

def _render_review_card(index: int, video: Dict[str, Any]) -> None:
    """Render a 3-column review row: Cover | Detected Original | Controls."""
    col_cover, col_original, col_controls = st.columns([2, 2, 1])

    # ---- Column 1: Cover info ----
    with col_cover:
        if video.get("thumbnail"):
            st.image(video["thumbnail"], width="stretch")
        st.markdown(f"**{video.get('title', '')}**")
        dur = format_duration(video.get("duration"))
        type_badge = "Short" if video.get("type") == "Short" else "Video"
        st.caption(f"{type_badge} · {dur}")

    # ---- Column 2: Detected original ----
    with col_original:
        orig_title = video.get("original_title") or "(no match)"
        orig_url = video.get("original_url") or ""
        confidence = video.get("confidence_score") or "Low"

        st.markdown(f"**{orig_title}**")
        if orig_url:
            st.markdown(f"[Open original]({orig_url})")
        st.caption(f"Confidence: {confidence}")

    # ---- Column 3: Controls ----
    with col_controls:
        checked = st.checkbox(
            "Include",
            value=video.get("selected", True),
            key=f"sel_{index}",
        )
        override = st.text_input(
            "Override URL",
            value=video.get("manual_override", ""),
            key=f"ovr_{index}",
        )
        # Sync back
        video["selected"] = checked
        video["manual_override"] = override


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _render_log_panel() -> None:
    """Show a collapsible live-log panel in the sidebar."""
    logs = st.session_state.get("log_messages", [])
    if not logs:
        return
    with st.sidebar.expander(f"Activity Log ({len(logs)})", expanded=False):
        # Show newest first, cap at 50 entries
        for entry in reversed(logs[-50:]):
            st.markdown(entry)
        if st.button("Clear log"):
            st.session_state["log_messages"] = []


def main() -> None:
    st.set_page_config(page_title="Maqam-Matcher", layout="wide")
    st.title("Maqam-Matcher — Arabic Piano Cover Dataset Curator")
    _ensure_state()
    logger.info("App page rendered (rerun)")

    # ---- Sidebar (use a form so text_input + button submit together) ----
    st.sidebar.header("Import")
    with st.sidebar.form("fetch_form"):
        url_input = st.text_input("YouTube Playlist / Channel URL")
        fetch_btn = st.form_submit_button("Fetch Videos")

    st.sidebar.markdown("---")
    filter_mode = st.sidebar.radio("Show", ["All", "Shorts Only", "Videos Only"])
    logger.debug("Filter mode: %s", filter_mode)

    # ---- Fetch → Classify → Match pipeline ----
    if fetch_btn and url_input:
        _log(f"Fetch requested for: {url_input}")

        fetcher = Fetcher()
        matcher = Matcher()

        # Step 1: Fetch metadata
        with st.spinner("Step 1/3 — Fetching video metadata from YouTube..."):
            raw_videos = fetcher.fetch(url_input)

        if not raw_videos:
            _log("No videos found at that URL.", "WARNING")
            st.sidebar.error("No videos found. Check the URL and try again.")
        else:
            _log(f"Fetched {len(raw_videos)} videos")

            # Step 2: Classify Shorts vs Videos
            with st.spinner("Step 2/3 — Classifying Shorts vs Full Videos..."):
                classify_batch(raw_videos)
                shorts_count = sum(1 for v in raw_videos if v["type"] == "Short")
                vids_count = len(raw_videos) - shorts_count
                _log(f"Classified: {vids_count} Videos, {shorts_count} Shorts")

            # Step 3: Match originals (parallel)
            progress_bar = st.progress(0, text="Step 3/3 — Matching original songs...")

            def _on_progress(done: int, total: int) -> None:
                progress_bar.progress(done / total, text=f"Step 3/3 — Matched {done}/{total} videos...")

            matcher.match_batch(raw_videos, max_workers=5, progress_callback=_on_progress)
            progress_bar.progress(1.0, text="Matching complete!")

            high = sum(1 for v in raw_videos if v.get("confidence_score") == "High")
            med = sum(1 for v in raw_videos if v.get("confidence_score") == "Medium")
            low = sum(1 for v in raw_videos if v.get("confidence_score") == "Low")
            _log(f"Matching done — High: {high}, Medium: {med}, Low: {low}")

            _set_videos(raw_videos)
            st.rerun()

    elif fetch_btn and not url_input:
        _log("Fetch clicked but no URL provided", "WARNING")
        st.sidebar.warning("Please paste a URL first.")

    # ---- Main area ----
    videos = _get_videos()
    logger.debug("Videos in session: %d", len(videos))

    if not videos:
        st.info("Paste a playlist or channel URL in the sidebar and press **Fetch Videos** to begin.")
        _render_log_panel()
        return

    # Apply filter
    if filter_mode == "Shorts Only":
        display = [v for v in videos if v.get("type") == "Short"]
    elif filter_mode == "Videos Only":
        display = [v for v in videos if v.get("type") == "Video"]
    else:
        display = videos

    _log(f"Displaying {len(display)}/{len(videos)} videos (filter: {filter_mode})")

    st.subheader(f"Review Grid — {len(display)} items")
    for idx, v in enumerate(display):
        _render_review_card(idx, v)
        st.markdown("---")

    # ---- Export ----
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Export Dataset"):
            out = _export_dataset(_get_videos())
            st.success(f"Saved to `{out}`")
            df = pd.read_csv(out, encoding="utf-8-sig")
            csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("Download CSV", data=csv_bytes, file_name="dataset_output.csv", mime="text/csv")
    with col2:
        st.caption("Unchecked rows are excluded. Manual URL overrides take precedence over auto-match.")

    # ---- Log panel (bottom of sidebar) ----
    _render_log_panel()


if __name__ == "__main__":
    main()
