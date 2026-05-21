import streamlit as st
import google.generativeai as genai
import json
import re

# ── Config ────────────────────────────────────────────────────────────────────
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ── System Instructions per mode ──────────────────────────────────────────────
SYSTEM_INSTRUCTIONS = {
    "tutor": """You are an encouraging and patient high school math tutor. \
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
""",

    "practice": """You are a math practice coach. Your job is to generate practice problems \
tailored to the student's level and topic, then evaluate their answers with clear, constructive feedback.

When a student asks to practice a topic:
1. Generate 1 problem at a time, clearly stated.
2. Wait for their answer.
3. If correct: celebrate and offer a slightly harder variation.
4. If incorrect: point out exactly where they went wrong with a brief explanation, then let them try again.
5. Track difficulty — start easy, ramp up gradually.

Format problems clearly. Use plain text math notation (e.g., x^2 + 3x - 4 = 0).
Always end your message with an encouraging word.
""",

    "explain": """You are a math concept explainer. Your job is to explain mathematical concepts \
with exceptional clarity using:

1. PLAIN LANGUAGE first — no jargon until the student is ready.
2. REAL-WORLD ANALOGIES — make abstract ideas concrete.
3. WORKED EXAMPLES — always show, don't just tell.
4. VISUAL DESCRIPTIONS — describe graphs, diagrams, or patterns in words when helpful.
5. COMMON MISTAKES — proactively mention pitfalls students often hit.

You cover: arithmetic, algebra, geometry, trigonometry, pre-calculus, statistics, AP Calculus AB/BC.

If the question is unrelated to math, kindly redirect to math topics.
""",
}

TOPIC_ANALYZER_INSTRUCTION = """You are a math topic classifier. Given a conversation between a student and tutor, \
identify the specific math topics, concepts, and subtopics being discussed.

Respond ONLY with a JSON object in this exact format (no markdown, no explanation):
{
  "primary_topic": "Topic name (e.g. Quadratic Equations)",
  "subject_area": "Subject area (e.g. Algebra)",
  "concepts": ["concept1", "concept2", "concept3"],
  "related_topics": ["related1", "related2"],
  "difficulty": "beginner|intermediate|advanced"
}

If no clear math topic is found, return:
{"primary_topic": null, "subject_area": null, "concepts": [], "related_topics": [], "difficulty": null}
"""

MAX_HISTORY_PAIRS = 10

# ── Page Setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Guided Helper · Math Tutor",
    page_icon="📐",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&family=Fraunces:ital,wght@0,300;0,600;1,300&display=swap');

:root {
    --bg:           #111318;
    --surface:      #1c1f27;
    --surface-hi:   #272b36;
    --border:       #2e3340;
    --accent:       #7eb8ff;
    --accent-2:     #a78bfa;
    --accent-soft:  rgba(126,184,255,.12);
    --user-bubble:  #1a2f4a;
    --text:         #1a1d27;
    --text-muted:   #3a3f52;
    --text-dim:     #4a5168;
    --success:      #6ee7b7;
    --warn:         #fbbf24;
    --radius:       16px;
    --font:         'DM Sans', sans-serif;
    --font-display: 'Fraunces', serif;
    --font-mono:    'DM Mono', monospace;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
footer { visibility: hidden; }

.block-container {
    max-width: 820px !important;
    padding: 0 1.2rem 6rem !important;
}

/* ── App header ── */
.gh-header {
    display: flex; align-items: center; gap: 14px;
    padding: 28px 0 14px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 6px;
}
.gh-logo {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, #7eb8ff 0%, #a78bfa 60%, #fb7185 100%);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; flex-shrink: 0;
}
.gh-title { font-family: var(--font-display); font-size: 1.3rem; font-weight: 600; color: var(--text); margin: 0; }
.gh-sub   { font-size: .78rem; color: var(--text-muted); margin: 2px 0 0; }

/* ── Mode badge ── */
.mode-badge {
    margin-left: auto;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: .75rem;
    font-weight: 500;
    border: 1px solid var(--border);
    color: var(--text-dim);
    background: var(--surface-hi);
    font-family: var(--font-mono);
}

/* ══════════════════════════════════════
   HOME SCREEN
══════════════════════════════════════ */
.home-hero {
    padding: 52px 0 32px;
    text-align: center;
}
.home-hero h1 {
    font-family: var(--font-display);
    font-size: 2.6rem;
    font-weight: 300;
    font-style: italic;
    color: var(--text);
    margin: 0 0 12px;
    line-height: 1.2;
}
.home-hero h1 em {
    font-style: normal;
    background: linear-gradient(90deg, #7eb8ff, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.home-hero p {
    color: var(--text-muted);
    font-size: .95rem;
    max-width: 460px;
    margin: 0 auto;
    line-height: 1.7;
}

.mode-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin: 40px 0;
}
@media (max-width: 600px) { .mode-grid { grid-template-columns: 1fr; } }

.mode-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 28px 22px;
    cursor: pointer;
    transition: all .2s ease;
    text-align: left;
    position: relative;
    overflow: hidden;
}
.mode-card::before {
    content: '';
    position: absolute;
    inset: 0;
    opacity: 0;
    transition: opacity .2s;
    border-radius: 20px;
}
.mode-card.tutor::before    { background: radial-gradient(circle at top left, rgba(126,184,255,.08), transparent 60%); }
.mode-card.practice::before { background: radial-gradient(circle at top left, rgba(167,139,250,.08), transparent 60%); }
.mode-card.explain::before  { background: radial-gradient(circle at top left, rgba(110,231,183,.08), transparent 60%); }
.mode-card:hover::before    { opacity: 1; }
.mode-card:hover {
    border-color: var(--border);
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,.35);
}
.mode-card:hover.tutor    { border-color: rgba(126,184,255,.4); }
.mode-card:hover.practice { border-color: rgba(167,139,250,.4); }
.mode-card:hover.explain  { border-color: rgba(110,231,183,.4); }

