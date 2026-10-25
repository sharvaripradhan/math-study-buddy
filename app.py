import json
import os
import re
from pathlib import Path

import streamlit as st

import llm
import prompts

st.set_page_config(page_title="Math Study Buddy", page_icon="🧮")

# Load API keys from Streamlit secrets (local secrets.toml or Cloud) into the environment.
for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER"):
    try:
        if key in st.secrets and key not in os.environ:
            os.environ[key] = st.secrets[key]
    except Exception:
        pass  # no secrets file; fall back to real environment variables

TOPICS = json.loads((Path(__file__).parent / "topics.json").read_text(encoding="utf-8"))
DIFFICULTIES = ["Easy", "Medium", "Hard"]
TAG_RE = re.compile(r"^\s*\[(CORRECT|INCORRECT|SOLUTION)\]\s*")

ss = st.session_state
ss.setdefault("messages", [])  # {"role", "content", "hidden"}
ss.setdefault("settings", None)  # (grade, topic, difficulty) of the active session
ss.setdefault("correct", 0)
ss.setdefault("attempted", 0)


def ask(user_text: str, hidden: bool = False) -> None:
    """Send a user turn to the LLM, update the score, and store the reply."""
    ss.messages.append({"role": "user", "content": user_text, "hidden": hidden})
    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    try:
        with st.spinner("Thinking..."):
            reply = llm.chat(prompts.build_system_prompt(*ss.settings), history)
    except Exception as e:  # keep the app alive on API/key errors
        ss.messages.pop()
        st.error(f"Couldn't reach the AI: {e}")
        return
    match = TAG_RE.match(reply)
    if match:
        if match.group(1) in ("CORRECT", "INCORRECT"):
            ss.attempted += 1
            ss.correct += match.group(1) == "CORRECT"
        reply = reply[match.end():]
    ss.messages.append({"role": "assistant", "content": reply, "hidden": False})


# ---- Sidebar: choices + score ----
with st.sidebar:
    st.header("🧮 Math Study Buddy")
    grade = st.selectbox("Grade", list(TOPICS))
    topic = st.selectbox("Topic", TOPICS[grade])
    difficulty = st.select_slider("Difficulty", DIFFICULTIES, value="Medium")
    if st.button("Start session", type="primary", use_container_width=True):
        ss.messages, ss.correct, ss.attempted = [], 0, 0
        ss.settings = (grade, topic, difficulty)
        ask(prompts.START_MESSAGE, hidden=True)
    st.divider()
    st.metric("Score", f"{ss.correct} / {ss.attempted}")

# ---- Main chat area ----
st.title("Math Study Buddy")
if not ss.settings:
    st.info("Pick a grade, topic and difficulty in the sidebar, then press **Start session**.")
    st.stop()

st.caption(" · ".join(ss.settings))
for m in ss.messages:
    if not m["hidden"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

col1, col2, col3 = st.columns(3)
if col1.button("💡 Hint", use_container_width=True):
    ask(prompts.HINT_MESSAGE)
    st.rerun()
if col2.button("📝 Show solution", use_container_width=True):
    ask(prompts.SOLUTION_MESSAGE)
    st.rerun()
if col3.button("➡️ Next question", use_container_width=True):
    ask(prompts.NEXT_MESSAGE)
    st.rerun()

if answer := st.chat_input("Type your answer or ask a question..."):
    ask(answer)
    st.rerun()
