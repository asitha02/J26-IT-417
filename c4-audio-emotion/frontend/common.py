"""
Helpers shared by both pages: backend calls, time formatting, labels and the charts.
Colours match the theme in .streamlit/config.toml; chart backgrounds are transparent so the
same charts look right in light and dark mode.
"""
import plotly.graph_objects as go
import requests
import streamlit as st

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SEVERITY_ICON = {"high": "🔴", "medium": "🟠", "low": "🟢"}
SEVERITY_COLOR = {"high": "#F43F5E", "medium": "#F59E0B", "low": "#10B981"}
QUADRANT_LABELS = {
    "energetic_positive": "Energetic / positive",
    "tense_negative": "Tense / negative",
    "low_negative": "Low / negative (sad, bored)",
    "calm_positive": "Calm / positive",
}
QUADRANT_COLOR = {"energetic_positive": "#F59E0B", "tense_negative": "#F43F5E",
                  "low_negative": "#6366F1", "calm_positive": "#10B981"}
VALENCE_COLOR, AROUSAL_COLOR = "#06B6D4", "#EC4899"
VOICE_COLOR, MUSIC_COLOR = "#22D3EE", "#A78BFA"


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
        response = requests.request(method, url, timeout=600, **kwargs)
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


def _layout(fig: go.Figure, height: int, **kwargs) -> go.Figure:
    """Shared chart look: transparent background, soft grid, legend on top."""
    settings = dict(height=height, margin=dict(t=50, b=40, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=1.15), hovermode="x unified")
    settings.update(kwargs)          # a chart can override any default (e.g. hovermode)
    fig.update_layout(**settings)
    fig.update_xaxes(gridcolor="rgba(124,58,237,0.12)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(124,58,237,0.12)", zeroline=False)
    return fig


def time_axis(fig: go.Figure, end_s: float) -> None:
    """x-axis in mm:ss."""
    ticks = list(range(0, int(end_s) + 1, 30 if end_s > 60 else 10))
    fig.update_xaxes(title="Time (mm:ss)", tickvals=ticks, ticktext=[mmss(t) for t in ticks])


def emotion_timeline(segments, end_s, compare=None, shaded=()) -> go.Figure:
    """
    Valence and arousal over time (plotted at the middle of each window), as smooth glowing curves.
    compare: optional (valence_list, arousal_list) drawn as dotted lines.
    shaded: [(start_s, end_s, label), ...] highlighted ranges.
    """
    x = [(s["start_s"] + s["end_s"]) / 2 for s in segments]
    fig = go.Figure()
    for key, name, color, fill in [("valence", "Valence (negative ↔ positive)", VALENCE_COLOR, "rgba(6,182,212,0.12)"),
                                   ("arousal", "Arousal (calm ↔ energetic)", AROUSAL_COLOR, "rgba(236,72,153,0.12)")]:
        fig.add_trace(go.Scatter(x=x, y=[s[key] for s in segments], name=name, mode="lines+markers",
                                 line=dict(color=color, width=3, shape="spline"), marker=dict(size=6),
                                 fill="tozeroy", fillcolor=fill))
    if compare:
        fig.add_trace(go.Scatter(x=x, y=compare[0], name="Valence, unseparated audio",
                                 line=dict(color=VALENCE_COLOR, dash="dot", shape="spline"), opacity=0.55))
        fig.add_trace(go.Scatter(x=x, y=compare[1], name="Arousal, unseparated audio",
                                 line=dict(color=AROUSAL_COLOR, dash="dot", shape="spline"), opacity=0.55))
    for start, end, label in shaded:
        fig.add_vrect(x0=start, x1=end, fillcolor="#F59E0B", opacity=0.16, line_width=0,
                      annotation_text=label, annotation_position="top left")
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(148,163,184,0.6)")
    _layout(fig, 410, yaxis=dict(title="Value", range=[-1.05, 1.05]))
    time_axis(fig, end_s)
    return fig


def quadrant_chart(segments) -> go.Figure:
    """Each window as a dot on the valence (x) / arousal (y) plane; coloured quadrants, dots coloured by time."""
    fig = go.Figure()
    for (x0, x1, y0, y1), key in [((0, 1.05, 0, 1.05), "energetic_positive"), ((-1.05, 0, 0, 1.05), "tense_negative"),
                                  ((-1.05, 0, -1.05, 0), "low_negative"), ((0, 1.05, -1.05, 0), "calm_positive")]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=QUADRANT_COLOR[key], opacity=0.10, line_width=0)
        fig.add_annotation(x=(x0 + x1) / 2, y=0.92 if y0 >= 0 else -0.92, text=QUADRANT_LABELS[key],
                           showarrow=False, font=dict(color=QUADRANT_COLOR[key], size=12))
    fig.add_trace(go.Scatter(
        x=[s["valence"] for s in segments], y=[s["arousal"] for s in segments], mode="markers",
        marker=dict(size=11, color=[s["start_s"] for s in segments], colorscale=[[0, "#22D3EE"], [0.5, "#A78BFA"], [1, "#EC4899"]],
                    line=dict(width=1, color="rgba(255,255,255,0.7)"), showscale=True,
                    colorbar=dict(title="time (s)", thickness=10)),
        text=[f"{mmss(s['start_s'])}–{mmss(s['end_s'])}" for s in segments],
        hovertemplate="%{text}<br>valence %{x:.2f}<br>arousal %{y:.2f}<extra></extra>", showlegend=False,
    ))
    fig.add_hline(y=0, line_color="rgba(148,163,184,0.6)")
    fig.add_vline(x=0, line_color="rgba(148,163,184,0.6)")
    _layout(fig, 420, xaxis=dict(title="Valence", range=[-1.05, 1.05]), yaxis=dict(title="Arousal", range=[-1.05, 1.05]),
            hovermode="closest")
    return fig


def donut(labels: list, values: list, colors: list, center: str, height: int = 280) -> go.Figure:
    """An easy-to-read donut chart with a big label in the middle."""
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.62, sort=False,
                           marker=dict(colors=colors, line=dict(color="rgba(255,255,255,0.6)", width=2)),
                           textinfo="value", textfont=dict(size=15, color="#fff"),
                           hovertemplate="%{label}: %{value}<extra></extra>"))
    fig.update_layout(height=height, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-0.12, font=dict(size=11)),
                      annotations=[dict(text=center, showarrow=False, font=dict(size=17))])
    return fig
