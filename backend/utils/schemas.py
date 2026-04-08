from typing import List, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    message: str
    filename: str
    total_chunks_added: int


class UploadUrlRequest(BaseModel):
    url: str = Field(..., min_length=8)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2)
    session_id: str = Field(default="default")
    k: Optional[int] = Field(default=None, ge=1, le=10)
    source_filter: Optional[str] = Field(default=None)
    mode: str = Field(default="original")
    role: str = Field(default="default")
    compare_sources: Optional[List[str]] = Field(default=None)
    stream: bool = Field(default=False)


class SourceChunk(BaseModel):
    content: str
    source: str
    page: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    session_id: str
    answer_provider: str
    sources: List[SourceChunk]
