"""
Look and feel: extra CSS on top of the theme in .streamlit/config.toml, a gradient page header,
and a music-themed loading animation (replaces Streamlit's swimming/cycling/running icons).

The CSS uses semi-transparent colours, so the same rules look right in light AND dark mode.
Streamlit elements are found by their fixed data-testid names (e.g. "stMetric").
"""
import html
from contextlib import contextmanager

import streamlit as st

CSS = """
<style>
/* ---------- background: soft violet / cyan glow, works in light and dark ---------- */
[data-testid="stAppViewContainer"] {
  background-image:
    radial-gradient(1200px 600px at 0% -10%, rgba(124, 58, 237, 0.20), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(6, 182, 212, 0.16), transparent 60%),
    radial-gradient(800px 600px at 50% 120%, rgba(236, 72, 153, 0.12), transparent 60%);
  background-attachment: fixed;
}
[data-testid="stSidebar"] {
  background-image: linear-gradient(180deg, rgba(124, 58, 237, 0.16), rgba(6, 182, 212, 0.08));
}

/* ---------- gradient page header ---------- */
.c4-hero {
  padding: 1.4rem 1.6rem; border-radius: 22px; margin-bottom: 1.2rem; color: #fff;
  background: linear-gradient(120deg, #7C3AED 0%, #4F46E5 40%, #06B6D4 75%, #EC4899 100%);
  background-size: 220% 220%; animation: c4-flow 12s ease infinite;
  box-shadow: 0 12px 40px rgba(124, 58, 237, 0.35);
}
.c4-hero h1 { margin: 0; font-size: 2.1rem; font-weight: 800; color: #fff; }
.c4-hero p  { margin: .35rem 0 0; opacity: .92; font-size: 1.02rem; }
.c4-hero .c4-notes { float: right; font-size: 2rem; opacity: .85; letter-spacing: .4rem; }
@keyframes c4-flow { 0% {background-position: 0% 50%} 50% {background-position: 100% 50%} 100% {background-position: 0% 50%} }

/* ---------- metric boxes ---------- */
[data-testid="stMetric"] {
  border-radius: 18px; padding: .8rem 1rem;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.14), rgba(6, 182, 212, 0.10));
  border: 1px solid rgba(124, 58, 237, 0.30);
}

/* ---------- buttons ---------- */
.stButton button[kind="primary"], .stDownloadButton button {
  background: linear-gradient(90deg, #7C3AED, #06B6D4); border: 0; color: #fff; font-weight: 700;
  box-shadow: 0 6px 20px rgba(124, 58, 237, 0.35); transition: transform .15s ease;
}
.stButton button[kind="primary"]:hover, .stDownloadButton button:hover { transform: translateY(-1px) scale(1.02); color: #fff; }

/* ---------- cards (st.container(key="card-...")) ---------- */
[class*="st-key-card"] {
  border-radius: 18px; padding: .9rem 1.1rem; border: 1px solid rgba(124, 58, 237, 0.28);
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(6, 182, 212, 0.05));
}
[class*="st-key-card-high"]   { border-left: 6px solid #F43F5E; }
[class*="st-key-card-medium"] { border-left: 6px solid #F59E0B; }
[class*="st-key-card-low"]    { border-left: 6px solid #10B981; }

/* ---------- featured "top priority" card ---------- */
.c4-featured {
  border-radius: 22px; padding: 1.3rem 1.5rem; margin: .4rem 0 1rem; color: #fff;
  background: linear-gradient(125deg, #BE185D, #7C3AED 55%, #2563EB);
  box-shadow: 0 14px 44px rgba(190, 24, 93, 0.35); position: relative; overflow: hidden;
}
.c4-featured .c4-badge { display: inline-block; background: rgba(255,255,255,.2); padding: .2rem .7rem;
  border-radius: 999px; font-size: .8rem; font-weight: 700; letter-spacing: .05rem; }
.c4-featured h3 { color: #fff; margin: .5rem 0 .2rem; font-size: 1.45rem; }
.c4-featured .c4-when { opacity: .9; font-size: .92rem; }
.c4-featured .c4-tip { background: rgba(255,255,255,.14); border-radius: 14px; padding: .7rem .9rem; margin-top: .8rem; }
.c4-featured ul { margin: .4rem 0 0 1.1rem; }
.c4-featured a { color: #fff; font-weight: 700; text-decoration: underline; }
.c4-featured::after { content: "♫"; position: absolute; right: 1.2rem; bottom: -1.2rem; font-size: 7rem; opacity: .12; }

/* ---------- plain-language summary lines ---------- */
.c4-summary { border-radius: 18px; padding: 1rem 1.2rem; margin-bottom: .8rem;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.12), rgba(124, 58, 237, 0.10));
  border: 1px solid rgba(6, 182, 212, 0.30); font-size: 1.04rem; line-height: 1.75; }

/* ---------- music-note loading animation ---------- */
.c4-loader { display: flex; align-items: center; gap: 1rem; padding: .9rem 1.1rem; border-radius: 18px;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.14), rgba(236, 72, 153, 0.10));
  border: 1px solid rgba(124, 58, 237, 0.30); margin: .5rem 0; }
.c4-loader .c4-eq { display: flex; align-items: flex-end; gap: 4px; height: 34px; }
.c4-loader .c4-eq span { width: 6px; border-radius: 3px; background: linear-gradient(#22D3EE, #A78BFA);
  animation: c4-eq 0.9s ease-in-out infinite; }
.c4-loader .c4-eq span:nth-child(2) { animation-delay: .15s } .c4-loader .c4-eq span:nth-child(3) { animation-delay: .3s }
.c4-loader .c4-eq span:nth-child(4) { animation-delay: .45s } .c4-loader .c4-eq span:nth-child(5) { animation-delay: .6s }
@keyframes c4-eq { 0%, 100% { height: 6px } 50% { height: 34px } }
.c4-loader .c4-float { font-size: 1.7rem; display: flex; gap: .45rem; }
.c4-loader .c4-float span { display: inline-block; animation: c4-bounce 1.4s ease-in-out infinite; }
.c4-loader .c4-float span:nth-child(2) { animation-delay: .2s } .c4-loader .c4-float span:nth-child(3) { animation-delay: .4s }
.c4-loader .c4-float span:nth-child(4) { animation-delay: .6s } .c4-loader .c4-float span:nth-child(5) { animation-delay: .8s }
@keyframes c4-bounce { 0%, 100% { transform: translateY(0) rotate(0) } 50% { transform: translateY(-9px) rotate(-10deg) } }
.c4-loader .c4-text { font-weight: 600; }

/* ---------- replace Streamlit's running icons (swimmer, cyclist, runner) with music symbols ---------- */
[data-testid="stStatusWidgetRunningIcon"] > * { display: none !important; }
[data-testid="stStatusWidgetRunningIcon"]::after {
  content: "♪"; font-size: 1.25rem; line-height: 1; display: inline-block; color: #A78BFA;
  animation: c4-symbols 2.4s steps(1) infinite, c4-bounce 0.8s ease-in-out infinite;
}
@keyframes c4-symbols { 0% {content: "♪"} 20% {content: "♫"} 40% {content: "♬"} 60% {content: "𝄞"} 80% {content: "🎧"} }
[data-testid="stSpinnerIcon"] { display: none !important; }
[data-testid="stSpinner"] > div::before { content: "♪"; margin-right: .4rem; display: inline-block;
  animation: c4-symbols 2.4s steps(1) infinite, c4-bounce 0.8s ease-in-out infinite; }
</style>
"""


def apply_style() -> None:
    """Add the extra CSS to the page (call once per page run)."""
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, notes: str = "♪ ♫ 𝄞") -> None:
    """Animated gradient header at the top of a page."""
    st.markdown(f'<div class="c4-hero"><span class="c4-notes">{notes}</span><h1>{html.escape(title)}</h1>'
                f'<p>{html.escape(subtitle)}</p></div>', unsafe_allow_html=True)


def loader_html(text: str) -> str:
    """Equaliser bars + bouncing music symbols with a message."""
    return ('<div class="c4-loader"><div class="c4-eq"><span></span><span></span><span></span><span></span><span></span></div>'
            '<div class="c4-float"><span>♪</span><span>♫</span><span>𝄞</span><span>♬</span><span>🎧</span></div>'
            f'<div class="c4-text">{html.escape(text)}</div></div>')


@contextmanager
def music_spinner(text: str):
    """Use like st.spinner: shows the music animation while the block inside runs."""
    placeholder = st.empty()
    placeholder.markdown(loader_html(text), unsafe_allow_html=True)
    try:
        yield
    finally:
        placeholder.empty()
