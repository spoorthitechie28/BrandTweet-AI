"""
BrandTweet AI - Streamlit interface.

Run locally with:
    streamlit run app.py
"""

from __future__ import annotations

import html
import os
import re
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from brandtweet import (
    DEFAULT_MODEL,
    OBJECTIVES,
    TONES,
    TWEET_LIMIT,
    BrandBrief,
    BrandTweetError,
    Tweet,
    VoiceProfile,
    generate_tweets,
    infer_brand_voice,
    validate_brief,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

AUTO_TONE = "Auto \u2014 infer tone"
APP_TITLE = "BrandTweet AI"


def _read_setting(name: str) -> str:
    """Read a Streamlit secret first, then an environment variable."""
    value = ""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        # st.secrets raises when no secrets.toml exists; that is expected locally.
        value = ""
    if not value:
        value = os.getenv(name, "")
    return str(value or "").strip()


API_KEY = _read_setting("OPENAI_API_KEY")
MODEL = _read_setting("OPENAI_MODEL") or DEFAULT_MODEL
API_READY = bool(API_KEY)

PRESETS: dict[str, dict[str, str]] = {
    "Zomato": {
        "brand_name": "Zomato",
        "industry": "Food delivery and restaurant discovery",
        "objective": "Engagement",
        "description": (
            "A food delivery and restaurant discovery app that helps people find "
            "nearby restaurants, read reviews, and order everyday meals."
        ),
        "audience": (
            "Urban food lovers, students, and young professionals who order meals "
            "online and enjoy discovering local restaurants."
        ),
        "tone": "Witty",
        "instructions": (
            "Keep it playful but not try-hard. Food humour is welcome. Avoid "
            "inventing offers, discounts, or delivery statistics."
        ),
    },
    "Apple": {
        "brand_name": "Apple",
        "industry": "Consumer technology",
        "objective": "Brand Awareness",
        "description": (
            "Consumer technology built around simple design, privacy, and creative "
            "work, including iPhone, Mac, iPad, and services."
        ),
        "audience": (
            "Design-conscious consumers, creative professionals, and everyday "
            "technology users who value simplicity and privacy."
        ),
        "tone": "Premium",
        "instructions": (
            "Calm, confident, and restrained. No exclamation marks and no emojis. "
            "Short declarative lines. Do not invent product specs or launch dates."
        ),
    },
}

WIDGET_KEYS = (
    "brand_name",
    "industry",
    "objective",
    "description",
    "audience",
    "tone",
    "instructions",
)


def current_form_keys() -> dict[str, str]:
    """
    Versioned widget keys.

    Streamlit keeps a widget's value on the client for the current run. If we
    only delete the key, the old value can come straight back. Incrementing the
    version gives every field a genuinely fresh key, so "Start Over" actually
    empties the form. Preset loaders write to the current version's keys.
    """
    version = st.session_state.setdefault("form_version", 0)
    return {name: f"{name}_{version}" for name in WIDGET_KEYS}


# ---------------------------------------------------------------------------
# Page setup and styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="\u2726",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1100px 380px at 12% -12%, rgba(99, 102, 241, .10), transparent 62%),
        #F6F7FB;
}
header[data-testid="stHeader"] { display: none; }
[data-testid="stToolbar"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"] { display: none !important; }
.block-container {
    max-width: 1180px;
    padding-top: 1.6rem;
    padding-bottom: 3rem;
}
#MainMenu, footer { visibility: hidden; }

h1, h2, h3, h4 {
    font-family: 'Inter', sans-serif;
    color: #0B1220;
    letter-spacing: -0.02em;
}

/* ---------- Hero ---------- */
.hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #0B1220 0%, #171B3D 55%, #312E81 100%);
    border-radius: 24px;
    padding: 2.1rem 2.3rem 1.9rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 20px 45px rgba(15, 23, 42, .18);
}
.hero::after {
    content: "";
    position: absolute;
    width: 380px;
    height: 380px;
    right: -120px;
    top: -170px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(124, 58, 237, .55), transparent 65%);
}
.hero-top {
    display: flex;
    align-items: center;
    gap: .75rem;
    margin-bottom: 1.1rem;
    position: relative;
    z-index: 1;
}
.brandmark {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #818CF8, #C084FC);
    color: #0B1220;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: .9rem;
    letter-spacing: -.03em;
}
.hero-badge {
    font-size: .68rem;
    letter-spacing: .16em;
    font-weight: 700;
    color: #C7D2FE;
    border: 1px solid rgba(199, 210, 254, .35);
    padding: .32rem .65rem;
    border-radius: 999px;
}
.hero h1 {
    color: #FFFFFF;
    font-size: 3.1rem;
    line-height: 1.02;
    margin: 0 0 .6rem;
    font-weight: 800;
    letter-spacing: -.045em;
    position: relative;
    z-index: 1;
}
.hero h1 .accent {
    background: linear-gradient(90deg, #A5B4FC, #E9D5FF);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}
.hero-sub {
    color: #CBD5E1;
    font-size: 1.08rem;
    max-width: 660px;
    margin: 0 0 1.2rem;
    line-height: 1.6;
    position: relative;
    z-index: 1;
}
.hero-pills {
    display: flex;
    flex-wrap: wrap;
    gap: .5rem;
    position: relative;
    z-index: 1;
}
.hero-pills span {
    font-size: .76rem;
    font-weight: 600;
    color: #E2E8F0;
    background: rgba(255, 255, 255, .08);
    border: 1px solid rgba(255, 255, 255, .12);
    padding: .36rem .7rem;
    border-radius: 999px;
}

/* ---------- Form ---------- */
div[data-testid="stForm"] {
    background: #FFFFFF;
    border: 1px solid #E6E9F2;
    border-radius: 18px;
    padding: 1.3rem 1.3rem 1.1rem;
    box-shadow: 0 10px 30px rgba(15, 23, 42, .05);
}
.form-title {
    font-size: 1.32rem;
    font-weight: 750;
    color: #0B1220;
    letter-spacing: -.02em;
    margin: 0 0 .1rem;
}
.form-caption {
    color: #64748B;
    font-size: .84rem;
    margin: 0 0 1rem;
}
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] label {
    font-size: .8rem !important;
    font-weight: 650 !important;
    color: #334155 !important;
}
div[data-testid="stCaptionContainer"] p {
    color: #64748B;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background: #FBFCFE !important;
    color: #0F172A !important;
    border-radius: 10px !important;
    font-size: .92rem !important;
}
div[data-baseweb="input"],
div[data-baseweb="textarea"],
div[data-baseweb="select"] > div {
    background: #FBFCFE !important;
    border-color: #DDE3EE !important;
    border-radius: 10px !important;
}
div[data-baseweb="select"] > div { min-height: 42px; }
div[data-baseweb="popover"] li { font-size: .9rem; }

div[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #4F46E5, #6D28D9) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 11px !important;
    min-height: 47px;
    font-weight: 700 !important;
    font-size: .98rem !important;
    box-shadow: 0 10px 24px rgba(79, 70, 229, .25) !important;
    transition: box-shadow .15s ease, filter .15s ease;
}
div[data-testid="stFormSubmitButton"] button:hover {
    filter: brightness(1.06);
    box-shadow: 0 13px 30px rgba(79, 70, 229, .32) !important;
}
div[data-testid="stFormSubmitButton"] button:disabled {
    background: #E2E8F0 !important;
    box-shadow: none !important;
    color: #64748B !important;
}

/* ---------- Cards and buttons ---------- */
/* Streamlit 1.66 marks a bordered st.container with these data attributes. */
div[data-testid="stVerticalBlock"][data-test-scroll-behavior] {
    background: #FFFFFF;
    border: 1px solid #E6E9F2 !important;
    border-radius: 16px !important;
    padding: 1rem 1.05rem .8rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, .035);
    transition: box-shadow .15s ease, border-color .15s ease;
}
div[data-testid="stVerticalBlock"][data-test-scroll-behavior]:hover {
    border-color: #D5DAE8 !important;
    box-shadow: 0 10px 26px rgba(15, 23, 42, .07);
}

