"""
Page 1: Affective Audio Analysis (descriptive).
What does the background audio of this video sound like, and where are the audio problems?

The backend answers in two phases: a quick "first look" on the mixed audio (~15 s), then the
voice/music separation runs in the background (~2 min). While it runs, this page shows a
progress panel that checks the backend every 3 s and refreshes itself when the result is ready.
"""
import json

import plotly.graph_objects as go
import streamlit as st

from common import (
    MUSIC_COLOR,
    QUADRANT_LABELS,
    SEVERITY_ICON,
    VOICE_COLOR,
    _layout,
    call_backend,
    emotion_timeline,
    mmss,
    quadrant_chart,
    time_axis,
)
from style import hero, loader_html, music_spinner


def loudness_chart(result: dict) -> go.Figure:
    """Loudness of the narration and of the background music per window, problems shaded."""
    segs = result["segments"]
    x = [(s["start_s"] + s["end_s"]) / 2 for s in segs]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=[s["speech_db"] for s in segs], name="Narration (voice)", mode="lines+markers",
                             line=dict(color=VOICE_COLOR, width=3, shape="spline")))
    fig.add_trace(go.Scatter(x=x, y=[s["music_db"] for s in segs], name="Background (music / sounds)", mode="lines+markers",
                             line=dict(color=MUSIC_COLOR, width=3, shape="spline"), fill="tozeroy",
                             fillcolor="rgba(167,139,250,0.10)"))
    for p in result["audio_problems"]:
        fig.add_vrect(x0=p["start_s"], x1=p["end_s"], fillcolor="#F43F5E", opacity=0.14, line_width=0,
                      annotation_text=p["type"].replace("_", " "), annotation_position="top left")
    lows = [s["speech_db"] for s in segs] + [s["music_db"] for s in segs]
    _layout(fig, 330, yaxis=dict(title="Loudness (dB, 0 = maximum)", range=[max(min(lows), -70) - 3, 0]))
    time_axis(fig, result["analyzed_seconds"])
    return fig


def show_sidebar():
    st.sidebar.header("🎵 Past audio analyses")
    items, error = call_backend("GET", "/audio/analyses")
    if error:
        st.sidebar.warning(error)
        return
    if not items:
        st.sidebar.caption("No analyses yet.")
    for item in items:
        vid = item["video_id"]
        open_col, delete_col = st.sidebar.columns([5, 1], vertical_alignment="center")
        if open_col.button(item["title"] or vid, key=f"a_{vid}", width="stretch"):
            data, error = call_backend("GET", f"/audio/analyses/{vid}")
            if error:
                st.sidebar.error(error)
            else:
                st.session_state.audio_result = data
        # The bin icon opens a small confirmation box, so nothing is deleted by one accidental click.
        with delete_col.popover("🗑", help="Delete this analysis"):
            st.write(f"Delete **{item['title'] or vid}** and its recommendations?")
            if st.button("Yes, delete", key=f"del_{vid}", type="primary"):
                delete_analysis(f"/audio/analyses/{vid}", vid)
    if items:
        with st.sidebar.popover("🗑 Delete all analyses", width="stretch"):
            st.write(f"Delete all **{len(items)}** saved analyses and their recommendations? This cannot be undone.")
            if st.button("Yes, delete all", key="del_all", type="primary"):
                delete_analysis("/audio/analyses", None)


def delete_analysis(path: str, video_id):
    """Ask the backend to delete, forget it on this page too, and redraw."""
    _, error = call_backend("DELETE", path)
    if error:
        st.sidebar.error(error)
        return
    shown = st.session_state.get("audio_result")
    if shown and (video_id is None or shown["video_id"] == video_id):
        st.session_state.audio_result = None
    report = st.session_state.get("report")
    if report and (video_id is None or report["video_id"] == video_id):
        st.session_state.report = None
    st.rerun()


@st.fragment(run_every=3)
def refinement_progress(video_id: str):
    """Runs every 3 s while the background separation works; refreshes the page when it is done."""
    data, error = call_backend("GET", f"/audio/analyses/{video_id}")
    if error:
        st.warning(error)
        return
    if data["status"] == "complete":
        st.session_state.audio_result = data
        st.rerun()                                   # redraw the whole page with the full result
    elif data["status"] == "failed":
        st.session_state.audio_result = data
        st.rerun()
    progress = data.get("progress") or 0.0
    st.markdown(loader_html(f"First look ready. Now separating the voice from the background music… "
                            f"{progress:.0%}  (about 2 minutes; this page updates by itself)"),
                unsafe_allow_html=True)
    st.progress(progress)


