"""
Page 2: Content Enhancement Recommendations (descriptive + prescriptive), written for content creators.
Fuses the Part 1 audio analysis with the outputs of C1 (transcript sections), C2 (knowledge gaps)
and C3 (audience comments). Those three are DUMMY data until the components are connected.

Layout: plain-language summary -> donut charts -> TOP PRIORITY card -> checklist -> all cards
        -> section-by-section details -> validation.
"""
import html
import json

import streamlit as st

from common import (
    QUADRANT_COLOR,
    QUADRANT_LABELS,
    SEVERITY_COLOR,
    SEVERITY_ICON,
    SEVERITY_ORDER,
    call_backend,
    donut,
    emotion_timeline,
    mmss,
)
from style import hero, music_spinner

CONTENT_TYPE_ICON = {"hook": "🎬", "explanation": "📘", "example": "🧪", "summary": "📝"}
# Recommendation type -> simple category for creators (and its colour in the donut).
CATEGORY = {
    "music_too_loud": "Music too loud", "audio_complaints": "Music too loud",
    "low_energy_segment": "Music energy", "tense_audio_segment": "Music energy", "flat_energy_profile": "Music energy",
    "intense_audio_complex_content": "Music vs. content", "mood_content_mismatch": "Music vs. content",
    "distortion": "Sound quality", "dead_air": "Sound quality",
    "requested_topics": "Viewer requests",
}
CATEGORY_COLOR = {"Music too loud": "#F43F5E", "Music energy": "#A78BFA", "Music vs. content": "#EC4899",
                  "Sound quality": "#F59E0B", "Viewer requests": "#22D3EE"}


def sorted_recs(report):
    return sorted(report["recommendations"], key=lambda r: (SEVERITY_ORDER.get(r["severity"], 3), -r["confidence"]))


def when(r, analysis):
    end = analysis["analyzed_seconds"] if analysis else 180
    return "the whole video" if r["start_s"] <= 0 and r["end_s"] >= end else f"{mmss(r['start_s'])}–{mmss(r['end_s'])}"


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
    return st.selectbox("🎬 Video (from Part 1)", ids, index=index, format_func=lambda v: titles[v])


# ---------- 1. plain-language summary ----------

def show_summary(report, analysis):
    recs = sorted_recs(report)
    lines = []
    if recs:
        urgent = sum(r["severity"] == "high" for r in recs)
        lines.append(f"🎯 We found <b>{len(recs)} things to improve</b> in the first 3 minutes"
                     + (f", <b>{urgent} of them urgent</b>." if urgent else "."))
        lines.append(f"⭐ Start with: <b>{html.escape(recs[0]['title'])}</b>.")
    else:
        lines.append("🎉 Nothing to fix: no problems were found in the first 3 minutes.")
    if analysis:
        o = analysis["overall"]
        sound = analysis["music_description"][0]["label"] if analysis["music_description"] else None
        lines.append(f"🎵 Your background music feels mostly <b>{QUADRANT_LABELS[o['dominant_quadrant']].lower()}</b>"
                     + (f" and sounds like <b>{html.escape(sound)}</b>." if sound else "."))
        loud = [p for p in analysis["audio_problems"] if p["type"] == "music_too_loud"]
        lines.append("🔊 " + (f"The background is too loud under your voice during "
                              f"<b>{', '.join(mmss(p['start_s']) + '–' + mmss(p['end_s']) for p in loud)}</b>."
                              if loud else "Your voice stays clearly above the background music. 👍"))
    c3 = report["inputs"]["c3_input"]
    negative = [c for c in c3.get("timestamped_feedback", []) if c["sentiment"] < 0]
    v = report["validation"]
    if negative:
        lines.append(f"💬 Viewers left <b>{len(negative)} negative comment(s)</b> at specific moments; "
                     f"<b>{v['comments_explained']}</b> of them line up with a problem we found.")
    gaps = report["inputs"]["c2_input"].get("gaps", [])
    if gaps:
        lines.append("📚 Mentioned but not explained: <b>" + ", ".join(html.escape(g["topic"]) for g in gaps) + "</b>.")
    st.markdown('<div class="c4-summary">' + "<br>".join(lines) + "</div>", unsafe_allow_html=True)
    st.caption("Viewer comments, transcript sections and knowledge gaps are DUMMY data until Components 1–3 are connected.")


