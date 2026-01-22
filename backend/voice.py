from typing import Optional, Tuple

import requests

from backend.config import Settings


def transcribe_audio(
    settings: Settings, audio_bytes: bytes, mime_type: Optional[str]
) -> str:
    if not settings.elevenlabs_api_key:
        raise ValueError("Falta configurar ELEVENLABS_API_KEY.")
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {"xi-api-key": settings.elevenlabs_api_key}
    data = {"model_id": settings.elevenlabs_stt_model}
    files = {
        "file": (
            "recording.webm",
            audio_bytes,
            mime_type or "audio/webm",
        )
    }
    response = requests.post(
        url, headers=headers, data=data, files=files, timeout=60
    )
    response.raise_for_status()
    payload = response.json()
    return (payload.get("text") or "").strip()


def text_to_speech(
    settings: Settings, text: str
) -> Tuple[bytes, str]:
    if not settings.elevenlabs_api_key:
        raise ValueError("Falta configurar ELEVENLABS_API_KEY.")
    if not settings.elevenlabs_voice_id:
        raise ValueError("Falta configurar ELEVENLABS_VOICE_ID.")
    url = (
        "https://api.elevenlabs.io/v1/text-to-speech/"
        f"{settings.elevenlabs_voice_id}"
    )
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": settings.elevenlabs_tts_model,
    }
    if settings.elevenlabs_output_format:
        payload["output_format"] = settings.elevenlabs_output_format
    response = requests.post(
        url, headers=headers, json=payload, timeout=90
    )
    response.raise_for_status()
    return response.content, "audio/mpeg"
