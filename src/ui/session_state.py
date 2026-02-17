"""Helpers to initialize and manage Streamlit session state for the app."""
import streamlit as st
from typing import List, Dict, Any


def ensure_state() -> None:
    """Ensure required session-state variables exist."""
    if "videos" not in st.session_state:
        st.session_state["videos"] = []


def set_videos(videos: List[Dict[str, Any]]) -> None:
    """Store a list of serializable video dicts into session state."""
    st.session_state["videos"] = videos


def get_videos() -> List[Dict[str, Any]]:
    """Return the current videos list from session state."""
    ensure_state()
    return st.session_state["videos"]
