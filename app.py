import streamlit as st
import google.generativeai as genai

# ── Config ────────────────────────────────────────────────────────────────────
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

SYSTEM_INSTRUCTION = """You are Alex, an encouraging and patient high school math tutor. \
Your core teaching philosophy is Socratic: you never give direct answers on the first attempt. \
Instead, guide students to discover solutions themselves through:

1. DIAGNOSIS – First identify exactly where the student is stuck.
2. HINT LADDER – Offer the smallest hint that moves them forward. If they're still stuck, \
   give a slightly bigger hint. Only reveal the full solution after ≥2 genuine attempts.
3. PRAISE EFFORT – Celebrate progress, not just correct answers.
4. ERROR ANALYSIS – When a student makes a mistake, ask them to spot the error themselves \
   before you point it out.
5. CONNECT CONCEPTS – Always tie the problem to the underlying principle (e.g., "This is \
   really about the distributive property…").

Tone: warm, encouraging, never condescending. Use plain language; introduce notation only \
when necessary and always explain it. If a student is frustrated, acknowledge the feeling first.

Topics you cover: arithmetic, algebra (1 & 2), geometry, trigonometry, pre-calculus, \
statistics, and AP Calculus AB/BC.

IMPORTANT: If a question is not related to math or tutoring, politely redirect: \
"I'm your math tutor, so let's keep the focus on math! What problem can I help you work through?"
"""

# Keep last K *pairs* of messages (user + model) to respect token limits
MAX_HISTORY_PAIRS = 10

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_INSTRUCTION,
)

# ── Page Setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Guided Helper · Math Tutor",
    page_icon="📐",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS – Gemini-inspired dark UI ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600&family=Google+Sans+Mono&display=swap');

/* ── Root palette (Gemini dark) ── */
:root {
    --bg:           #1c1c1e;
    --surface:      #2c2c2e;
    --surface-hi:   #3a3a3c;
    --border:       #3a3a3c;
    --accent:       #8ab4f8;
    --accent-soft:  rgba(138,180,248,.15);
    --user-bubble:  #1e3a5f;
    --text:         #5f6368;
    --text-muted:   #9aa0a6;
    --danger:       #f28b82;
    --radius:       18px;
    --font:         'Google Sans', sans-serif;
    --font-mono:    'Google Sans Mono', monospace;
}

/* ── Global resets ── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border); }
footer { visibility: hidden; }

/* ── Main container ── */
.block-container {
    max-width: 780px !important;
    padding: 0 1rem 6rem !important;
}

/* ── Header ── */
.gh-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 28px 0 12px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--border);
}
.gh-logo {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #8ab4f8 0%, #c58af9 50%, #f28b82 100%);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; flex-shrink: 0;
}
.gh-title  { font-size: 1.25rem; font-weight: 600; color: var(--text); margin: 0; }
.gh-sub    { font-size: .8rem; color: var(--text-muted); margin: 0; }

/* ── Welcome card ── */
.welcome-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px 28px;
    margin: 24px 0;
    text-align: center;
}
.welcome-card h2 { font-size: 1.4rem; font-weight: 600; margin-bottom: 6px; }
.welcome-card p  { color: var(--text-muted); font-size: .9rem; margin: 0; line-height: 1.6; }

/* ── Chip suggestions ── */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 18px; }
.chip {
    background: var(--surface-hi);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 7px 14px;
    font-size: .82rem;
    color: var(--text-muted);
    cursor: pointer;
    transition: all .15s;
}
.chip:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

/* ── Chat bubbles ── */
.msg-row { display: flex; gap: 12px; margin: 10px 0; align-items: flex-start; }
.msg-row.user  { flex-direction: row-reverse; }

