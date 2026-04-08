from typing import List, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    message: str
    filename: str
    total_chunks_added: int


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2)
    session_id: str = Field(default="default")
    k: Optional[int] = Field(default=None, ge=1, le=10)


class SourceChunk(BaseModel):
    content: str
    source: str
    page: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    session_id: str
    answer_provider: str
    sources: List[SourceChunk]
