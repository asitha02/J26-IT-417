"""
Page 1: Affective Audio Analysis (descriptive).
What does the background audio of this video sound like, and where are the audio problems?
"""
import json

import plotly.graph_objects as go
import streamlit as st

from common import (
    QUADRANT_LABELS,
    SEVERITY_ICON,
    call_backend,
    emotion_timeline,
    mmss,
    quadrant_chart,
    time_axis,
)


def loudness_chart(result: dict) -> go.Figure:
    """Loudness of the narration and of the background music per window, problems shaded."""
    segs = result["segments"]
    x = [(s["start_s"] + s["end_s"]) / 2 for s in segs]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=[s["speech_db"] for s in segs], name="Narration (voice)", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=x, y=[s["music_db"] for s in segs], name="Background music", mode="lines+markers"))
    for p in result["audio_problems"]:
        fig.add_vrect(x0=p["start_s"], x1=p["end_s"], fillcolor="red", opacity=0.12, line_width=0,
                      annotation_text=p["type"].replace("_", " "), annotation_position="top left")
    fig.update_layout(yaxis=dict(title="Loudness (dB, 0 = maximum)"), legend=dict(orientation="h", y=1.15),
                      height=320, margin=dict(t=50, b=40))
    time_axis(fig, result["analyzed_seconds"])
    return fig


def show_sidebar():
    st.sidebar.header("Past audio analyses")
    items, error = call_backend("GET", "/audio/analyses")
    if error:
        st.sidebar.warning(error)
        return
    if not items:
        st.sidebar.caption("No analyses yet.")
    for item in items:
        if st.sidebar.button(item["title"] or item["video_id"], key=f"a_{item['video_id']}", width="stretch"):
            data, error = call_backend("GET", f"/audio/analyses/{item['video_id']}")
            if error:
                st.sidebar.error(error)
            else:
                st.session_state.audio_result = data


def show_result(r: dict):
    # 1. Header
    st.header(r["title"] or r["video_id"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analysed", mmss(r["analyzed_seconds"]))
    c2.metric("Windows", len(r["segments"]))
    c3.metric("Voice loudness", f"{r['separation']['speech_db']} dB")
    c4.metric("Music loudness", f"{r['separation']['music_db']} dB")
    if r["model_info"]["mock"]:
        st.warning("⚠️ MOCK MODEL: these emotion values are fake (random walk), used only to test the pipeline.")
    else:
        st.success(f"Model: {r['model_info']['embedding_model']} + {r['model_info']['head']}  ·  "
                   f"music/speech separation: {r['separation']['method']}")
    if r["separation"]["method"] == "none":
        st.info("Separation is switched off: the 'background music' below is the full mixed audio.")

    # 2. What the music sounds like (CLAP text matching)
    st.subheader("What the background music sounds like")
    if r["music_description"]:
        for item in r["music_description"]:
            st.progress(item["score"], text=f"{item['label']}: {item['score'] * 100:.0f}%")
        st.caption("CLAP compares the music with written descriptions and shows the closest matches.")
    else:
        st.caption("Not available with the mock model.")

    # 3. Emotion of the background music, compared with the unseparated audio
    st.subheader("Emotion of the background music over time")
    o, om = r["overall"], r["overall_mixed"]
    st.write(f"Background music: **{QUADRANT_LABELS[o['dominant_quadrant']]}** "
             f"(valence {o['mean_valence']:+.2f}, arousal {o['mean_arousal']:+.2f}).  "
             f"Unseparated audio (voice + music): {QUADRANT_LABELS[om['dominant_quadrant']]} "
             f"(valence {om['mean_valence']:+.2f}, arousal {om['mean_arousal']:+.2f}).")
    compare = st.checkbox("Also show the unseparated audio (dotted lines)", value=True)
    segs = r["segments"]
    st.plotly_chart(emotion_timeline(
        segs, r["analyzed_seconds"],
        compare=([s["mixed_valence"] for s in segs], [s["mixed_arousal"] for s in segs]) if compare else None,
        shaded=[(p["start_s"], p["end_s"], p["type"].replace("_", " ")) for p in r["audio_problems"]],
    ), width="stretch")
    left, right = st.columns(2)
    with left:
        st.markdown("**Valence–arousal map (background music)**")
        st.plotly_chart(quadrant_chart(segs), width="stretch")
    with right:
        st.markdown("**Loudness: voice vs. background music**")
        st.plotly_chart(loudness_chart(r), width="stretch")
        st.caption("Music should stay well below the voice (more than 10 dB) so the narration is easy to follow.")

    # 4. Audio problems (measured)
    st.subheader("Audio problems found")
    if not r["audio_problems"]:
        st.success("No loudness, distortion or silence problems were measured.")
    for p in r["audio_problems"]:
        with st.container(border=True):
            link = f"{r['youtube_url']}&t={int(p['start_s'])}s"
            st.markdown(f"{SEVERITY_ICON.get(p['severity'], '')} **{p['description']}**  ·  "
                        f"{p['severity']} severity  ·  [▶ watch at {mmss(p['start_s'])}]({link})")
            for e in p["evidence"]:
                st.write(f"- {e}")

    # 5. Next step + download
    st.divider()
    st.session_state.selected_video = r["video_id"]
    st.page_link("recommendations.py", label="Go to Part 2: Recommendations for this video →", icon="💡")
    st.download_button("Download JSON (Part 1)", data=json.dumps(r, indent=2),
                       file_name=f"c4_audio_{r['video_id']}.json", mime="application/json")


st.title("Part 1 · Affective Audio Analysis")
st.caption("Separates the narration from the background music, then describes the music's emotion over time "
           "and measures audio problems. First 3 minutes of the video.")
show_sidebar()

url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
force = st.checkbox("Re-analyse even if a saved result exists")
if st.button("Analyze audio", type="primary"):
    if not url.strip():
        st.error("Please paste a YouTube URL first.")
    else:
        with st.spinner("Downloading, separating voice and music, and analysing... (about 2 minutes for a new video)"):
            data, error = call_backend("POST", "/audio/analyze", json={"youtube_url": url, "force_reanalyze": force})
        if error:
            st.error(error)
        else:
            st.session_state.audio_result = data

if st.session_state.get("audio_result"):
    show_result(st.session_state.audio_result)