# ---------- 2. donut charts ----------

def show_donuts(report, analysis):
    recs = report["recommendations"]
    cols = st.columns(4)
    with cols[0]:
        st.markdown("**What needs attention**")
        counts = {}
        for r in recs:
            counts[CATEGORY.get(r["type"], "Other")] = counts.get(CATEGORY.get(r["type"], "Other"), 0) + 1
        if counts:
            st.plotly_chart(donut(list(counts), list(counts.values()),
                                  [CATEGORY_COLOR.get(k, "#94A3B8") for k in counts], f"{len(recs)}<br>fixes"),
                            width="stretch", key="d_cat")
    with cols[1]:
        st.markdown("**How urgent**")
        sev = [s for s in ("high", "medium", "low") if any(r["severity"] == s for r in recs)]
        if sev:
            st.plotly_chart(donut([s.capitalize() for s in sev], [sum(r["severity"] == s for r in recs) for s in sev],
                                  [SEVERITY_COLOR[s] for s in sev], "urgency"), width="stretch", key="d_sev")
    with cols[2]:
        st.markdown("**Music mood (share of time)**")
        if analysis:
            q = [s["quadrant"] for s in analysis["segments"]]
            keys = [k for k in QUADRANT_LABELS if k in q]
            st.plotly_chart(donut([QUADRANT_LABELS[k] for k in keys], [q.count(k) for k in keys],
                                  [QUADRANT_COLOR[k] for k in keys], "🎵 mood"), width="stretch", key="d_mood")
    with cols[3]:
        st.markdown("**What viewers felt** (dummy)")
        fb = report["inputs"]["c3_input"].get("timestamped_feedback", [])
        pos, neg = sum(c["sentiment"] >= 0 for c in fb), sum(c["sentiment"] < 0 for c in fb)
        if fb:
            st.plotly_chart(donut(["Positive", "Negative"], [pos, neg], ["#10B981", "#F43F5E"], "💬 comments"),
                            width="stretch", key="d_c3")


# ---------- 3. top priority + checklist + all cards ----------

def show_top_priority(report, analysis):
    recs = sorted_recs(report)
    if not recs:
        return
    top = recs[0]
    why = "".join(f"<li>{html.escape(e)}</li>" for e in top["evidence"][:4])
    link = f'<a href="{html.escape(top["link"])}" target="_blank">▶ Watch this moment</a>' if top.get("link") else ""
    st.markdown(
        f'<div class="c4-featured"><span class="c4-badge">⭐ TOP PRIORITY · {top["severity"].upper()} · '
        f'confidence {top["confidence"]:.2f}</span>'
        f'<h3>{html.escape(top["title"])}</h3><div class="c4-when">⏱ {when(top, analysis)} &nbsp; {link}</div>'
        f'<div class="c4-tip">💡 <b>What to do:</b> {html.escape(top["suggestion"])}</div>'
        f'<div style="margin-top:.6rem"><b>Why we think so:</b><ul>{why}</ul></div></div>',
        unsafe_allow_html=True)


def show_checklist(report, analysis):
    recs = sorted_recs(report)
    if len(recs) < 2:
        return
    st.subheader("✅ Your quick checklist")
    for r in recs:
        link = f" · [▶ watch]({r['link']})" if r.get("link") else ""
        st.markdown(f"{SEVERITY_ICON.get(r['severity'], '')} **{when(r, analysis)}**: {r['suggestion']}{link}")


