import base64
import html
import os
from typing import List, Dict

import requests
import streamlit as st
import streamlit.components.v1 as components


APP_TITLE = "ETERNUM"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
LOGO_PATH = os.path.join("assets", "logo.png")


def load_logo_data_uri(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_messages_html(messages: List[Dict[str, str]], thinking: bool = False) -> str:
    if not messages and not thinking:
        return '<div class="chat-window"><div class="chat-empty">No messages yet.</div></div>'

    parts = ['<div class="chat-window">']
    for message in messages:
        role = message.get("role", "assistant")
        if role == "system":
            continue
        label = "YOU" if role == "user" else APP_TITLE
        safe = html.escape(message.get("content", "")).replace("\n", "<br>")
        css_class = "msg user" if role == "user" else "msg assistant"
        parts.append(
            f'<div class="{css_class}">'
            f'<div class="msg-role">{label}</div>'
            f'<div class="msg-content">{safe}</div>'
            f"</div>"
        )
    if thinking:
        parts.append(
            f'<div class="msg assistant thinking">'
            f'<div class="msg-role">{APP_TITLE}</div>'
            f'<div class="msg-content">Pensando</div>'
            f"</div>"
        )
    parts.append("</div>")
    return "\n".join(parts)


def ollama_chat(messages: List[Dict[str, str]], model: str) -> str:
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("message", {}).get("content", "").strip()


def scroll_chat_to_bottom() -> None:
    components.html(
        """
<script>
const parentDoc = window.parent.document;
const runScroll = () => {
  const chat = parentDoc.querySelector(".chat-window");
  if (chat) {
    chat.scrollTop = chat.scrollHeight;
  }
};
requestAnimationFrame(runScroll);
setTimeout(runScroll, 120);
</script>
""",
        height=0,
        width=0,
    )


st.set_page_config(page_title=APP_TITLE, layout="wide")

logo_uri = load_logo_data_uri(LOGO_PATH)
logo_markup = f'<img src="{logo_uri}" alt="Logo">' if logo_uri else ""

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Oxanium:wght@400;600&family=Share+Tech+Mono&display=swap');

:root {
  --bg: #0b0c0f;
  --panel: #101114;
  --panel-border: #2a2d35;
  --accent: #f0a500;
  --text: #f5f5f5;
  --muted: #9da3b0;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg);
  color: var(--text);
}

[data-testid="stAppViewContainer"] {
  background-image:
    radial-gradient(circle at 12% 18%, rgba(240, 165, 0, 0.12), transparent 45%),
    radial-gradient(circle at 88% 20%, rgba(0, 200, 255, 0.12), transparent 45%),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(180deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 42px 42px, 42px 42px;
}

.block-container {
  padding-top: 1.4rem;
  padding-bottom: 2rem;
}

header, footer, #MainMenu {
  visibility: hidden;
}

.top-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  background: rgba(12, 13, 16, 0.86);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  margin-bottom: 18px;
}

.top-bar img {
  height: 28px;
}

.top-title {
  font-family: "Oxanium", sans-serif;
  font-size: 20px;
  letter-spacing: 4px;
}

div[data-testid="stHorizontalBlock"]:nth-of-type(1) > div[data-testid="column"]:first-child {
  background: rgba(11, 12, 16, 0.85);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  padding: 18px 16px;
  min-height: 60vh;
}

div[data-testid="stHorizontalBlock"]:nth-of-type(1) > div[data-testid="column"]:nth-child(2) {
  background: rgba(9, 10, 14, 0.88);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  padding: 18px 20px 22px 20px;
  min-height: 60vh;
}

.stButton > button {
  width: 100%;
  background: var(--accent);
  color: #1b1305;
  border: 1px solid var(--accent);
  border-radius: 10px;
  padding: 12px 14px;
  font-family: "Oxanium", sans-serif;
  font-size: 14px;
  letter-spacing: 0.8px;
  box-shadow: 0 8px 18px rgba(240, 165, 0, 0.2);
}

.stButton > button:hover {
  background: #ffb326;
  border-color: #ffb326;
}

button[title="Send message"] {
  width: 56px !important;
  height: 56px !important;
  border-radius: 16px !important;
  background: rgba(12, 14, 18, 0.9) !important;
  color: transparent !important;
  border: 1px solid var(--panel-border) !important;
  font-size: 0 !important;
  padding: 0 !important;
  position: relative;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03);
}

button[title="Send message"]::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23f0a500' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><line x1='22' y1='2' x2='11' y2='13'/><polygon points='22 2 15 22 11 13 2 9 22 2'/></svg>");
  background-repeat: no-repeat;
  background-position: center;
  background-size: 22px 22px;
  filter: drop-shadow(0 0 6px rgba(240, 165, 0, 0.35));
}

