"""
C4 Streamlit UI.

Start the backend first, then (from the c4-audio-emotion folder):
    venv\\Scripts\\python -m streamlit run frontend/app.py

How Streamlit works: this whole file runs top to bottom every time the user
clicks something. Anything we want to remember between runs (the current
result) is kept in st.session_state.
"""
import json

import plotly.graph_objects as go
import requests
import streamlit as st

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SEVERITY_ICON = {"high": "🔴", "medium": "🟠", "low": "🟢"}
QUADRANT_LABELS = {
    "energetic_positive": "Energetic / positive",
    "tense_negative": "Tense / negative",
    "low_negative": "Low / negative (sad, bored)",
    "calm_positive": "Calm / positive",
}


# ---------- small helpers ----------

def mmss(seconds: float) -> str:
    """130 -> '02:10'"""
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def is_whole_video(rec: dict, result: dict) -> bool:
    """True for recommendations about the whole clip (e.g. overall complaints), not one section."""
    return rec["start_s"] == 0 and rec["end_s"] >= result["analyzed_seconds"]


def time_range(rec: dict, result: dict) -> str:
    return "whole video" if is_whole_video(rec, result) else f"{mmss(rec['start_s'])}–{mmss(rec['end_s'])}"


def call_backend(method: str, path: str, **kwargs):
    """
    Call the FastAPI backend and return (data, error_message).
    Exactly one of the two is None.
    """
    url = st.session_state.backend_url.rstrip("/") + path
    try:
        response = requests.request(method, url, timeout=600, **kwargs)  # long videos + retries can take minutes
    except requests.exceptions.ConnectionError:
        return None, f"Cannot reach the backend at {st.session_state.backend_url}. Is uvicorn running?"
    except requests.exceptions.Timeout:
        return None, "The backend took too long to answer (over 10 minutes)."

    if response.ok:
        try:
            return response.json(), None
        except ValueError:
            return None, "The backend sent an empty or invalid reply. Check the uvicorn terminal for errors."
    # FastAPI puts its error message in "detail".
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    return None, f"Error {response.status_code}: {detail}"


# ---------- charts ----------

