from fastapi import APIRouter

from services.vector_store_service import VectorStoreService

router = APIRouter()


@router.post("/reset-index")
def reset_index() -> dict:
    """Clear the current FAISS index so the next upload starts clean."""
    vector_store = VectorStoreService()
    vector_store.reset_index()
    return {"status": "ok", "message": "FAISS index reset successfully."}