.avatar {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; flex-shrink: 0; margin-top: 2px;
}
.avatar.bot  { background: linear-gradient(135deg,#8ab4f8,#c58af9); }
.avatar.user { background: var(--surface-hi); border: 1px solid var(--border); }

.bubble {
    max-width: 82%;
    padding: 12px 16px;
    border-radius: var(--radius);
    font-size: .93rem;
    line-height: 1.65;
    word-break: break-word;
}
.bubble.bot  {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top-left-radius: 4px;
}
.bubble.user {
    background: var(--user-bubble);
    border: 1px solid #2a4a70;
    border-top-right-radius: 4px;
    color: #cde;
}

/* math / code inside bubbles */
.bubble code { font-family: var(--font-mono); background: rgba(255,255,255,.08); padding: 1px 5px; border-radius: 4px; font-size: .88em; }
.bubble pre  { background: rgba(0,0,0,.3); border-radius: 10px; padding: 12px; overflow-x: auto; }

/* ── Thinking animation ── */
@keyframes blink { 0%,80%,100%{opacity:.2} 40%{opacity:1} }
.thinking-dots span {
    display: inline-block; width: 6px; height: 6px;
    background: var(--text-muted); border-radius: 50%; margin: 0 2px;
    animation: blink 1.2s infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: .2s; }
.thinking-dots span:nth-child(3) { animation-delay: .4s; }

/* ── Input area ── */
[data-testid="stChatInput"] > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 28px !important;
    padding: 4px 8px !important;
}
[data-testid="stChatInput"] textarea {
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-size: .93rem !important;
    background: transparent !important;
}
[data-testid="stChatInputSubmitButton"] svg { fill: var(--accent) !important; }

/* ── Buttons ── */
.stButton > button {
    background: var(--surface-hi) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    font-family: var(--font) !important;
    font-size: .82rem !important;
    padding: 4px 14px !important;
    transition: all .15s !important;
}
.stButton > button:hover {
    background: var(--accent-soft) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 8px 0 !important; }

/* scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surface-hi); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    # Each entry: {"role": "user"|"model", "content": str}
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="gh-header">
  <div class="gh-logo">📐</div>
  <div>
    <p class="gh-title">Guided Helper</p>
    <p class="gh-sub">Your personal high school math tutor</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📚 Topics")
    topics = ["Algebra", "Geometry", "Trigonometry", "Pre-Calculus", "Statistics", "AP Calculus"]
    for t in topics:
        st.markdown(f"- {t}")
    st.divider()
    st.markdown("### ℹ️ How it works")
    st.markdown("""
I won't give you the answer right away — that's how real learning happens!

**My approach:**
1. Ask what you've tried so far
2. Give hints, not solutions
3. Celebrate your progress
4. Reveal the full solution only after you've made an attempt
""")
    st.divider()
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()
    hist_count = len(st.session_state.messages)
    st.caption(f"Messages in session: {hist_count} / keeping last {MAX_HISTORY_PAIRS*2}")

# ── Welcome card (shown when no messages) ────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
<div class="welcome-card">
  <h2>Hi, I'm Alex 👋</h2>
  <p>I'm your math tutor. I'll guide you to the answer with hints and questions — not just the solution.<br>
     What are you working on today?</p>
  <div class="chip-row">
    <div class="chip">Solve a quadratic equation</div>
    <div class="chip">Help with the chain rule</div>
    <div class="chip">Understand sine and cosine</div>
    <div class="chip">Statistics – mean vs median</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Render conversation ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    if role == "user":
        st.markdown(f"""
<div class="msg-row user">
  <div class="avatar user">🧑</div>
  <div class="bubble user">{content}</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div class="msg-row">
  <div class="avatar bot">✨</div>
  <div class="bubble bot">{content}</div>
</div>""", unsafe_allow_html=True)

# ── Helper: build Gemini history from session ─────────────────────────────────
def build_gemini_history(messages: list) -> list:
    """
    Convert session messages to Gemini Content format.
    Trims to last MAX_HISTORY_PAIRS pairs to stay within token limits.
    All messages except the last user turn go into history.
    """
    # Drop the very last message (the new user turn — sent separately)
    history_msgs = messages[:-1]

    # Keep only the last MAX_HISTORY_PAIRS * 2 messages
    max_msgs = MAX_HISTORY_PAIRS * 2
    if len(history_msgs) > max_msgs:
        history_msgs = history_msgs[-max_msgs:]

    # Gemini requires alternating user/model and cannot start with model
    # Ensure we start with a user message
    while history_msgs and history_msgs[0]["role"] != "user":
        history_msgs = history_msgs[1:]

    return [
        {"role": m["role"], "parts": [{"text": m["content"]}]}
        for m in history_msgs
    ]

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask me a math question…")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.pending_prompt = user_input
    st.rerun()

# ── Generate response if we have a pending prompt ────────────────────────────
if st.session_state.pending_prompt:
    # Show the latest user bubble (already in messages, just re-render it)
    last_user = st.session_state.messages[-1]
    st.markdown(f"""
<div class="msg-row user">
  <div class="avatar user">🧑</div>
  <div class="bubble user">{last_user['content']}</div>
</div>""", unsafe_allow_html=True)

    # Thinking indicator
    thinking_placeholder = st.empty()
    thinking_placeholder.markdown("""
<div class="msg-row">
  <div class="avatar bot">✨</div>
  <div class="bubble bot">
    <div class="thinking-dots">
      <span></span><span></span><span></span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    try:
        history = build_gemini_history(st.session_state.messages)

        # Start a chat session with the trimmed history, then send the new message
        chat = model.start_chat(history=history)
        response = chat.send_message(st.session_state.pending_prompt)
        reply = response.text if response.text else "I didn't catch that — could you rephrase?"

    except Exception as e:
        reply = f"⚠️ Something went wrong: `{e}`"

    # Replace thinking indicator with real response
    thinking_placeholder.markdown(f"""
<div class="msg-row">
  <div class="avatar bot">✨</div>
  <div class="bubble bot">{reply}</div>
</div>""", unsafe_allow_html=True)

    st.session_state.messages.append({"role": "model", "content": reply})
    st.session_state.pending_prompt = None
