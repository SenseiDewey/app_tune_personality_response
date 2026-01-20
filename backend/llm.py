from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from backend.config import Settings


def get_chat_model(settings: Settings):
    if settings.llm_provider == "openai":
        api_key = settings.llm_api_key or settings.openai_api_key
        return ChatOpenAI(model=settings.chat_model, openai_api_key=api_key)
    return ChatOllama(model=settings.chat_model, base_url=settings.ollama_base_url)


def get_embedding_model(settings: Settings):
    if settings.llm_provider == "openai":
        api_key = settings.llm_api_key or settings.openai_api_key
        return OpenAIEmbeddings(model=settings.embedding_model, openai_api_key=api_key)
    return OllamaEmbeddings(
        model=settings.embedding_model, base_url=settings.ollama_base_url
    )