div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {
    border-radius: 10px;
    border: 1px solid #DDE3EE;
    background: #FFFFFF;
    color: #1E293B;
    font-weight: 600;
    min-height: 42px;
    transition: border-color .15s ease, color .15s ease, background .15s ease;
}
div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {
    border-color: #A5B4FC;
    color: #4338CA;
    background: #F8FAFF;
}

/* ---------- Tweet cards ---------- */
.tweet-meta {
    display: flex;
    align-items: center;
    gap: .45rem;
    margin: .1rem 0 .15rem;
    flex-wrap: wrap;
}
.tweet-no {
    font-size: .7rem;
    font-weight: 800;
    letter-spacing: .13em;
    color: #4F46E5;
    text-transform: uppercase;
}
.angle-pill {
    font-size: .67rem;
    font-weight: 700;
    letter-spacing: .03em;
    color: #475569;
    background: #F1F5F9;
    border: 1px solid #E2E8F0;
    border-radius: 999px;
    padding: .15rem .5rem;
}
.char-pill {
    margin-left: auto;
    font-size: .71rem;
    font-weight: 650;
    color: #047857;
    background: #ECFDF5;
    border: 1px solid #D1FAE5;
    border-radius: 999px;
    padding: .15rem .48rem;
    font-variant-numeric: tabular-nums;
}

