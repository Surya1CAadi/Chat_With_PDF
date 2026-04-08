from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from services.pdf_service import extract_pdf_documents
from services.vector_store_service import VectorStoreService
from utils.config import UPLOADS_DIR
from utils.schemas import UploadResponse

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        safe_name = Path(file.filename).name
        save_path = UPLOADS_DIR / safe_name

        with open(save_path, "wb") as out_file:
            out_file.write(await file.read())

        docs = extract_pdf_documents(save_path, source_name=safe_name)
        if not docs:
            raise HTTPException(status_code=400, detail="No extractable text found in PDF.")

        vector_store = VectorStoreService()
        chunks_added = vector_store.add_documents(docs)

        return UploadResponse(
            message="PDF processed and indexed successfully.",
            filename=safe_name,
            total_chunks_added=chunks_added,
        )
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(ex)}") from ex