.mode-icon {
    width: 44px; height: 44px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
    margin-bottom: 16px;
}
.mode-icon.tutor    { background: rgba(126,184,255,.15); }
.mode-icon.practice { background: rgba(167,139,250,.15); }
.mode-icon.explain  { background: rgba(110,231,183,.15); }

.mode-card h3 {
    font-size: 1rem; font-weight: 600;
    color: var(--text); margin: 0 0 6px;
}
.mode-card p {
    font-size: .8rem; color: var(--text-muted);
    margin: 0; line-height: 1.55;
}
.mode-tag {
    display: inline-block;
    margin-top: 14px;
    font-size: .7rem;
    font-family: var(--font-mono);
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 500;
}
.mode-tag.tutor    { background: rgba(126,184,255,.12); color: #7eb8ff; }
.mode-tag.practice { background: rgba(167,139,250,.12); color: #a78bfa; }
.mode-tag.explain  { background: rgba(110,231,183,.12); color: #6ee7b7; }

.home-topics {
    text-align: center;
    padding: 16px 0 40px;
    border-top: 1px solid var(--border);
}
.home-topics p { color: var(--text-muted); font-size: .82rem; margin-bottom: 12px; }
.topic-chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.topic-chip {
    background: var(--surface-hi);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 5px 13px;
    font-size: .78rem;
    color: var(--text-dim);
}

/* ══════════════════════════════════════
   CHAT VIEW
══════════════════════════════════════ */
.welcome-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 22px 26px;
    margin: 20px 0;
    text-align: center;
}
.welcome-card p { color: var(--text-muted); font-size: .88rem; margin: 0; line-height: 1.65; }
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 14px; }
.chip {
    background: var(--surface-hi); border: 1px solid var(--border);
    border-radius: 20px; padding: 6px 13px; font-size: .79rem;
    color: var(--text-muted); cursor: pointer; transition: all .15s;
}
.chip:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

/* ── Chat bubbles ── */
.msg-row { display: flex; gap: 10px; margin: 8px 0; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }
.avatar {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; flex-shrink: 0; margin-top: 3px;
}
.avatar.bot  { background: linear-gradient(135deg,#7eb8ff,#a78bfa); }
.avatar.user { background: var(--surface-hi); border: 1px solid var(--border); }
.bubble {
    max-width: 82%; padding: 11px 15px;
    border-radius: var(--radius); font-size: .9rem; line-height: 1.65; word-break: break-word;
}
.bubble.bot  { background: var(--surface); border: 1px solid var(--border); border-top-left-radius: 4px; }
.bubble.user { background: var(--user-bubble); border: 1px solid #1e3d66; border-top-right-radius: 4px; color: #c5d9f0; }
.bubble code { font-family: var(--font-mono); background: rgba(255,255,255,.07); padding: 1px 5px; border-radius: 4px; font-size: .85em; }
.bubble pre  { background: rgba(0,0,0,.3); border-radius: 10px; padding: 12px; overflow-x: auto; }

/* ── Thinking ── */
@keyframes blink { 0%,80%,100%{opacity:.2} 40%{opacity:1} }
.thinking-dots span {
    display: inline-block; width: 6px; height: 6px;
    background: var(--text-muted); border-radius: 50%; margin: 0 2px;
    animation: blink 1.2s infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: .2s; }
.thinking-dots span:nth-child(3) { animation-delay: .4s; }

/* ── Input ── */
[data-testid="stChatInput"] > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 28px !important;
    padding: 4px 8px !important;
}
[data-testid="stChatInput"] textarea {
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-size: .9rem !important;
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
    font-size: .8rem !important;
    padding: 4px 14px !important;
    transition: all .15s !important;
}
.stButton > button:hover {
    background: var(--accent-soft) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ── Sidebar topic panel ── */
.topic-panel-header {
    font-family: var(--font-display);
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 4px;
}
.topic-primary {
    font-size: 1.2rem; font-weight: 600;
    background: linear-gradient(90deg, #7eb8ff, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 8px 0 4px;
}
.topic-area {
    font-family: var(--font-mono); font-size: .72rem;
    color: var(--text-muted); margin-bottom: 12px;
}
.diff-badge {
    display: inline-block; padding: 3px 10px;
    border-radius: 20px; font-size: .7rem;
    font-family: var(--font-mono); font-weight: 500;
    margin-bottom: 16px;
}
.diff-beginner     { background: rgba(110,231,183,.12); color: #6ee7b7; }
.diff-intermediate { background: rgba(251,191,36,.12);  color: #fbbf24; }
.diff-advanced     { background: rgba(251,113,133,.12); color: #fb7185; }

.concept-map {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px;
    margin: 10px 0;
}
.concept-node {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--surface-hi);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 5px 11px;
    font-size: .78rem;
    color: var(--text-dim);
    margin: 3px;
}
.concept-node.primary {
    background: var(--accent-soft);
    border-color: rgba(126,184,255,.3);
    color: var(--accent);
    font-weight: 500;
}
.related-list { margin-top: 10px; }
.related-item {
    font-size: .78rem; color: var(--text-muted);
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 8px;
}
.related-item:last-child { border-bottom: none; }
.related-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--accent-2); flex-shrink: 0; }

/* ── Clickable logo/home button in chat header ── */
.logo-btn-wrap .stButton > button {
    background: transparent !important;
    border: none !important;
    padding: 24px 0 12px !important;
    font-family: var(--font-display) !important;
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: var(--text) !important;
    border-radius: 0 !important;
    text-align: left !important;
    box-shadow: none !important;
    letter-spacing: -.01em !important;
    transition: color .15s !important;
    width: 100% !important;
}
.logo-btn-wrap .stButton > button:hover {
    color: var(--accent) !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Mode badge floated right in the header row */
.mode-badge-right {
    margin-top: 24px;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: .75rem;
    font-weight: 500;
    border: 1px solid var(--border);
    color: var(--text-dim);
    background: var(--surface-hi);
    font-family: var(--font-mono);
    display: inline-block;
    white-space: nowrap;
    float: right;
}
.header-rule { margin: 0 0 6px !important; }

hr { border-color: var(--border) !important; margin: 8px 0 !important; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surface-hi); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
defaults = {
    "screen": "home",          # "home" | "chat"
    "mode": None,              # "tutor" | "practice" | "explain"
    "messages": [],
    "pending_prompt": None,
    "topic_data": None,        # dict from topic analyzer
    "analyze_topics": False,   # flag to trigger analysis
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Models ────────────────────────────────────────────────────────────────────
def get_model(mode: str):
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_INSTRUCTIONS[mode],
    )

analyzer_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=TOPIC_ANALYZER_INSTRUCTION,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def build_gemini_history(messages: list) -> list:
    history_msgs = messages[:-1]
    max_msgs = MAX_HISTORY_PAIRS * 2
    if len(history_msgs) > max_msgs:
        history_msgs = history_msgs[-max_msgs:]
    while history_msgs and history_msgs[0]["role"] != "user":
        history_msgs = history_msgs[1:]
    return [{"role": m["role"], "parts": [{"text": m["content"]}]} for m in history_msgs]


def analyze_topics(messages: list) -> dict | None:
    if not messages:
        return None
    # Build a short conversation summary for the analyzer
    convo = "\n".join(
        f"{'Student' if m['role'] == 'user' else 'Tutor'}: {m['content'][:300]}"
        for m in messages[-6:]  # last 3 pairs
    )
    try:
        resp = analyzer_model.generate_content(convo)
        raw = resp.text.strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"```$", "", raw).strip()
        data = json.loads(raw)
        if data.get("primary_topic"):
            return data
    except Exception:
        pass
    return None


MODE_META = {
    "tutor": {
        "label": "Guided Tutor",
        "icon": "🧑‍🏫",
        "desc": "Build the critical thinking math demands. Learn to break down word problems, see math's logic, and solve higher math with the basics.",
        "tag": "Socratic Method",
        "chips": [
            "Solve a quadratic equation",
            "Help with the chain rule",
            "Understand sine and cosine",
            "Statistics — mean vs median",
        ],
        "welcome": "I'll guide you with hints and questions, not just solutions. What are you working on today?",
    },
    "practice": {
        "label": "Practice Mode",
        "icon": "🎯",
        "desc": "Get a full grasp with generated problems that format tests: difficulty and question types that are tailored to you with feedback.",
        "tag": "Adaptive Drills",
        "chips": [
            "Practice quadratic equations",
            "Give me geometry problems",
            "Drill me on derivatives",
            "Probability practice problems",
        ],
        "welcome": "Let's drill! Tell me what topic you want to practice and I'll generate problems at your level.",
    },
    "explain": {
        "label": "Concept Explainer",
        "icon": "💡",
        "desc": "Deep dives into any math concept with plain-language explanations, analogies, visualizations, and examples.",
        "tag": "Deep Dives",
        "chips": [
            "What is a derivative?",
            "Explain the unit circle",
            "How does standard deviation work?",
            "What is imaginary number i?",
        ],
        "welcome": "Ask me to explain any math concept and I'll break it down with plain language and real examples.",
    },
}

# ════════════════════════════════════════════════════════════════════════════════
#  HOME SCREEN
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state.screen == "home":
    # Header
    st.markdown("""
<div class="gh-header">
  <div class="gh-logo">📐</div>
  <div>
    <p class="gh-title">Guided Helper</p>
    <p class="gh-sub">Your personal math tutor</p>
  </div>
</div>""", unsafe_allow_html=True)

    # Hero
    st.markdown("""
<div class="home-hero">
  <h1>Learn to Apply Math and Yourself</h1>
  <p>Choose a mode below to get started. Guided Tutor internatlizes subjects through (potentially frustrating) discovery,
     Practice Mode builds (test-taking) skills with adaptive drills, and Concept Explainer gives you clear, visualizing explanations.</p>
</div>""", unsafe_allow_html=True)

    # Mode cards — rendered as st.columns with clickable buttons underneath
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    modes = ["tutor", "practice", "explain"]

    for col, mode_key in zip(cols, modes):
        m = MODE_META[mode_key]
        with col:
            st.markdown(f"""
<div class="mode-card {mode_key}">
  <div class="mode-icon {mode_key}">{m['icon']}</div>
  <h3>{m['label']}</h3>
  <p>{m['desc']}</p>
  <span class="mode-tag {mode_key}">{m['tag']}</span>
</div>""", unsafe_allow_html=True)
            if st.button(f"Open {m['label']}", key=f"mode_{mode_key}", use_container_width=True):
                st.session_state.mode = mode_key
                st.session_state.screen = "chat"
                st.session_state.messages = []
                st.session_state.topic_data = None
                st.rerun()

    # Topics footer
    st.markdown("""
<div class="home-topics">
  <p>Covers all standard high school math topics</p>
  <div class="topic-chips">
    <span class="topic-chip">Arithmetic</span>
    <span class="topic-chip">Algebra I &amp; II</span>
    <span class="topic-chip">Geometry</span>
    <span class="topic-chip">Trigonometry</span>
    <span class="topic-chip">Pre-Calculus</span>
    <span class="topic-chip">Statistics</span>
    <span class="topic-chip">AP Calculus AB/BC</span>
  </div>
</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  CHAT SCREEN
# ════════════════════════════════════════════════════════════════════════════════
else:
    mode = st.session_state.mode or "tutor"
    meta = MODE_META[mode]

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"<div class='topic-panel-header'>🔭 Topic Radar</div>", unsafe_allow_html=True)
        st.caption("Updates as you chat")

        td = st.session_state.topic_data
        if td:
            st.markdown(f"<div class='topic-primary'>{td.get('primary_topic','—')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='topic-area'>{td.get('subject_area','')}</div>", unsafe_allow_html=True)

            diff = td.get("difficulty")
            if diff:
                st.markdown(f"<span class='diff-badge diff-{diff}'>{diff.capitalize()}</span>", unsafe_allow_html=True)

            concepts = td.get("concepts", [])
            if concepts:
                st.markdown("**Core concepts**")
                nodes_html = ""
                for i, c in enumerate(concepts):
                    cls = "primary" if i == 0 else ""
                    nodes_html += f"<span class='concept-node {cls}'>{'◆ ' if i==0 else ''}{c}</span>"
                st.markdown(f"<div class='concept-map'>{nodes_html}</div>", unsafe_allow_html=True)

            related = td.get("related_topics", [])
            if related:
                st.markdown("**Related topics**")
                items_html = "".join(
                    f"<div class='related-item'><span class='related-dot'></span>{r}</div>"
                    for r in related
                )
                st.markdown(f"<div class='related-list'>{items_html}</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
<div style='background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center;margin-top:8px;'>
  <div style='font-size:1.6rem;margin-bottom:8px;opacity:.4;'>🔭</div>
  <div style='font-size:.8rem;color:var(--text-muted);line-height:1.6;'>
    Topics you're working on will appear here as a concept map.
  </div>
</div>""", unsafe_allow_html=True)

        st.divider()
        st.markdown("### 📚 Topics Covered")
        for t in ["Arithmetic", "Algebra I & II", "Geometry", "Trigonometry", "Pre-Calculus", "Statistics", "AP Calc AB/BC"]:
            st.markdown(f"<span style='font-size:.82rem;color:var(--text-muted)'>· {t}</span>", unsafe_allow_html=True)
        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.screen = "home"
                st.rerun()
        with col_b:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.session_state.pending_prompt = None
                st.session_state.topic_data = None
                st.rerun()

        hist_count = len(st.session_state.messages)
        st.caption(f"Messages: {hist_count} · keeping last {MAX_HISTORY_PAIRS*2}")

    # ── Header (logo button navigates home) ──────────────────────────────────
    st.markdown("<div class='logo-btn-wrap'>", unsafe_allow_html=True)
    hcol1, hcol2 = st.columns([6, 2])
    with hcol1:
        if st.button("📐  Guided Helper", key="home_logo_btn"):
            st.session_state.screen = "home"
            st.rerun()
    with hcol2:
        st.markdown(f"<div class='mode-badge-right'>{meta['label']}</div>", unsafe_allow_html=True)
    st.markdown("</div><hr class='header-rule'>", unsafe_allow_html=True)

    # ── Welcome card ──────────────────────────────────────────────────────────
    if not st.session_state.messages:
        chips_html = "".join(f"<div class='chip'>{c}</div>" for c in meta["chips"])
        st.markdown(f"""
<div class="welcome-card">
  <p>{meta['welcome']}</p>
  <div class="chip-row">{chips_html}</div>
</div>""", unsafe_allow_html=True)

    # ── Render conversation ───────────────────────────────────────────────────
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

    # ── Chat input ────────────────────────────────────────────────────────────
    user_input = st.chat_input(f"Ask me a math question…")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.pending_prompt = user_input
        st.session_state.analyze_topics = True
        st.rerun()

    # ── Generate response ─────────────────────────────────────────────────────
    if st.session_state.pending_prompt:
        last_user = st.session_state.messages[-1]
        st.markdown(f"""
<div class="msg-row user">
  <div class="avatar user">🧑</div>
  <div class="bubble user">{last_user['content']}</div>
</div>""", unsafe_allow_html=True)

        thinking_ph = st.empty()
        thinking_ph.markdown("""
<div class="msg-row">
  <div class="avatar bot">✨</div>
  <div class="bubble bot">
    <div class="thinking-dots"><span></span><span></span><span></span></div>
  </div>
</div>""", unsafe_allow_html=True)

        try:
            mdl = get_model(mode)
            history = build_gemini_history(st.session_state.messages)
            chat = mdl.start_chat(history=history)
            response = chat.send_message(st.session_state.pending_prompt)
            reply = response.text if response.text else "I didn't catch that — could you rephrase?"
        except Exception as e:
            reply = f"⚠️ Something went wrong: `{e}`"

        thinking_ph.markdown(f"""
<div class="msg-row">
  <div class="avatar bot">✨</div>
  <div class="bubble bot">{reply}</div>
</div>""", unsafe_allow_html=True)

        st.session_state.messages.append({"role": "model", "content": reply})
        st.session_state.pending_prompt = None

        # ── Topic analysis (after every 2 user messages to save API calls) ──
        if st.session_state.analyze_topics:
            user_msg_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
            if user_msg_count % 2 == 0 or user_msg_count <= 2:
                td = analyze_topics(st.session_state.messages)
                if td:
                    st.session_state.topic_data = td
            st.session_state.analyze_topics = False

        st.rerun()