button[title="Send message"]:hover {
  border-color: rgba(240, 165, 0, 0.65) !important;
  box-shadow:
    inset 0 0 0 1px rgba(240, 165, 0, 0.2),
    0 8px 14px rgba(240, 165, 0, 0.2);
}

button[title="Send message"]:active {
  transform: translateY(1px);
}

.chat-window {
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  background: rgba(12, 13, 18, 0.85);
  padding: 18px;
  min-height: 46vh;
  max-height: 56vh;
  overflow-y: auto;
  scroll-behavior: smooth;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03);
}

.chat-empty {
  font-family: "Share Tech Mono", monospace;
  color: var(--muted);
  text-align: center;
  margin-top: 18px;
}

.msg {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.msg:last-child {
  margin-bottom: 0;
}

.msg-role {
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--muted);
  font-family: "Share Tech Mono", monospace;
}

.msg-content {
  background: rgba(20, 22, 28, 0.9);
  border: 1px solid var(--panel-border);
  border-radius: 12px;
  padding: 12px 14px;
  max-width: 86%;
  line-height: 1.5;
}

.msg.thinking .msg-content {
  color: var(--muted);
  font-style: italic;
}

.msg.thinking .msg-content::after {
  content: "...";
  display: inline-block;
  overflow: hidden;
  width: 0;
  vertical-align: bottom;
  animation: thinking-dots 1.2s steps(4, end) infinite;
}

@keyframes thinking-dots {
  to {
    width: 1.2em;
  }
}

.msg.user {
  align-items: flex-end;
}

.msg.user .msg-content {
  border-color: rgba(240, 165, 0, 0.6);
  background: rgba(240, 165, 0, 0.12);
  color: #fbe9c8;
}

div[data-testid="stTextInput"] input {
  background: rgba(10, 12, 16, 0.9);
  border: 1px solid var(--panel-border);
  color: var(--text);
  border-radius: 16px;
  height: 56px;
  padding: 0 18px;
  font-family: "Share Tech Mono", monospace;
}

div[data-testid="stTextInput"] input:focus {
  border-color: rgba(240, 165, 0, 0.8);
  box-shadow: 0 0 0 2px rgba(240, 165, 0, 0.15);
}

div[data-testid="stForm"] {
  margin-top: 18px;
  padding: 14px 16px 12px 16px;
  border: 1px solid var(--panel-border);
  border-radius: 18px;
  background: rgba(11, 12, 16, 0.75);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02);
}

div[data-testid="stForm"] form {
  padding: 0;
}

.mode-pill {
  margin-top: 16px;
  padding: 8px 12px;
  border: 1px solid rgba(240, 165, 0, 0.4);
  border-radius: 999px;
  font-family: "Share Tech Mono", monospace;
  font-size: 12px;
  letter-spacing: 2px;
  text-transform: uppercase;
  text-align: center;
  color: var(--accent);
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="top-bar">
  {logo_markup}
  <div class="top-title">{APP_TITLE}</div>
</div>
""",
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "mode" not in st.session_state:
    st.session_state.mode = "idle"

left_col, right_col = st.columns([1, 3], gap="small")

with left_col:
    if st.button("Grabar recuerdo", key="record", help="Record memory"):
        st.session_state.mode = "record"
    if st.button("Revivir recuerdos", key="recall", help="Recall memories"):
        st.session_state.mode = "recall"
    st.markdown(
        f'<div class="mode-pill">Mode: {st.session_state.mode}</div>',
        unsafe_allow_html=True,
    )

with right_col:
    chat_placeholder = st.empty()
    chat_placeholder.markdown(
        build_messages_html(st.session_state.messages),
        unsafe_allow_html=True,
    )
    scroll_chat_to_bottom()

    with st.form("chat-form", clear_on_submit=True):
        input_col, send_col = st.columns([8, 1], gap="small")
        with input_col:
            user_text = st.text_input(
                "Message",
                placeholder="Type your message",
                label_visibility="collapsed",
            )
        with send_col:
            send_clicked = st.form_submit_button("Send", help="Send message")

    if send_clicked and user_text.strip():
        st.session_state.messages.append({"role": "user", "content": user_text.strip()})
        chat_placeholder.markdown(
            build_messages_html(st.session_state.messages, thinking=True),
            unsafe_allow_html=True,
        )
        scroll_chat_to_bottom()
        with st.spinner("Pensando..."):
            try:
                reply = ollama_chat(st.session_state.messages, OLLAMA_MODEL)
            except requests.RequestException as exc:
                reply = (
                    "Unable to reach Ollama at "
                    f"{OLLAMA_HOST}. Is it running? Details: {exc}"
                )
        st.session_state.messages.append({"role": "assistant", "content": reply})
        chat_placeholder.markdown(
            build_messages_html(st.session_state.messages),
            unsafe_allow_html=True,
        )
        scroll_chat_to_bottom()
