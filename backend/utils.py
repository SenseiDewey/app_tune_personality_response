from datetime import datetime, timezone
import json
import re
import uuid
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_uuid() -> str:
    return str(uuid.uuid4())


def trim_chat_history(
    chat_history: List[Dict[str, str]], max_messages: int
) -> List[Dict[str, str]]:
    filtered = [
        message
        for message in chat_history
        if message.get("role") in ("user", "assistant")
    ]
    if max_messages > 0 and len(filtered) > max_messages:
        return filtered[-max_messages:]
    return filtered


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = cleaned.rstrip("`").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
