"""
Helpers shared by both pages: backend calls, time formatting, labels and the emotion charts.
"""
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
VALENCE_COLOR, AROUSAL_COLOR = "#2a9d8f", "#e76f51"


def mmss(seconds: float) -> str:
    """130 -> '02:10'"""
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def call_backend(method: str, path: str, **kwargs):
    """
    Call the FastAPI backend and return (data, error_message).
    Exactly one of the two is None.
    """
    url = st.session_state.backend_url.rstrip("/") + path
    try:
        response = requests.request(method, url, timeout=600, **kwargs)  # separation can take minutes
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


def time_axis(fig: go.Figure, end_s: float) -> None:
    """x-axis in mm:ss."""
    ticks = list(range(0, int(end_s) + 1, 30 if end_s > 60 else 10))
    fig.update_xaxes(title="Time (mm:ss)", tickvals=ticks, ticktext=[mmss(t) for t in ticks])


def emotion_timeline(segments, end_s, compare=None, shaded=()) -> go.Figure:
    """
    Valence and arousal over time (plotted at the middle of each window).
    compare: optional (valence_list, arousal_list) drawn as dotted lines.
    shaded: [(start_s, end_s, label), ...] highlighted ranges.
    """
    x = [(s["start_s"] + s["end_s"]) / 2 for s in segments]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=[s["valence"] for s in segments], name="Valence (negative ↔ positive)",
                             mode="lines+markers", line=dict(color=VALENCE_COLOR)))
    fig.add_trace(go.Scatter(x=x, y=[s["arousal"] for s in segments], name="Arousal (calm ↔ energetic)",
                             mode="lines+markers", line=dict(color=AROUSAL_COLOR)))
    if compare:
        fig.add_trace(go.Scatter(x=x, y=compare[0], name="Valence, unseparated audio",
                                 line=dict(color=VALENCE_COLOR, dash="dot"), opacity=0.6))
        fig.add_trace(go.Scatter(x=x, y=compare[1], name="Arousal, unseparated audio",
                                 line=dict(color=AROUSAL_COLOR, dash="dot"), opacity=0.6))
    for start, end, label in shaded:
        fig.add_vrect(x0=start, x1=end, fillcolor="gold", opacity=0.2, line_width=0,
                      annotation_text=label, annotation_position="top left")
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(yaxis=dict(title="Value", range=[-1.05, 1.05]), legend=dict(orientation="h", y=1.15),
                      height=400, margin=dict(t=50, b=40))
    time_axis(fig, end_s)
    return fig


def quadrant_chart(segments) -> go.Figure:
    """Each window as a dot on the valence (x) / arousal (y) plane."""
    fig = go.Figure(go.Scatter(
        x=[s["valence"] for s in segments], y=[s["arousal"] for s in segments], mode="markers",
        marker=dict(size=9, opacity=0.7),
        text=[f"{mmss(s['start_s'])}–{mmss(s['end_s'])}" for s in segments],
        hovertemplate="%{text}<br>valence %{x:.2f}<br>arousal %{y:.2f}<extra></extra>",
    ))
    for qx, qy, key in [(0.5, 0.95, "energetic_positive"), (-0.5, 0.95, "tense_negative"),
                        (-0.5, -0.95, "low_negative"), (0.5, -0.95, "calm_positive")]:
        fig.add_annotation(x=qx, y=qy, text=QUADRANT_LABELS[key], showarrow=False, font=dict(color="gray"))
    fig.add_hline(y=0, line_color="gray")
    fig.add_vline(x=0, line_color="gray")
    fig.update_layout(xaxis=dict(title="Valence", range=[-1.05, 1.05]), yaxis=dict(title="Arousal", range=[-1.05, 1.05]),
                      height=420, margin=dict(t=20, b=40))
    return fig
