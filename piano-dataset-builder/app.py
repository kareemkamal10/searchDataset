"""Streamlit application entry point for Maqam-Matcher.

Run with: `streamlit run app.py`
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any

import streamlit as st
import pandas as pd

from config import settings
from src.connectors.youtube_client import YouTubeFetcher
from src.processing.matcher import SongMatcher
from src.ui import components, session_state


# ---- logging ---------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Maqam-Matcher")


def _export_dataset(videos: List[Dict[str, Any]]) -> str:
    """Export selected videos to CSV and return the filepath."""
    rows = []
    for v in videos:
        if not v.get("selected", True):
            continue
        cover_url = v.get("cover_url")
        cover_title = v.get("title")
        # manual override takes precedence
        original_url = v.get("manual_override") or v.get("proposed_original_url")
        original_title = v.get("manual_override") and "(manual)" or v.get("proposed_original_title")
        rows.append({
            "cover_url": cover_url,
            "original_url": original_url,
            "cover_title": cover_title,
            "original_title": original_title,
        })

    df = pd.DataFrame(rows, columns=["cover_url", "original_url", "cover_title", "original_title"])
    out_path = settings.DATASET_OUTPUT_PATH
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def main() -> None:
    st.set_page_config(page_title="Maqam-Matcher", layout="wide")
    st.title("Maqam-Matcher — Arabic Piano Covers curation")
    session_state.ensure_state()

    # Sidebar controls
    st.sidebar.header("Import")
    playlist_url = st.sidebar.text_input("Playlist / Channel URL")
    fetch = st.sidebar.button("Fetch Videos")

    fetcher = YouTubeFetcher(ydl_opts=settings.DEFAULT_YTDLP_OPTS)
    matcher = SongMatcher()

    if fetch and playlist_url:
        with st.spinner("Fetching playlist metadata — fast, metadata-only..."):
            items = fetcher.get_playlist_videos(playlist_url)
            # Attach proposed matches lazily
            for it in items:
                proposed = matcher.find_original(it.get("title", ""))
                it["proposed_original_url"] = proposed.get("url")
                it["proposed_original_title"] = proposed.get("title")
                it.setdefault("selected", True)
                it.setdefault("manual_override", "")
            session_state.set_videos(items)
            st.success(f"Loaded {len(items)} videos")

    videos = session_state.get_videos()

    st.sidebar.markdown("---")
    if videos:
        st.sidebar.write(f"Loaded videos: **{len(videos)}**")
        if st.sidebar.button("Clear list"):
            session_state.set_videos([])
            st.experimental_rerun()

    # Main curation area
    st.header("Curation interface")
    if not videos:
        st.info("Paste a playlist or channel URL on the left and press 'Fetch Videos' to begin.")
        return

    # Display each video using the reusable component
    for idx, video in enumerate(videos):
        components.render_video_card(idx, video)
        st.markdown("---")

    # Export button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Export Dataset"):
            out = _export_dataset(session_state.get_videos())
            st.success(f"Dataset saved to {out}")
            # also offer download
            df = pd.read_csv(out, encoding="utf-8-sig")
            csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("Download CSV", data=csv_bytes, file_name="dataset_output.csv", mime="text/csv")

    with col2:
        st.markdown(
            "**Export rules:** unchecked videos are excluded. Manual URL overrides take precedence over auto-match."
        )


if __name__ == "__main__":
    main()