def show_all_cards(report, analysis):
    st.subheader("🛠 Every recommendation, with the evidence")
    for i, r in enumerate(sorted_recs(report)):
        with st.container(key=f"card-{r['severity']}-r{i}"):
            st.markdown(f"{SEVERITY_ICON.get(r['severity'], '')} **{r['title']}**")
            st.caption(f"⏱ {when(r, analysis)} · {r['severity']} severity · confidence {r['confidence']:.2f} · "
                       f"{r['id']} · rule {r['rule_id']}")
            st.markdown(f"💡 **What to do:** {r['suggestion']}")
            for e in r["evidence"]:
                st.write(f"- {e}")
            if r.get("link"):
                st.markdown(f"[▶ Watch this moment on YouTube]({r['link']})")


# ---------- 4. descriptive details + validation ----------

def show_sections(report, analysis):
    with st.expander("📖 What happened, section by section (descriptive details)", expanded=False):
        for i, s in enumerate(report["section_summaries"]):
            with st.container(key=f"card-sec-{i}"):
                st.markdown(f"{CONTENT_TYPE_ICON.get(s['content_type'], '•')} **{mmss(s['start_s'])}–{mmss(s['end_s'])} · "
                            f"{s['topic']}** ({s['content_type']})")
                a, b, c = st.columns(3)
                a.caption(f"🎵 Music: {s['music_mood']}")
                b.caption(f"🔊 Loudness: {s['music_loudness']}")
                c.caption(f"💬 Negative comments: {s['negative_comments']}")
                for o in s["observations"]:
                    st.write(f"- {o}")
        if analysis:
            whole = lambda r: r["start_s"] <= 0 and r["end_s"] >= analysis["analyzed_seconds"]
            fig = emotion_timeline(analysis["segments"], analysis["analyzed_seconds"],
                                   shaded=[(r["start_s"], r["end_s"], r["id"]) for r in report["recommendations"] if not whole(r)])
            for cm in report["inputs"]["c3_input"].get("timestamped_feedback", []):
                fig.add_vline(x=cm["t_s"], line_dash="dash", line_color="#F43F5E" if cm["sentiment"] < 0 else "#10B981",
                              opacity=0.7)
            st.plotly_chart(fig, width="stretch", key="sec_timeline")
            st.caption("Highlighted = flagged sections (rec ids) · dashed lines = viewer comments (red negative, green positive; dummy).")


def show_validation(report):
    v = report["validation"]
    with st.expander("🔬 Validation: do the flagged moments match what viewers complain about?", expanded=False):
        a, b, c, d = st.columns(4)
        a.metric("Flagged sections", v["flagged_segments"])
        b.metric("Agreement", "–" if v["agreement"] is None else f"{v['agreement']:.0%}")
        c.metric("Chance (random)", "–" if v["random_baseline"] is None else f"{v['random_baseline']:.0%}")
        d.metric("Lift vs. chance", "–" if v["lift"] is None else f"{v['lift']:.1f}×")
        st.write(v["explanation"])
        if v["mock_data"]:
            st.warning("Computed on DUMMY C3 comments, so this only demonstrates the validation METHOD. "
                       "With Component 3's real comments it becomes the actual evaluation.")


def show_inputs(report):
    inputs = report["inputs"]
    with st.expander("🧩 Inputs from the other components (DUMMY DATA)"):
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


hero("Part 2 · Content Enhancement Recommendations",
     "Your audio analysis combined with the transcript, knowledge gaps and viewer comments: "
     "what happened, what to fix first, and why.", notes="💡 ♫ ⭐")

video_id = pick_video()
if video_id and st.button("Generate recommendations", type="primary"):
    with music_spinner("Combining the audio analysis with the transcript, knowledge gaps and comments…"):
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
    show_summary(report, analysis)
    show_donuts(report, analysis)
    show_top_priority(report, analysis)
    show_checklist(report, analysis)
    show_all_cards(report, analysis)
    show_sections(report, analysis)
    show_validation(report)
    show_inputs(report)
    st.download_button("Download JSON (Part 2)", data=json.dumps(report, indent=2),
                       file_name=f"c4_recommendations_{report['video_id']}.json", mime="application/json")
elif video_id:
    st.info("Click **Generate recommendations** to combine the inputs for this video.")