div[data-testid="stCode"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}
div[data-testid="stCode"] pre {
    background: transparent !important;
    padding: .4rem 1.8rem .1rem 0 !important;
    margin: 0 !important;
    white-space: pre-wrap !important;
    overflow-x: visible !important;
}
div[data-testid="stCode"] code {
    font-family: 'Inter', sans-serif !important;
    font-size: 1rem !important;
    line-height: 1.62 !important;
    color: #1E293B !important;
    white-space: pre-wrap !important;
    word-break: break-word !important;
}
div[data-testid="stCode"] > div:last-child {
    opacity: 1 !important;
    visibility: visible !important;
}
div[data-testid="stCode"] button {
    opacity: 1 !important;
    visibility: visible !important;
    color: #64748B !important;
    background: #F1F5F9 !important;
    border-radius: 7px !important;
}
div[data-testid="stCode"] button:hover {
    color: #4338CA !important;
    background: #EEF2FF !important;
}

/* ---------- Voice profile ---------- */
.voice-card {
    background: #FFFFFF;
    border: 1px solid #E6E9F2;
    border-radius: 18px;
    padding: 1.35rem 1.5rem 1.2rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, .035);
    margin: .2rem 0 1.6rem;
}
.voice-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
}
.eyebrow {
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .16em;
    color: #6366F1;
    margin: 0 0 .35rem;
}
.voice-card h3 {
    margin: 0;
    font-size: 1.26rem;
}
.ai-badge {
    font-size: .68rem;
    font-weight: 700;
    color: #4338CA;
    background: #EEF2FF;
    border: 1px solid #E0E7FF;
    border-radius: 999px;
    padding: .3rem .62rem;
    white-space: nowrap;
}
.chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: .4rem;
    margin: .9rem 0 1rem;
}
.chip {
    font-size: .72rem;
    font-weight: 600;
    color: #475569;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 999px;
    padding: .28rem .6rem;
}
.voice-list {
    margin: 0;
    padding-left: 1.1rem;
}
.voice-list li {
    color: #334155;
    font-size: .94rem;
    line-height: 1.62;
    margin-bottom: .35rem;
}
.voice-note {
    margin: .9rem 0 0;
    font-size: .74rem;
    color: #94A3B8;
    line-height: 1.5;
    border-top: 1px solid #F1F5F9;
    padding-top: .75rem;
}

/* ---------- Results header ---------- */
.results-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    margin: 2rem 0 .3rem;
}
.results-head h2 {
    margin: 0;
    font-size: 1.8rem;
}
.results-meta {
    color: #64748B;
    font-size: .83rem;
    margin: .2rem 0 1rem;
}
.set-badge {
    font-size: .7rem;
    font-weight: 750;
    letter-spacing: .06em;
    color: #4338CA;
    background: #EEF2FF;
    border: 1px solid #E0E7FF;
    border-radius: 999px;
    padding: .34rem .65rem;
    white-space: nowrap;
}
.tweets-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin: 1.7rem 0 .7rem;
}
.tweets-head h3 {
    margin: 0;
    font-size: 1.18rem;
}
.tweets-head p {
    margin: 0;
    color: #94A3B8;
    font-size: .76rem;
}

