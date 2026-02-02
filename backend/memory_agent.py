import re
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from backend.config import Settings
from backend.llm import get_chat_model, get_embedding_model
from backend.memory_schema import MemoryDecision
from backend.prompts import (
    MEMORY_DECIDER_SYSTEM_PROMPT,
    MEMORY_DECIDER_USER_PROMPT,
    SYSTEM_CHAT_PROMPT,
)
from backend.qdrant_store import QdrantStore
from backend.utils import extract_json, new_uuid, trim_chat_history, utc_now_iso


_CROSS_USER_REFUSAL = "No puedo acceder a memorias de otros usuarios."
_SELF_REFERENCES = {"mi", "mis", "mio", "mia", "mios", "mias", "yo"}


class ChatState(TypedDict):
    tenant_id: str
    user_message: str
    chat_history: List[Dict[str, str]]
    system_prompt: str
    retrieved_memories: List[Dict[str, Any]]
    assistant_answer: str
    memory_decision: Optional[MemoryDecision]


def _format_memories(memories: List[Dict[str, Any]]) -> str:
    if not memories:
        return ""
    lines = ["Recuerdos relevantes:"]
    for memory in memories:
        memory_type = memory.get("memory_type", "fact")
        importance = memory.get("importance", 3)
        text = memory.get("text", "")
        lines.append(f"- ({memory_type}, importance {importance}) {text}")
    return "\n".join(lines)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.lower().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return cleaned


def _messages_from_history(history: List[Dict[str, str]]) -> List:
    messages = []
    for message in history:
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def _is_cross_user_request(user_message: str, tenant_id: str) -> bool:
    if not user_message or not tenant_id:
        return False
    message = user_message.lower()
    if "otro usuario" in message or "otra persona" in message:
        return True
    patterns = [
        r"(?:memorias|recuerdos)\s+de\s+([\w.-]+)",
        r"de\s+usuario\s+([\w.-]+)",
        r"del\s+usuario\s+([\w.-]+)",
        r"\busuario\s+([\w.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if not match:
            continue
        target = match.group(1).strip()
        if not target or target in _SELF_REFERENCES:
            continue
        if target != tenant_id.lower():
            return True
    return False


def build_memory_graph(settings: Settings):
    chat_model = get_chat_model(settings)
    embeddings = get_embedding_model(settings)
    store = QdrantStore(settings)

    def retrieve_memories(state: ChatState) -> Dict[str, Any]:
        query = state.get("user_message", "").strip()
        if not query:
            return {"retrieved_memories": []}
        query_vector = embeddings.embed_query(query)
        results = store.search(query_vector, state["tenant_id"], settings.memory_top_k)
        memories = []
        for result in results:
            payload = result.payload or {}
            memories.append(
                {
                    "memory_id": payload.get("memory_id", str(result.id)),
                    "memory_type": payload.get("memory_type", "fact"),
                    "text": payload.get("text", ""),
                    "created_at": payload.get("created_at", ""),
                    "importance": payload.get("importance", 3),
                }
            )
        return {"retrieved_memories": memories}

    def generate_answer(state: ChatState) -> Dict[str, Any]:
        history = trim_chat_history(
            state.get("chat_history", []), settings.history_max_messages
        )
        system_prompt = state.get("system_prompt") or SYSTEM_CHAT_PROMPT
        messages = [SystemMessage(content=system_prompt)]
        memory_context = _format_memories(state.get("retrieved_memories", []))
        if memory_context:
            messages.append(SystemMessage(content=memory_context))
        messages.extend(_messages_from_history(history))
        messages.append(HumanMessage(content=state["user_message"]))
        response = chat_model.invoke(messages)
        return {"assistant_answer": response.content.strip()}

    def decide_memory(state: ChatState) -> Dict[str, Any]:
        prompt = MEMORY_DECIDER_USER_PROMPT.format(
            user_message=state["user_message"],
        )
        response = chat_model.invoke(
            [
                SystemMessage(content=MEMORY_DECIDER_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        payload = extract_json(response.content)
        if not payload:
            return {"memory_decision": None}
        try:
            decision = MemoryDecision.model_validate(payload)
        except Exception:
            return {"memory_decision": None}
        if decision.should_store and decision.memory is None:
            return {"memory_decision": None}
        return {"memory_decision": decision}

    def store_memory(state: ChatState) -> Dict[str, Any]:
        decision = state.get("memory_decision")
        if not decision or not decision.should_store or not decision.memory:
            return {}
        candidate = decision.memory
        candidate_text_norm = _normalize_text(candidate.text)
        if not candidate_text_norm:
            return {}
        retrieved = state.get("retrieved_memories", [])
        for memory in retrieved:
            existing_norm = _normalize_text(memory.get("text", ""))
            if existing_norm and existing_norm == candidate_text_norm:
                return {}
        vector = embeddings.embed_query(candidate.text)
        similar = store.search(vector, state["tenant_id"], settings.memory_top_k)
        for match in similar:
            if match.score is not None and match.score >= settings.memory_dedup_threshold:
                # Skip near-duplicates; update strategy can be added later.
                return {}
        memory_id = new_uuid()
        payload = {
            "tenant_id": state["tenant_id"],
            "memory_id": memory_id,
            "memory_type": candidate.memory_type,
            "text": candidate.text,
            "created_at": utc_now_iso(),
            "importance": candidate.importance,
            "source": "chat",
        }
        store.upsert(memory_id, vector, payload)
        return {}

    graph = StateGraph(ChatState)
    graph.add_node("retrieve_memories", retrieve_memories)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("decide_memory", decide_memory)
    graph.add_node("store_memory", store_memory)

    graph.set_entry_point("retrieve_memories")
    graph.add_edge("retrieve_memories", "generate_answer")
    graph.add_edge("generate_answer", "decide_memory")
    graph.add_edge("decide_memory", "store_memory")
    graph.add_edge("store_memory", END)

    return graph.compile()


def run_chat(
    graph,
    tenant_id: str,
    user_message: str,
    chat_history: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
) -> str:
    if _is_cross_user_request(user_message, tenant_id):
        return _CROSS_USER_REFUSAL
    prompt = system_prompt or SYSTEM_CHAT_PROMPT
    result = graph.invoke(
        {
            "tenant_id": tenant_id,
            "user_message": user_message,
            "chat_history": chat_history,
            "system_prompt": prompt,
        }
    )
    return result.get("assistant_answer", "").strip()
