"""Placeholder for reusable Streamlit UI components."""

from __future__ import annotations

import streamlit as st


def section_header(title: str) -> None:
    """Render a standard section header."""
    st.markdown(f"## {title}")