def show_result(r: dict):
    processing = r["status"] == "processing"

    # 1. Header
    st.header(r["title"] or r["video_id"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analysed", mmss(r["analyzed_seconds"]))
    c2.metric("10 s windows", len(r["segments"]))
    if processing:
        c3.metric("Voice loudness", "measuring…")
        c4.metric("Music loudness", "measuring…")
    else:
        c3.metric("Voice loudness", f"{r['separation']['speech_db']} dB")
        c4.metric("Music loudness", f"{r['separation']['music_db']} dB")
    if r["model_info"]["mock"]:
        st.warning("⚠️ MOCK MODEL: these emotion values are fake (random walk), used only to test the pipeline.")
    elif not processing:
        st.success(f"🎧 Model: {r['model_info']['embedding_model']} + {r['model_info']['head']}  ·  "
                   f"voice/music separation: {r['separation']['method']}")
    if r["status"] == "failed":
        st.error(r.get("error") or "The voice/music separation failed. Showing the first look on the mixed audio.")
    if processing:
        refinement_progress(r["video_id"])
    if r["separation"]["method"] == "none":
        st.info("Separation is switched off: the 'background music' below is the full mixed audio.")

    # 2. What the music sounds like (CLAP text matching)
    st.subheader("🎼 What the background music sounds like")
    if r["music_description"]:
        for item in r["music_description"]:
            st.progress(item["score"], text=f"**{item['label']}**: {item['score'] * 100:.0f}%")
        st.caption("CLAP compares the music with written descriptions and shows the closest matches."
                   + ("  (First look: still includes the voice.)" if processing else ""))
    else:
        st.caption("Not available with the mock model.")

    # 3. Emotion over time
    o, om = r["overall"], r["overall_mixed"]
    if processing:
        st.subheader("📈 Emotion over time (first look: voice + music together)")
        st.write(f"So far: **{QUADRANT_LABELS[o['dominant_quadrant']]}** "
                 f"(valence {o['mean_valence']:+.2f}, arousal {o['mean_arousal']:+.2f}). "
                 "The music-only result follows when the separation finishes.")
        st.plotly_chart(emotion_timeline(r["segments"], r["analyzed_seconds"]), width="stretch")
    else:
        st.subheader("📈 Emotion of the background music over time")
        st.write(f"Background music: **{QUADRANT_LABELS[o['dominant_quadrant']]}** "
                 f"(valence {o['mean_valence']:+.2f}, arousal {o['mean_arousal']:+.2f}).  "
                 f"Voice + music together: {QUADRANT_LABELS[om['dominant_quadrant']]} "
                 f"(valence {om['mean_valence']:+.2f}, arousal {om['mean_arousal']:+.2f}).")
        compare = st.checkbox("Also show voice + music together (dotted lines)", value=True)
        segs = r["segments"]
        st.plotly_chart(emotion_timeline(
            segs, r["analyzed_seconds"],
            compare=([s["mixed_valence"] for s in segs], [s["mixed_arousal"] for s in segs]) if compare else None,
            shaded=[(p["start_s"], p["end_s"], p["type"].replace("_", " ")) for p in r["audio_problems"]],
        ), width="stretch")

    left, right = st.columns(2)
    with left:
        st.markdown("**🧭 Valence–arousal map**")
        st.plotly_chart(quadrant_chart(r["segments"]), width="stretch")
    with right:
        st.markdown("**🔊 Loudness: voice vs. background**")
        if processing:
            st.markdown(loader_html("Measured after the voice and music are separated…"), unsafe_allow_html=True)
        else:
            st.plotly_chart(loudness_chart(r), width="stretch")
            st.caption("The background should stay well below the voice (more than 10 dB) so the narration is easy to follow.")

    # 4. Audio problems (measured)
    st.subheader("🚨 Audio problems found")
    if processing:
        st.caption("Distortion and silence are checked already; loudness under the voice follows after separation.")
    if not r["audio_problems"]:
        st.success("No loudness, distortion or silence problems were measured." if not processing else "None so far.")
    for i, p in enumerate(r["audio_problems"]):
        with st.container(key=f"card-{p['severity']}-p{i}"):
            link = f"{r['youtube_url']}&t={int(p['start_s'])}s"
            st.markdown(f"{SEVERITY_ICON.get(p['severity'], '')} **{p['description']}**  ·  "
                        f"{p['severity']} severity  ·  [▶ watch at {mmss(p['start_s'])}]({link})")
            for e in p["evidence"]:
                st.write(f"- {e}")

    # 5. Next step + download
    st.divider()
    st.session_state.selected_video = r["video_id"]
    if processing:
        st.caption("💡 The recommendations unlock when the separation is finished.")
    else:
        st.page_link("recommendations.py", label="See the recommendations for enhancements →", icon="💡")
    st.download_button("Download the analysis (JSON)", data=json.dumps(r, indent=2),
                       file_name=f"c4_audio_{r['video_id']}.json", mime="application/json")


hero("Affective Background Audio Analysis",
     "Separates the narration from the background music, then shows the music's emotion over time "
     "and measures audio problems (first 3 minutes of the video).", notes="♪ ♫ 𝄞 🎧")
show_sidebar()

url = st.text_input("🎬 YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
force = st.checkbox("Re-analyse even if a saved result exists")
if st.button("Analyze audio", type="primary"):
    if not url.strip():
        st.error("Please paste a YouTube URL first.")
    else:
        with music_spinner("Downloading the audio and taking a first listen… (about 15 seconds)"):
            data, error = call_backend("POST", "/audio/analyze", json={"youtube_url": url, "force_reanalyze": force})
        if error:
            st.error(error)
        else:
            st.session_state.audio_result = data

if st.session_state.get("audio_result"):
    show_result(st.session_state.audio_result)