def timeline_chart(result: dict) -> go.Figure:
    """Valence and arousal over time, with recommendation time ranges shaded."""
    segments = result["segments"]
    # Plot each value at the middle of its window.
    x = [(s["start_s"] + s["end_s"]) / 2 for s in segments]

    fig = go.Figure()
    # Two clearly different colours so valence and arousal are easy to tell apart.
    fig.add_trace(go.Scatter(x=x, y=[s["valence"] for s in segments], name="Valence (negative ↔ positive)",
                             mode="lines+markers", line=dict(color="#2a9d8f")))
    fig.add_trace(go.Scatter(x=x, y=[s["arousal"] for s in segments], name="Arousal (calm ↔ energetic)",
                             mode="lines+markers", line=dict(color="#e76f51")))

    # Shade only recommendations about a specific section (whole-video ones would cover everything).
    for rec in result["recommendations"]:
        if not is_whole_video(rec, result):
            fig.add_vrect(x0=rec["start_s"], x1=rec["end_s"], fillcolor="gold", opacity=0.2, line_width=0,
                          annotation_text=rec["id"], annotation_position="top left")

    end = result["analyzed_seconds"]
    ticks = list(range(0, int(end) + 1, 30 if end > 60 else 10))
    fig.update_layout(
        xaxis=dict(title="Time (mm:ss)", tickvals=ticks, ticktext=[mmss(t) for t in ticks]),
        yaxis=dict(title="Value", range=[-1.05, 1.05]),
        legend=dict(orientation="h", y=1.12),
        height=380, margin=dict(t=40, b=40),
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    return fig


def quadrant_chart(result: dict) -> go.Figure:
    """Each window as a dot on the valence (x) / arousal (y) plane."""
    segments = result["segments"]
    fig = go.Figure(go.Scatter(
        x=[s["valence"] for s in segments],
        y=[s["arousal"] for s in segments],
        mode="markers",
        marker=dict(size=9, opacity=0.7),
        text=[f"{mmss(s['start_s'])}–{mmss(s['end_s'])}" for s in segments],
        hovertemplate="%{text}<br>valence %{x:.2f}<br>arousal %{y:.2f}<extra></extra>",
    ))
    # Quadrant names in the four corners.
    for qx, qy, key in [(0.5, 0.95, "energetic_positive"), (-0.5, 0.95, "tense_negative"),
                        (-0.5, -0.95, "low_negative"), (0.5, -0.95, "calm_positive")]:
        fig.add_annotation(x=qx, y=qy, text=QUADRANT_LABELS[key], showarrow=False, font=dict(color="gray"))
    fig.add_hline(y=0, line_color="gray")
    fig.add_vline(x=0, line_color="gray")
    fig.update_layout(
        xaxis=dict(title="Valence", range=[-1.05, 1.05]),
        yaxis=dict(title="Arousal", range=[-1.05, 1.05]),
        height=420, margin=dict(t=20, b=40),
    )
    return fig


# ---------- page sections ----------

def show_sidebar():
    st.sidebar.header("Settings")
    st.sidebar.text_input("Backend URL", key="backend_url")

    st.sidebar.header("Past analyses")
    analyses, error = call_backend("GET", "/analyses")
    if error:
        st.sidebar.warning(error)
        return
    if not analyses:
        st.sidebar.caption("No analyses yet.")
    for item in analyses:
        if st.sidebar.button(item["title"] or item["video_id"], key=f"open_{item['video_id']}", width="stretch"):
            data, error = call_backend("GET", f"/analyses/{item['video_id']}")
            if error:
                st.sidebar.error(error)
            else:
                st.session_state.result = data


def show_results(result: dict):
    # 1. Header
    st.header(result["title"] or result["video_id"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Video id", result["video_id"])
    col2.metric("Analysed", mmss(result["analyzed_seconds"]))
    col3.metric("Segments", len(result["segments"]))
    if result["model_info"]["mock"]:
        st.warning("⚠️ MOCK MODEL: these emotion values are fake (random walk), used only to test the pipeline.")
    else:
        st.success(f"Model: {result['model_info']['embedding_model']} + {result['model_info']['head']}")

    # 2. Emotion timeline
    st.subheader("Emotion timeline")
    st.plotly_chart(timeline_chart(result), width="stretch")

    # 3. Valence-arousal quadrant plot
    overall = result["overall"]
    st.subheader("Valence–arousal map")
    st.write(
        f"Dominant mood: **{QUADRANT_LABELS[overall['dominant_quadrant']]}** "
        f"(mean valence {overall['mean_valence']:+.2f}, mean arousal {overall['mean_arousal']:+.2f})"
    )
    st.plotly_chart(quadrant_chart(result), width="stretch")

    # 4. Inputs from other components (dummy data)
    st.subheader("Inputs from other components (DUMMY DATA)")
    st.caption("⚠️ These are made-up placeholder inputs for Component 3 and knowledge-gap detection, "
               "used until the real components are connected. They are not real comments or analysis.")
    c3, gaps = result["c3_input"], result["gaps_input"]
    left, right = st.columns(2)
    with left:
        st.markdown("**Audience sentiment (C3), dummy**")
        if c3:
            st.write(f"Overall: **{c3.get('sentiment_label')}** ({c3.get('sentiment_score'):+.2f}, "
                     f"{c3.get('comment_count')} comments)")
            st.write("Top complaints: " + (", ".join(c3.get("top_complaints", [])) or "none"))
            st.write("Requested topics: " + (", ".join(c3.get("requested_topics", [])) or "none"))
            for c in c3.get("timestamped_feedback", []):
                st.write(f"- {mmss(c['t_s'])}  '{c['text']}'  ({c['sentiment']:+.1f})")
        else:
            st.caption("No C3 input stored for this analysis (re-analyse to add it).")
    with right:
        st.markdown("**Knowledge gaps, dummy**")
        if gaps.get("gaps"):
            for gap in gaps["gaps"]:
                st.write(f"- **{gap['topic']}** ({mmss(gap['start_s'])}–{mmss(gap['end_s'])}, "
                         f"{gap['severity']}): {gap['description']}")
        else:
            st.caption("No knowledge gaps for this video.")

    # 5. Recommendation cards, most severe first
    st.subheader("Recommendations")
    recs = sorted(result["recommendations"], key=lambda r: (SEVERITY_ORDER.get(r["severity"], 3), -r["confidence"]))
    if not recs:
        st.info("No recommendations for this video (no rule was triggered).")
    for rec in recs:
        with st.container(border=True):
            st.markdown(f"{SEVERITY_ICON.get(rec['severity'], '')} **{rec['title']}**  ·  "
                        f"{time_range(rec, result)}  ·  {rec['severity']} severity  ·  confidence {rec['confidence']:.2f}")
            st.caption(f"{rec['id']} · rule {rec['rule_id']}")
            for line in rec["evidence"]:
                st.write(f"- {line}")
            st.markdown(f"**Suggestion:** {rec['suggestion']}")

    # 6. Download the full JSON result
    st.download_button(
        "Download JSON",
        data=json.dumps(result, indent=2),
        file_name=f"c4_analysis_{result['video_id']}.json",
        mime="application/json",
    )


# ---------- main page ----------

st.set_page_config(page_title="C4 Audio Emotion", layout="wide")
st.session_state.setdefault("backend_url", "http://localhost:8000")
st.session_state.setdefault("result", None)

show_sidebar()

st.title("C4: Audio Emotion Analysis")
st.caption("Paste a YouTube link. The first 3 minutes of audio are analysed for valence (negative ↔ positive) and arousal (calm ↔ energetic).")

youtube_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
force = st.checkbox("Re-analyse even if a saved result exists")

if st.button("Analyze", type="primary"):
    if not youtube_url.strip():
        st.error("Please paste a YouTube URL first.")
    else:
        with st.spinner("Analysing... downloading audio and running the model (usually 10-20 s for a new video)"):
            data, error = call_backend("POST", "/analyze", json={"youtube_url": youtube_url, "force_reanalyze": force})
        if error:
            st.error(error)
        else:
            st.session_state.result = data

if st.session_state.result:
    show_results(st.session_state.result)
