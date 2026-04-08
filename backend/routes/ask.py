import logging
import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from services.rag_service import RAGService
from utils.schemas import AskRequest, AskResponse, SourceChunk

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    start = time.perf_counter()
    logger.info("/ask started (session_id=%s)", payload.session_id)
    try:
        rag_service = RAGService()
        answer, answer_provider, sources = rag_service.ask(
            question=payload.question,
            session_id=payload.session_id,
            k=payload.k,
            source_filter=payload.source_filter,
            mode=payload.mode,
            role=payload.role,
            compare_sources=payload.compare_sources,
        )

        logger.info("/ask finished in %.0f ms (provider=%s)", (time.perf_counter() - start) * 1000, answer_provider)

        return AskResponse(
            answer=answer,
            session_id=payload.session_id,
            answer_provider=answer_provider,
            sources=[SourceChunk(**item) for item in sources],
        )
    except ValueError as ex:
        logger.exception("/ask validation error")
        raise HTTPException(status_code=400, detail=str(ex)) from ex
    except Exception as ex:
        message = str(ex).lower()
        if "quota" in message or "429" in message or "resourceexhausted" in message:
            raise HTTPException(status_code=429, detail=str(ex)) from ex
        logger.exception("/ask failed")
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(ex)}") from ex


@router.post("/ask-stream")
def ask_question_stream(payload: AskRequest) -> StreamingResponse:
    try:
        rag_service = RAGService()
        stream_iter, answer_provider, sources = rag_service.stream_ask(
            question=payload.question,
            session_id=payload.session_id,
            k=payload.k,
            source_filter=payload.source_filter,
            mode=payload.mode,
            role=payload.role,
            compare_sources=payload.compare_sources,
        )

        def event_stream():
            yield f"data: {json.dumps({'type': 'ready'})}\n\n"
            for chunk in stream_iter:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'provider': answer_provider, 'sources': sources})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as ex:
        logger.exception("/ask-stream failed")
        raise HTTPException(status_code=500, detail=f"Failed to stream answer: {str(ex)}") from ex
