import logging
import time
from typing import Iterator, List, Tuple

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

    def ask(
        self,
        question: str,
        session_id: str,
        k: int | None = None,
        source_filter: str | None = None,
        mode: str = "original",
        role: str = "default",
        compare_sources: List[str] | None = None,
    ) -> Tuple[str, str, List[dict]]:
        start_time = time.perf_counter()
        top_k = k or TOP_K

        retrieval_start = time.perf_counter()
        docs = self._retrieve_docs(
            question=question,
            top_k=top_k,
            source_filter=source_filter,
            mode=mode,
            compare_sources=compare_sources,
        )
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

        prompt = self._build_prompt(
            question=question,
            history_text=history_text,
            context=context,
            mode=mode,
            role=role,
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

    def stream_ask(
        self,
        question: str,
        session_id: str,
        k: int | None = None,
        source_filter: str | None = None,
        mode: str = "original",
        role: str = "default",
        compare_sources: List[str] | None = None,
    ) -> tuple[Iterator[str], str, List[dict]]:
        top_k = k or TOP_K
        docs = self._retrieve_docs(
            question=question,
            top_k=top_k,
            source_filter=source_filter,
            mode=mode,
            compare_sources=compare_sources,
        )

        if not docs:
            empty_msg = "I could not find any indexed PDF content. Please upload at least one PDF first."

            def empty_iterator() -> Iterator[str]:
                yield empty_msg

            return empty_iterator(), "none", []

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

        prompt = self._build_prompt(
            question=question,
            history_text=history_text,
            context=context,
            mode=mode,
            role=role,
        )

        chunks: List[str] = []

        def generate() -> Iterator[str]:
            for chunk in self.llm.stream(prompt):
                text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                if text:
                    chunks.append(text)
                    yield text
            append_history(session_id, question, "".join(chunks))

        sources = [
            {
                "content": d.page_content,
                "source": d.metadata.get("source", "unknown"),
                "page": d.metadata.get("page"),
            }
            for d in docs
        ]

        return generate(), "ollama", sources

    def _retrieve_docs(
        self,
        question: str,
        top_k: int,
        source_filter: str | None,
        mode: str,
        compare_sources: List[str] | None,
    ):
        if mode == "compare" and compare_sources:
            merged_docs = []
            unique_sources = [s for s in dict.fromkeys(compare_sources) if s]
            for source in unique_sources[:4]:
                merged_docs.extend(
                    self.vector_store_service.similarity_search(
                        query=question,
                        k=max(1, top_k),
                        source_filter=source,
                    )
                )
            return merged_docs

        return self.vector_store_service.similarity_search(
            query=question,
            k=top_k,
            source_filter=source_filter,
        )

    @staticmethod
    def _build_prompt(
        question: str,
        history_text: str,
        context: str,
        mode: str,
        role: str,
    ) -> str:
        mode_instructions = {
            "original": "Answer directly and precisely.",
            "qa": "Focus on concise question-answer style with short factual bullets.",
            "summary": "Provide a concise summary with key points.",
            "deep_analysis": "Provide a deep analysis: assumptions, evidence, and implications.",
            "extract_data": "Extract structured facts, entities, dates, and numbers in bullet format.",
            "compare": "Compare the relevant documents with similarities, differences, and final recommendation.",
        }
        role_instructions = {
            "default": "Use neutral professional tone.",
            "student": "Explain clearly with simple language and learning-oriented guidance.",
            "hr": "Focus on policy, people-impact, compliance, and communication clarity.",
            "developer": "Focus on technical trade-offs, architecture, and implementation details.",
        }

        mode_text = mode_instructions.get(mode, mode_instructions["original"])
        role_text = role_instructions.get(role, role_instructions["default"])

        return (
            "You are a helpful assistant for question-answering over PDF documents.\n"
            "Use only the provided context to answer accurately.\n"
            "If the answer is not in context, say you do not know based on the uploaded PDFs.\n"
            f"Mode instruction: {mode_text}\n"
            f"Role instruction: {role_text}\n\n"
            f"Conversation history:\n{history_text}\n\n"
            f"Retrieved context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