/* ---------- Side panel ---------- */
.side-card {
    background: #FFFFFF;
    border: 1px solid #E6E9F2;
    border-radius: 18px;
    padding: 1.25rem 1.3rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, .035);
    margin-bottom: 1rem;
}
.side-kicker {
    font-size: .66rem;
    font-weight: 800;
    letter-spacing: .16em;
    color: #6366F1;
    margin: 0 0 .9rem;
}
.step {
    display: flex;
    gap: .7rem;
    margin-bottom: .95rem;
}
.step:last-child { margin-bottom: 0; }
.step-num {
    flex: 0 0 auto;
    width: 24px;
    height: 24px;
    border-radius: 7px;
    background: #EEF2FF;
    color: #4338CA;
    font-size: .68rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
}
.step strong {
    display: block;
    font-size: .86rem;
    color: #1E293B;
    margin-bottom: .1rem;
}
.step p {
    margin: 0;
    font-size: .78rem;
    line-height: 1.5;
    color: #64748B;
}

/* ---------- Config warning ---------- */
.config-warning {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-left: 4px solid #F59E0B;
    color: #78350F;
    padding: .95rem 1.05rem;
    border-radius: 12px;
    font-size: .89rem;
    line-height: 1.55;
    margin-bottom: 1.2rem;
}
.config-warning code {
    background: #FEF3C7;
    color: #92400E;
    padding: .08rem .3rem;
    border-radius: 5px;
    font-size: .84rem;
}

/* ---------- Footer ---------- */
.app-footer {
    margin-top: 2.6rem;
    padding-top: 1rem;
    border-top: 1px solid #E6E9F2;
    display: flex;
    justify-content: space-between;
    gap: .7rem;
    flex-wrap: wrap;
    color: #94A3B8;
    font-size: .74rem;
}

