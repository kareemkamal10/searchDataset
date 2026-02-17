"""Reusable Streamlit UI components for Maqam-Matcher.

Keep UI helpers small and declarative so `app.py` remains focused on flow.
"""
from typing import Dict, Any
import streamlit as st


def render_video_card(index: int, video: Dict[str, Any]) -> None:
    """Render a single video card in the Streamlit app.

    Controls are keyed using the index so state persists across reruns.
    This helper mutates Streamlit session state controls (checkbox, override).
    """
    cols = st.columns([1, 4])
    with cols[0]:
        if video.get("thumbnail"):
            st.image(video["thumbnail"], use_column_width=True)
        else:
            st.empty()
    with cols[1]:
        title = video.get("title", "")
        short_flag = video.get("is_short", False)
        badge = " 🔸 SHORT" if short_flag else ""
        st.markdown(f"**{title}**{badge}")
        checked = st.checkbox("Select", value=video.get("selected", True), key=f"selected_{index}")

        proposed_title = video.get("proposed_original_title") or "(no match)"
        proposed_url = video.get("proposed_original_url") or ""
        proposed_conf = video.get("proposed_confidence") or "Low"
        st.markdown(f"**Proposed Original:** {proposed_title}  ")
        if proposed_url:
            st.markdown(f"[Open]({proposed_url})  ")
        st.markdown(f"**Confidence:** {proposed_conf}")

        # manual override field (serves as 'Edit')
        override = st.text_input("Manual original URL (override)", value=video.get("manual_override", ""), key=f"override_{index}")

        # Sync simple fields back into the video dict stored in session
        video["selected"] = checked
        video["manual_override"] = override
