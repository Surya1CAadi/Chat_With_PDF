from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from fastapi import APIRouter, File, HTTPException, UploadFile

from services.pdf_service import extract_pdf_documents
from services.vector_store_service import VectorStoreService
from utils.config import UPLOADS_DIR
from utils.schemas import UploadResponse, UploadUrlRequest

router = APIRouter()


def _resolve_download_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "drive.google.com" in host:
        # Support typical Drive share URLs.
        if "/file/d/" in parsed.path:
            file_id = parsed.path.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        query = parse_qs(parsed.query)
        if "id" in query and query["id"]:
            return f"https://drive.google.com/uc?export=download&id={query['id'][0]}"

    return url


def _download_pdf(url: str) -> tuple[bytes, str]:
    download_url = _resolve_download_url(url)
    req = Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=45) as response:
        content_type = (response.headers.get("Content-Type") or "").lower()
        payload = response.read()

    if not payload:
        raise ValueError("Downloaded file is empty.")

    if "pdf" not in content_type and not payload.startswith(b"%PDF"):
        raise ValueError("URL did not return a PDF file.")

    parsed = urlparse(url)
    candidate_name = Path(parsed.path).name or "remote.pdf"
    if not candidate_name.lower().endswith(".pdf"):
        candidate_name = f"{candidate_name}.pdf"
    safe_name = Path(candidate_name).name
    return payload, safe_name


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


@router.post("/upload-url", response_model=UploadResponse)
async def upload_pdf_from_url(payload: UploadUrlRequest) -> UploadResponse:
    try:
        raw_bytes, filename = _download_pdf(payload.url)
        save_path = UPLOADS_DIR / filename
        with open(save_path, "wb") as out_file:
            out_file.write(raw_bytes)

        docs = extract_pdf_documents(save_path, source_name=filename)
        if not docs:
            raise HTTPException(status_code=400, detail="No extractable text found in PDF.")

        vector_store = VectorStoreService()
        chunks_added = vector_store.add_documents(docs)

        return UploadResponse(
            message="PDF downloaded and indexed successfully.",
            filename=filename,
            total_chunks_added=chunks_added,
        )
    except HTTPException:
        raise
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex)) from ex
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF URL: {str(ex)}") from ex