@media (max-width: 780px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    .hero { padding: 1.5rem 1.3rem 1.4rem; border-radius: 18px; }
    .hero h1 { font-size: 2.35rem; }
    .hero-sub { font-size: .98rem; }
    .results-head { align-items: flex-start; flex-direction: column; gap: .4rem; }
    .voice-card { padding: 1.1rem; }
    .tweets-head { flex-direction: column; gap: .15rem; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Small UI helpers
# ---------------------------------------------------------------------------


def load_preset(name: str) -> None:
    keys = current_form_keys()
    st.session_state.update(
        {keys[field]: value for field, value in PRESETS[name].items()}
    )
    st.session_state.pop("result", None)
    st.session_state["set_number"] = 0


def reset_app() -> None:
    # A new form version means every field gets a fresh, empty widget key.
    # We intentionally do not delete the old widget keys here: Streamlit does
    # not allow modifying a widget's state after it has been instantiated in
    # the current run. The stale keys are harmless and hold only old text.
    st.session_state["form_version"] = st.session_state.get("form_version", 0) + 1
    st.session_state.pop("result", None)
    st.session_state["set_number"] = 0


def tone_value(label: str) -> str:
    return "" if label == AUTO_TONE else label


def render_header() -> None:
    st.markdown(
        """
<div class="hero">
  <div class="hero-top">
    <div class="brandmark">BT</div>
    <span class="hero-badge">AI MARKETING STUDIO</span>
  </div>
  <h1>BrandTweet <span class="accent">AI</span></h1>
  <p class="hero-sub">
    Turn a brand brief into ten tweets that sound like the brand wrote them.
    A two-stage AI pipeline infers the voice, then writes a campaign-ready set for X.
  </p>
  <div class="hero-pills">
    <span>Two-stage voice inference</span>
    <span>10 distinct posts</span>
    <span>280-character limit</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_config_warning() -> None:
    st.markdown(
        """
<div class="config-warning">
  <strong>OpenAI API key not configured.</strong>
  Add <code>OPENAI_API_KEY</code> to your <code>.env</code> file locally, or to your
  Streamlit app secrets when deployed, then reload this page. Generation is disabled
  until a valid key is available. The app never shows mock output as if it were AI-generated.
</div>
""",
        unsafe_allow_html=True,
    )
    with st.expander("How to configure the key"):
        st.markdown("**Local development** — create a file named `.env` in the project folder:")
        st.code("OPENAI_API_KEY=sk-your-key-here\nOPENAI_MODEL=gpt-4.1-mini", language="bash")
        st.markdown("**Streamlit Community Cloud** — open *App settings → Secrets* and paste:")
        st.code('OPENAI_API_KEY = "sk-your-key-here"\nOPENAI_MODEL = "gpt-4.1-mini"', language="toml")
        st.caption("Never commit the real key to GitHub. `.env` and `.streamlit/secrets.toml` are git-ignored.")


def render_side_panel() -> None:
    st.markdown(
        """
<div class="side-card">
  <p class="side-kicker">HOW IT WORKS</p>
  <div class="step">
    <span class="step-num">01</span>
    <div><strong>Describe the brand</strong>
      <p>Product, audience and campaign goal. A brand name helps, but it is optional.</p>
    </div>
  </div>
  <div class="step">
    <span class="step-num">02</span>
    <div><strong>AI infers the voice</strong>
      <p>Personality, audience, themes, vocabulary, humour and emoji guidance.</p>
    </div>
  </div>
  <div class="step">
    <span class="step-num">03</span>
    <div><strong>10 tweets, checked</strong>
      <p>Distinct angles, no invented facts, each within 280 characters and ready to copy.</p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<p class="side-kicker">TRY A DEMO BRIEF</p>', unsafe_allow_html=True)
        st.caption("Loads example inputs only. Tweets are still generated live.")
        st.button(
            "Load Zomato example",
            use_container_width=True,
            on_click=load_preset,
            args=("Zomato",),
        )
        st.button(
            "Load Apple example",
            use_container_width=True,
            on_click=load_preset,
            args=("Apple",),
        )


def render_tweet_cards(tweets: list[Tweet]) -> None:
    # Build one row at a time so the grid stays numbered 1, 2 / 3, 4 on every
    # screen size. It also keeps each pair of cards visually aligned.
    for row_start in range(0, len(tweets), 2):
        row = st.columns(2, gap="medium")
        for offset, tweet in enumerate(tweets[row_start : row_start + 2]):
            index = row_start + offset
            with row[offset]:
                with st.container(border=True):
                    st.markdown(
                        (
                            '<div class="tweet-meta">'
                            f'<span class="tweet-no">Tweet {index + 1:02d}</span>'
                            f'<span class="angle-pill">{html.escape(tweet.angle)}</span>'
                            f'<span class="char-pill">{tweet.char_count} / {TWEET_LIMIT}</span>'
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                    # st.code() supplies a native, reliable copy-to-clipboard
                    # button. The CSS above turns the block into tweet text.
                    st.code(tweet.text, language=None)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "brand"


def tweets_as_text(result: dict) -> str:
    brief: BrandBrief = result["brief"]
    voice: VoiceProfile = result["voice"]
    lines = [
        f"{APP_TITLE} - generated tweet set {result['set_number']}",
        f"Brand: {brief.brand or 'Unnamed brand'}",
        f"Objective: {brief.objective}",
        f"Tone: {voice.tone}",
        f"Generated: {result['created'].strftime('%Y-%m-%d %H:%M')}",
        f"Model: {result['model']}",
        "",
        "BRAND VOICE SUMMARY",
        *[f"- {item}" for item in voice.summary],
        "",
        f"{len(result['tweets'])} TWEETS",
        "",
    ]
    for index, tweet in enumerate(result["tweets"], start=1):
        lines.append(f"{index}. {tweet.text}")
        lines.append(f"   ({tweet.char_count} characters)")
        lines.append("")
    return "\n".join(lines)


def run_generation(brief: BrandBrief, voice: VoiceProfile | None = None) -> bool:
    """
    Run Stage 1 (unless a voice is supplied) and Stage 2. Returns True on success.

    All errors are caught so a failed API call can never crash the app.
    """
    previous: list[str] = []
    existing = st.session_state.get("result")
    if existing:
        previous = [tweet.text for tweet in existing["tweets"]]

    error_message = ""
    error_details = ""
    active_voice = voice
    tweets: list[Tweet] = []
    notes: dict[str, int] = {}

    with st.status("Generating your tweet set\u2026", expanded=True) as status:
        try:
            client = OpenAI(api_key=API_KEY, timeout=75.0, max_retries=1)
            if voice is None:
                st.write("**Stage 1 of 2** \u00b7 Inferring the brand voice")
                active_voice = infer_brand_voice(client, MODEL, brief)
            else:
                st.write("**Stage 1 of 2** \u00b7 Reusing the saved brand voice")
                active_voice = voice

            st.write("**Stage 2 of 2** \u00b7 Writing and validating 10 tweets")
            tweets, notes = generate_tweets(
                client=client,
                model=MODEL,
                brief=brief,
                voice=active_voice,
                excluded=previous,
            )
            status.update(label="10 tweets ready", state="complete", expanded=False)
        except BrandTweetError as exc:
            status.update(label="Generation failed", state="error", expanded=False)
            error_message = str(exc)
        except Exception as exc:  # defensive: never let an API failure crash the app
            status.update(label="Generation failed", state="error", expanded=False)
            error_message = (
                "Something unexpected went wrong while generating. Please try again."
            )
            error_details = f"{type(exc).__name__}: {exc}"

    if error_message:
        # Render outside the collapsed status element so the reason is always visible.
        st.error(error_message)
        if error_details:
            with st.expander("Technical details"):
                st.code(error_details)
        return False

    st.session_state["set_number"] = st.session_state.get("set_number", 0) + 1
    st.session_state["result"] = {
        "brief": brief,
        "voice": active_voice,
        "tweets": tweets,
        "model": MODEL,
        "created": datetime.now(),
        "set_number": st.session_state["set_number"],
        "trimmed": notes.get("trimmed", 0),
    }
    return True


def render_results(result: dict) -> None:
    brief: BrandBrief = result["brief"]
    voice: VoiceProfile = result["voice"]
    tweets: list[Tweet] = result["tweets"]
    name = brief.brand or "Your brand"

    st.markdown(
        f"""
<div class="results-head">
  <div>
    <p class="eyebrow">RESULTS</p>
    <h2>Your campaign set</h2>
  </div>
  <span class="set-badge">SET {result['set_number']:02d} \u00b7 {len(tweets)} TWEETS</span>
</div>
<div class="results-meta">
  {html.escape(brief.objective)} \u00b7 {html.escape(voice.tone)}
  {('\u00b7 ' + html.escape(brief.industry)) if brief.industry else ''}
  \u00b7 generated with {html.escape(result['model'])}
</div>
""",
        unsafe_allow_html=True,
    )

    action1, action2, action3, action4 = st.columns([1.3, 1.3, .9, .9], gap="small")
    with action1:
        if st.button(
            "Regenerate All Tweets",
            use_container_width=True,
            help="Write 10 new tweets using the same voice profile.",
        ):
            if run_generation(result["brief"], voice=result["voice"]):
                st.rerun()
    with action2:
        if st.button(
            "Generate Another Set",
            use_container_width=True,
            help="Re-analyse the voice and write a completely fresh set.",
        ):
            if run_generation(result["brief"], voice=None):
                st.rerun()
    with action3:
        if st.button("Start Over", use_container_width=True):
            reset_app()
            st.rerun()
    with action4:
        st.download_button(
            "Download .txt",
            data=tweets_as_text(result),
            file_name=f"brandtweet-{slugify(name)}-set-{result['set_number']}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    chips = [brief.objective, voice.tone, *voice.content_themes[:3]]
    chip_html = "".join(f'<span class="chip">{html.escape(chip)}</span>' for chip in chips)
    bullets = "".join(f"<li>{html.escape(item)}</li>" for item in voice.summary)

    st.markdown(
        f"""
<div class="voice-card">
  <div class="voice-top">
    <div>
      <p class="eyebrow">STAGE 1 \u00b7 BRAND VOICE SUMMARY</p>
      <h3>{html.escape(name)}</h3>
    </div>
    <span class="ai-badge">AI inferred</span>
  </div>
  <div class="chip-row">{chip_html}</div>
  <ul class="voice-list">{bullets}</ul>
  <p class="voice-note">
    Inferred from your brief by {html.escape(result['model'])}. No live social
    profiles or posts were retrieved or analysed.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="tweets-head">
  <h3>10 tweets, ready to post</h3>
  <p>Use the copy icon in the top-right corner of any card.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    if result.get("trimmed"):
        st.caption(
            f"{result['trimmed']} tweet(s) exceeded 280 characters and were trimmed "
            "at a word boundary. Regenerate for a cleaner cut if needed."
        )
    render_tweet_cards(tweets)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

render_header()

if not API_READY:
    render_config_warning()

form_col, side_col = st.columns([1.62, 1], gap="large")
form_keys = current_form_keys()

with form_col:
    with st.form("brand_brief", clear_on_submit=False):
        st.markdown('<p class="form-title">Brand brief</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="form-caption">Only the product or service description is required. '
            "The more context you give, the sharper the voice.</p>",
            unsafe_allow_html=True,
        )

        row1_left, row1_right = st.columns(2, gap="medium")
        with row1_left:
            brand = st.text_input(
                "Brand name",
                key=form_keys["brand_name"],
                placeholder="e.g. Zomato",
                max_chars=80,
            )
        with row1_right:
            industry = st.text_input(
                "Industry / category",
                key=form_keys["industry"],
                placeholder="e.g. Food delivery",
                max_chars=120,
            )

        row2_left, row2_right = st.columns(2, gap="medium")
        with row2_left:
            objective = st.selectbox(
                "Campaign objective", OBJECTIVES, key=form_keys["objective"]
            )
        with row2_right:
            tone_choice = st.selectbox(
                "Preferred tone",
                [AUTO_TONE, *TONES],
                key=form_keys["tone"],
            )

        description = st.text_area(
            "Product / service description *",
            key=form_keys["description"],
            height=118,
            placeholder=(
                "What does the brand offer? What makes it useful, different, or worth "
                "talking about?"
            ),
            max_chars=1200,
        )

        audience = st.text_input(
            "Target audience",
            key=form_keys["audience"],
            placeholder="e.g. Urban food lovers aged 20-35 who order online",
            max_chars=300,
        )

        instructions = st.text_area(
            "Additional instructions",
            key=form_keys["instructions"],
            height=104,
            placeholder=(
                "Any must-use ideas, phrases to avoid, or format preferences? "
                "(e.g. no emojis, keep it under 200 characters)"
            ),
            max_chars=600,
        )

        submitted = st.form_submit_button(
            "Generate 10 Tweets",
            type="primary",
            use_container_width=True,
            disabled=not API_READY,
        )

    if submitted:
        brief, error = validate_brief(
            brand=brand,
            industry=industry,
            objective=objective,
            description=description,
            audience=audience,
            tone=tone_value(tone_choice),
            instructions=instructions,
        )
        if error:
            st.error(error)
        elif not API_READY:
            st.error("Add your OpenAI API key before generating tweets.")
        else:
            if run_generation(brief, voice=None):
                st.toast("Your 10 tweets are ready below.")

with side_col:
    render_side_panel()
    st.caption(
        "Your inputs are sent to the OpenAI API to generate the voice profile and "
        "tweets. The app does not scrape social media or store your brief."
    )

result = st.session_state.get("result")
if result:
    render_results(result)

st.markdown(
    f"""
<div class="app-footer">
  <span><strong>BrandTweet AI</strong> \u00b7 voice inferred from your brief, not from scraped social data.</span>
  <span>Model: {html.escape(MODEL)}</span>
</div>
""",
    unsafe_allow_html=True,
)
