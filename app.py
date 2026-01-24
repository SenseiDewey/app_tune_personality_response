import base64
import hashlib
import html
import os
import time
from typing import Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

from backend.auth_db import verify_user_credentials
from backend.config import get_settings
from backend.memory_agent import build_memory_graph, run_chat
from backend.prompts import INITIAL_ASSISTANT_MESSAGE, SYSTEM_CHAT_PROMPT
from backend.voice import text_to_speech, transcribe_audio


APP_TITLE = "ETERNUM"
LOGO_PATH = os.path.join("assets", "logo.png")
CHAT_ICON = "\N{SPEECH BALLOON}"
VOICE_ICON = "\N{MICROPHONE}"
VOICE_INTRO_PATH = os.path.join("assets", "mensaje_inicial.mp3")


def load_logo_data_uri(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def audio_to_data_uri(audio_bytes: bytes, mime_type: Optional[str]) -> str:
    encoded = base64.b64encode(audio_bytes).decode("ascii")
    safe_mime = mime_type or "audio/mpeg"
    return f"data:{safe_mime};base64,{encoded}"


def log_voice_debug(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.voice_debug.append(f"{timestamp} - {message}")


def load_audio_bytes(path: str) -> Optional[bytes]:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()


def render_login() -> None:
    settings = get_settings()
    st.markdown(
        """
<style>
div[data-testid="stForm"] {
  margin: 6vh auto 0 auto;
  width: min(440px, 92vw);
  padding: 24px 22px 26px 22px;
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  background: rgba(11, 12, 16, 0.9);
  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.4);
}

div[data-testid="stForm"] form {
  padding: 0;
}
</style>
""",
        unsafe_allow_html=True,
    )
    with st.form("login-form"):
        st.markdown(
            """
<div class="login-title">Acceso</div>
<div class="login-subtitle">Identifica tu usuario para iniciar la interfaz.</div>
""",
            unsafe_allow_html=True,
        )
        username = st.text_input("Usuario", placeholder="Tu usuario")
        password = st.text_input("Clave", type="password", placeholder="Tu clave")
        submitted = st.form_submit_button("Ingresar")
    if not settings.database_url:
        st.error(
            "No se encontro la configuracion de la base de datos. "
            "Define DATABASE_URL para validar usuarios."
        )
    if submitted:
        if not username.strip() or not password:
            st.session_state.auth_error = "Completa usuario y clave."
        else:
            try:
                if verify_user_credentials(username, password, settings):
                    st.session_state.authenticated = True
                    st.session_state.auth_error = ""
                    st.session_state.login_user = username.strip()
                    st.session_state.tenant_id = st.session_state.login_user
                    st.rerun()
                else:
                    st.session_state.auth_error = "Credenciales invalidas."
            except Exception:
                st.session_state.auth_error = (
                    "No se pudo validar el acceso con la base de datos."
                )
    if st.session_state.auth_error:
        st.error(st.session_state.auth_error)


def clear_voice_autoplay_flags() -> None:
    for message in st.session_state.voice_messages:
        if message.get("autoplay"):
            message["autoplay"] = False


def add_voice_intro_message() -> None:
    if st.session_state.voice_messages:
        return
    audio_bytes = load_audio_bytes(VOICE_INTRO_PATH)
    if not audio_bytes:
        return
    st.session_state.voice_messages.append(
        {
            "role": "assistant",
            "transcript": "",
            "audio_uri": audio_to_data_uri(audio_bytes, "audio/mpeg"),
            "autoplay": True,
        }
    )


def build_initial_message(user_name: str) -> str:
    name = user_name.strip() if user_name else ""
    if not name:
        name = "amigo"
    return INITIAL_ASSISTANT_MESSAGE.format(name=name)


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
    parts.append("</div>")
    return "\n".join(parts)


def build_voice_messages_html(
    messages: List[Dict[str, str]], thinking: bool = False
) -> str:
    if not messages and not thinking:
        return '<div class="chat-window"><div class="chat-empty">No messages yet.</div></div>'

    parts = ['<div class="chat-window voice-chat">']
    for message in messages:
        role = message.get("role", "assistant")
        if role == "system":
            continue
        label = "YOU" if role == "user" else APP_TITLE
        transcript = html.escape(message.get("transcript", "") or "").replace(
            "\n", "<br>"
        )
        audio_uri = message.get("audio_uri", "")
        autoplay_attr = " autoplay" if message.get("autoplay") else ""
        css_class = "msg user" if role == "user" else "msg assistant"
        audio_tag = ""
        if audio_uri:
            audio_tag = (
                f'<audio class="voice-audio" controls preload="metadata"{autoplay_attr} '
                f'src="{audio_uri}"></audio>'
            )
        transcript_tag = (
            f'<div class="msg-transcript">{transcript}</div>'
            if transcript
            else ""
        )
        content = f'<div class="voice-stack">{audio_tag}{transcript_tag}</div>'
        parts.append(
            f'<div class="{css_class}">'
            f'<div class="msg-role">{label}</div>'
            f'<div class="msg-content">{content}</div>'
            f"</div>"
        )
    parts.append("</div>")
    return "\n".join(parts)


def scroll_chat_to_bottom() -> None:
    components.html(
        """
<script>
const parentDoc = window.parent.document;
const attachAutoScroll = () => {
  const chat = parentDoc.querySelector(".chat-window");
  if (!chat) {
    return false;
  }
  const scrollToBottom = () => {
    chat.scrollTop = chat.scrollHeight;
  };
  if (chat.dataset.autoscrollAttached === "true") {
    scrollToBottom();
    return true;
  }
  chat.dataset.autoscrollAttached = "true";
  scrollToBottom();
  const observer = new MutationObserver(scrollToBottom);
  observer.observe(chat, { childList: true, subtree: true });
  window.addEventListener("resize", scrollToBottom);
  return true;
};
const tryAttach = () => {
  if (!attachAutoScroll()) {
    requestAnimationFrame(tryAttach);
  }
};
tryAttach();
</script>
""",
        height=0,
        width=0,
    )


@st.cache_resource
def get_runtime():
    settings = get_settings()
    graph = build_memory_graph(settings)
    return settings, graph


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
  min-height: 68vh;
}

div[data-testid="stHorizontalBlock"]:nth-of-type(1) > div[data-testid="column"]:nth-child(2) {
  background: rgba(9, 10, 14, 0.88);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  padding: 18px 20px 22px 20px;
  min-height: 68vh;
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
  min-height: 60vh;
  max-height: 70vh;
  overflow-y: auto;
  scroll-behavior: smooth;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03);
}

