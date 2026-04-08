import logging
import time

from fastapi import APIRouter, HTTPException

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
