"""
C4 Streamlit UI: two pages, one per part of the component.

  Affective Background Audio Analysis   (frontend/audio_analysis.py)
  Recommendations for Enhancements      (frontend/recommendations.py)

Start the backend first, then (from the c4-audio-emotion folder):
    venv\\Scripts\\python -m streamlit run frontend/app.py

How Streamlit works: the page script runs top to bottom every time the user clicks something.
Anything to remember between runs (the current results) is kept in st.session_state.
"""
import streamlit as st

from style import apply_style

st.set_page_config(page_title="C4 Audio Emotion", page_icon="🎧", layout="wide")
apply_style()     # colours, cards and music-note loading animations (frontend/style.py)

pages = st.navigation([
    st.Page("audio_analysis.py", title="Affective Background Audio Analysis", icon="🎵", default=True),
    st.Page("recommendations.py", title="Recommendations for Enhancements", icon="💡"),
])
pages.run()
