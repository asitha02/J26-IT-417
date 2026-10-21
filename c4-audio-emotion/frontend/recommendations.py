"""
Page 2: Content Enhancement Recommendations (descriptive + prescriptive).
Fuses the Part 1 audio analysis with the outputs of C1 (transcript sections), C2 (knowledge gaps)
and C3 (audience comments). Those three are DUMMY data until the components are connected.
"""
import json

import streamlit as st

from common import SEVERITY_ICON, SEVERITY_ORDER, call_backend, emotion_timeline, mmss

CONTENT_TYPE_ICON = {"hook": "🎬", "explanation": "📘", "example": "🧪", "summary": "📝"}


def pick_video():
    """Choose a video that already has a Part 1 result (Part 2 needs it as input)."""
    items, error = call_backend("GET", "/audio/analyses")
    if error:
        st.error(error)
        return None
    if not items:
        st.info("No audio analyses yet. Run Part 1 (Audio Analysis) for a video first.")
        return None
    ids = [i["video_id"] for i in items]
    titles = {i["video_id"]: i["title"] or i["video_id"] for i in items}
    preselected = st.session_state.get("selected_video")
    index = ids.index(preselected) if preselected in ids else 0
    return st.selectbox("Video (from Part 1)", ids, index=index, format_func=lambda v: titles[v])


def show_inputs(report: dict):
    inputs = report["inputs"]
    with st.expander("Inputs from the other components (DUMMY DATA, click to view)"):
        st.warning("C1, C2 and C3 are not connected yet. These inputs are made-up placeholders in the agreed "
                   "JSON format, used to demonstrate the fusion. They are not real transcripts, gaps or comments.")
        a, b, c = st.columns(3)
        with a:
            st.markdown("**C1 · transcript sections**")
            for sec in inputs["c1_input"].get("sections", []):
                st.write(f"- {mmss(sec['start_s'])}–{mmss(sec['end_s'])} {sec['content_type']}: {sec['topic']}")
        with b:
            st.markdown("**C2 · knowledge gaps**")
            for g in inputs["c2_input"].get("gaps", []) or [{"topic": "none"}]:
                st.write(f"- {g['topic']}" + (f" ({mmss(g['start_s'])}–{mmss(g['end_s'])})" if "start_s" in g else ""))
        with c:
            c3 = inputs["c3_input"]
            st.markdown("**C3 · audience comments**")
            st.write(f"Overall: {c3.get('sentiment_label')} ({c3.get('sentiment_score'):+.2f}, {c3.get('comment_count')} comments)")
            for cm in c3.get("timestamped_feedback", []):
                st.write(f"- {mmss(cm['t_s'])} '{cm['text']}' ({cm['sentiment']:+.1f})")
            st.caption("Requested topics: " + (", ".join(c3.get("requested_topics", [])) or "none"))


def show_descriptive(report: dict, analysis: dict):
    st.subheader("What happened, section by section (descriptive)")
    for s in report["section_summaries"]:
        with st.container(border=True):
            st.markdown(f"{CONTENT_TYPE_ICON.get(s['content_type'], '•')} **{mmss(s['start_s'])}–{mmss(s['end_s'])} · "
                        f"{s['topic']}** ({s['content_type']})")
            a, b, c = st.columns(3)
            a.caption(f"🎵 Music: {s['music_mood']}")
            b.caption(f"🔊 Loudness: {s['music_loudness']}")
            c.caption(f"💬 Negative comments: {s['negative_comments']}")
            for o in s["observations"]:
                st.write(f"- {o}")

    if analysis:
        st.markdown("**Background music over time, with the flagged sections and viewer comments**")
        whole = lambda r: r["start_s"] <= 0 and r["end_s"] >= analysis["analyzed_seconds"]
        fig = emotion_timeline(analysis["segments"], analysis["analyzed_seconds"],
                               shaded=[(r["start_s"], r["end_s"], r["id"]) for r in report["recommendations"] if not whole(r)])
        for cm in report["inputs"]["c3_input"].get("timestamped_feedback", []):
            fig.add_vline(x=cm["t_s"], line_dash="dash", line_color="red" if cm["sentiment"] < 0 else "green", opacity=0.6)
        st.plotly_chart(fig, width="stretch")
        st.caption("Yellow = flagged sections (rec ids) · dashed lines = viewer comments (red negative, green positive, dummy).")


def show_prescriptive(report: dict):
    st.subheader("What to change (prescriptive)")
    recs = sorted(report["recommendations"], key=lambda r: (SEVERITY_ORDER.get(r["severity"], 3), -r["confidence"]))
    if not recs:
        st.success("No recommendations: no rule was triggered for this video.")
    for r in recs:
        with st.container(border=True):
            whole = r["start_s"] <= 0
            when = "whole video" if whole and r["end_s"] >= 170 else f"{mmss(r['start_s'])}–{mmss(r['end_s'])}"
            st.markdown(f"{SEVERITY_ICON.get(r['severity'], '')} **{r['title']}**")
            st.caption(f"{when} · {r['severity']} severity · confidence {r['confidence']:.2f} · {r['id']} · rule {r['rule_id']}")
            st.markdown(f"**Suggestion:** {r['suggestion']}")
            st.markdown("**Why:**")
            for e in r["evidence"]:
                st.write(f"- {e}")
            if r.get("link"):
                st.markdown(f"[▶ Watch this moment on YouTube]({r['link']})")


def show_validation(report: dict):
    v = report["validation"]
    st.subheader("Do the flagged sections match what viewers complain about? (validation)")
    a, b, c, d = st.columns(4)
    a.metric("Flagged sections", v["flagged_segments"])
    b.metric("Agreement", "–" if v["agreement"] is None else f"{v['agreement']:.0%}")
    c.metric("Chance (random baseline)", "–" if v["random_baseline"] is None else f"{v['random_baseline']:.0%}")
    d.metric("Lift vs. chance", "–" if v["lift"] is None else f"{v['lift']:.1f}×")
    st.write(v["explanation"])
    if v["mock_data"]:
        st.warning("Computed on DUMMY C3 comments, so this only demonstrates the validation METHOD. "
                   "With Component 3's real comments it becomes the actual evaluation.")


st.title("Part 2 · Content Enhancement Recommendations")
st.caption("Combines the audio analysis (Part 1) with the transcript sections (C1), knowledge gaps (C2) and "
           "audience comments (C3) into a description of each section and ranked, explained recommendations.")

video_id = pick_video()
if video_id and st.button("Generate recommendations", type="primary"):
    with st.spinner("Combining all inputs..."):
        report, error = call_backend("POST", f"/recommendations/{video_id}")
    if error:
        st.error(error)
    else:
        st.session_state.report = report

report = st.session_state.get("report")
if report and report["video_id"] == video_id:
    analysis, _ = call_backend("GET", f"/audio/analyses/{video_id}")
    st.header(report["title"])
    st.markdown(f"[Open the video on YouTube]({report['youtube_url']})")
    show_inputs(report)
    show_descriptive(report, analysis)
    show_prescriptive(report)
    show_validation(report)
    st.download_button("Download JSON (Part 2)", data=json.dumps(report, indent=2),
                       file_name=f"c4_recommendations_{report['video_id']}.json", mime="application/json")
elif video_id:
    st.info("Click **Generate recommendations** to combine the inputs for this video.")
