import logging
import time
from typing import List, Tuple

from langchain_ollama import ChatOllama

from services.history_service import append_history, get_history
from services.vector_store_service import VectorStoreService
from utils.config import (
    CHAT_MODEL,
    OLLAMA_BASE_URL,
    TOP_K,
)

_CHAT_LLM_CACHE = None
_CHAT_LLM_CACHE_KEY = None
logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self) -> None:
        self.vector_store_service = VectorStoreService()
        self.llm = self._get_primary_llm()

    @staticmethod
    def _get_primary_llm():
        global _CHAT_LLM_CACHE, _CHAT_LLM_CACHE_KEY

        cache_key = (CHAT_MODEL, OLLAMA_BASE_URL)
        if _CHAT_LLM_CACHE is not None and _CHAT_LLM_CACHE_KEY == cache_key:
            return _CHAT_LLM_CACHE

        client = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
        )

        _CHAT_LLM_CACHE = client
        _CHAT_LLM_CACHE_KEY = cache_key
        return client

    def ask(self, question: str, session_id: str, k: int | None = None) -> Tuple[str, str, List[dict]]:
        start_time = time.perf_counter()
        top_k = k or TOP_K

        retrieval_start = time.perf_counter()
        docs = self.vector_store_service.similarity_search(question, k=top_k)
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
        logger.info("/ask retrieval completed in %.0f ms (k=%s, docs=%s)", retrieval_ms, top_k, len(docs))

        if not docs:
            return (
                "I could not find any indexed PDF content. Please upload at least one PDF first.",
                "none",
                [],
            )

        context = "\n\n".join(
            [
                f"Source: {d.metadata.get('source', 'unknown')} | Page: {d.metadata.get('page', 'N/A')}\n{d.page_content}"
                for d in docs
            ]
        )

        history_lines = []
        for q, a in get_history(session_id):
            history_lines.append(f"User: {q}")
            history_lines.append(f"Assistant: {a}")
        history_text = "\n".join(history_lines)

        prompt = (
            "You are a helpful assistant for question-answering over PDF documents.\n"
            "Use the provided context to answer accurately.\n"
            "If the answer is not in context, say you do not know based on the uploaded PDFs.\n\n"
            f"Conversation history:\n{history_text}\n\n"
            f"Retrieved context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        llm_start = time.perf_counter()
        response = self.llm.invoke(prompt)
        llm_ms = (time.perf_counter() - llm_start) * 1000
        total_ms = (time.perf_counter() - start_time) * 1000
        logger.info("/ask llm completed in %.0f ms, total %.0f ms", llm_ms, total_ms)

        answer_provider = "ollama"
        answer = response.content if isinstance(response.content, str) else str(response.content)
        append_history(session_id, question, answer)

        sources = [
            {
                "content": d.page_content,
                "source": d.metadata.get("source", "unknown"),
                "page": d.metadata.get("page"),
            }
            for d in docs
        ]
        return answer, answer_provider, sources