.voice-chat .msg-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.voice-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.voice-audio {
  width: 240px;
}

.msg-transcript {
  font-size: 12px;
  font-family: "Share Tech Mono", monospace;
  color: var(--muted);
  line-height: 1.4;
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
  max-width: 92%;
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

div[data-testid="stAudioInput"] {
  margin-top: 16px;
  padding: 12px 14px;
  border: 1px solid var(--panel-border);
  border-radius: 18px;
  background: rgba(11, 12, 16, 0.75);
}

div[data-testid="stAudioInput"] label {
  font-family: "Share Tech Mono", monospace;
  color: var(--muted);
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

.login-title {
  font-family: "Oxanium", sans-serif;
  font-size: 20px;
  letter-spacing: 4px;
  margin-bottom: 6px;
}

.login-subtitle {
  font-family: "Share Tech Mono", monospace;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 16px;
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

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "auth_error" not in st.session_state:
    st.session_state.auth_error = ""

if "login_user" not in st.session_state:
    st.session_state.login_user = ""

if not st.session_state.authenticated:
    render_login()
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_CHAT_PROMPT},
        {
            "role": "assistant",
            "content": build_initial_message(st.session_state.login_user),
        },
    ]

if "voice_messages" not in st.session_state:
    st.session_state.voice_messages = []

if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

if "voice_debug" not in st.session_state:
    st.session_state.voice_debug = []

if "mode" not in st.session_state:
    st.session_state.mode = "chat"

if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = "default"

if st.session_state.authenticated and st.session_state.login_user:
    st.session_state.tenant_id = st.session_state.login_user

left_col, right_col = st.columns([1, 4], gap="small")

with left_col:
    if st.button(f"{CHAT_ICON} Modo chat", key="chat", help="Modo chat"):
        st.session_state.mode = "chat"
    if st.button(f"{VOICE_ICON} Modo voz", key="voice", help="Modo voz"):
        st.session_state.mode = "voice"
    st.markdown(
        f'<div class="mode-pill">Modo: {st.session_state.mode}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height: 300px;"></div>', unsafe_allow_html=True)
    if st.button("Cerrar sesión"):
        st.session_state.authenticated = False
        st.session_state.auth_error = ""
        st.session_state.login_user = ""
        st.session_state.tenant_id = "default"
        st.rerun()

with right_col:
    if st.session_state.mode == "voice":
        settings, graph = get_runtime()
        clear_voice_autoplay_flags()
        add_voice_intro_message()
        voice_placeholder = st.empty()
        voice_placeholder.markdown(
            build_voice_messages_html(st.session_state.voice_messages),
            unsafe_allow_html=True,
        )
        scroll_chat_to_bottom()

        if not settings.elevenlabs_api_key:
            st.warning(
                f"Configura ELEVENLABS_API_KEY en tu .env para transcribir y sintetizar. es {settings.elevenlabs_api_key}"
            )
        if not settings.elevenlabs_voice_id:
            st.warning(
                f"Configura ELEVENLABS_VOICE_ID en tu .env para generar voz. {settings.qdrant_api_key}"
            )

        audio_input = st.audio_input(
            "Grabar mensaje de voz",
            key="voice-input",
        )

        if audio_input is not None:
            audio_bytes = audio_input.getvalue()
            if audio_bytes:
                audio_hash = hashlib.sha256(audio_bytes).hexdigest()
                if audio_hash != st.session_state.last_audio_hash:
                    st.session_state.last_audio_hash = audio_hash
                    user_audio_uri = audio_to_data_uri(
                        audio_bytes, audio_input.type
                    )
                    st.session_state.voice_messages.append(
                        {
                            "role": "user",
                            "transcript": "",
                            "audio_uri": user_audio_uri,
                            "autoplay": False,
                        }
                    )
                    voice_placeholder.markdown(
                        build_voice_messages_html(
                            st.session_state.voice_messages, thinking=True
                        ),
                        unsafe_allow_html=True,
                    )
                    scroll_chat_to_bottom()

                    transcript = ""
                    if settings.elevenlabs_api_key:
                        with st.spinner("Transcribiendo audio..."):
                            try:
                                transcript = transcribe_audio(
                                    settings, audio_bytes, audio_input.type
                                )
                            except Exception as exc:
                                st.error(
                                    f"No se pudo transcribir el audio. Detalles: {exc}"
                                )
                    if not transcript:
                        transcript = "No se pudo transcribir el audio."
                    st.session_state.voice_messages[-1]["transcript"] = transcript
                    voice_placeholder.markdown(
                        build_voice_messages_html(
                            st.session_state.voice_messages, thinking=True
                        ),
                        unsafe_allow_html=True,
                    )
                    scroll_chat_to_bottom()

                    reply = ""
                    if transcript and transcript != "No se pudo transcribir el audio.":
                        history_snapshot = list(st.session_state.messages)
                        st.session_state.messages.append(
                            {"role": "user", "content": transcript}
                        )
                        with st.spinner("Pensando..."):
                            try:
                                reply = run_chat(
                                    graph,
                                    st.session_state.tenant_id,
                                    transcript,
                                    history_snapshot,
                                )
                            except Exception as exc:
                                reply = (
                                    "No se pudo generar la respuesta. "
                                    f"Detalles: {exc}"
                                )
                        st.session_state.messages.append(
                            {"role": "assistant", "content": reply}
                        )

                    if reply:
                        assistant_audio_uri = ""
                        if settings.elevenlabs_api_key and settings.elevenlabs_voice_id:
                            with st.spinner("Generando audio..."):
                                try:
                                    audio_reply, mime = text_to_speech(
                                        settings, reply
                                    )
                                    assistant_audio_uri = audio_to_data_uri(
                                        audio_reply, mime
                                    )
                                except Exception as exc:
                                    st.error(
                                        "No se pudo generar el audio del asistente. "
                                        f"Detalles: {exc}"
                                    )

                        for msg in st.session_state.voice_messages:
                            msg["autoplay"] = False
                        st.session_state.voice_messages.append(
                            {
                                "role": "assistant",
                                "transcript": reply,
                                "audio_uri": assistant_audio_uri,
                                "autoplay": bool(assistant_audio_uri),
                            }
                        )
                        voice_placeholder.markdown(
                            build_voice_messages_html(st.session_state.voice_messages),
                            unsafe_allow_html=True,
                        )
                        scroll_chat_to_bottom()
    else:
        _, graph = get_runtime()
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
            user_message = user_text.strip()
            history_snapshot = list(st.session_state.messages)
            st.session_state.messages.append(
                {"role": "user", "content": user_message}
            )
            chat_placeholder.markdown(
                build_messages_html(st.session_state.messages, thinking=True),
                unsafe_allow_html=True,
            )
            scroll_chat_to_bottom()
            with st.spinner("Pensando..."):
                try:
                    reply = run_chat(
                        graph, st.session_state.tenant_id, user_message, history_snapshot
                    )
                except Exception as exc:
                    reply = (
                        "No se pudo generar la respuesta. "
                        f"Detalles: {exc}"
                    )
            st.session_state.messages.append({"role": "assistant", "content": reply})
            chat_placeholder.markdown(
                build_messages_html(st.session_state.messages),
                unsafe_allow_html=True,
            )
            scroll_chat_to_bottom()
