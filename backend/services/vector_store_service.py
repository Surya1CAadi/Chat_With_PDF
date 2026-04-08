import json
import logging
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

from utils.config import (
    EMBEDDING_MODEL,
    INDEX_DIR,
    INDEX_VERSION,
)

logger = logging.getLogger(__name__)
_EMBEDDINGS_CACHE = None
_EMBEDDINGS_CACHE_KEY = None
_VECTOR_STORE_CACHE = None
_VECTOR_STORE_CACHE_SIGNATURE = None
INDEX_META_FILE = INDEX_DIR / "index_meta.json"


class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> List[float]:
        vector = self.model.encode([text], normalize_embeddings=True)[0]
        return vector.tolist()


class VectorStoreService:
    """Handles creating, loading, saving, and querying the FAISS index."""

    def __init__(self) -> None:
        self.embeddings = self._get_embeddings_client()

    @staticmethod
    def _get_embeddings_client():
        global _EMBEDDINGS_CACHE, _EMBEDDINGS_CACHE_KEY

        cache_key = EMBEDDING_MODEL
        if _EMBEDDINGS_CACHE is not None and _EMBEDDINGS_CACHE_KEY == cache_key:
            return _EMBEDDINGS_CACHE

        client = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)

        _EMBEDDINGS_CACHE = client
        _EMBEDDINGS_CACHE_KEY = cache_key
        return client

    def _index_exists(self) -> bool:
        return (INDEX_DIR / "index.faiss").exists() and (INDEX_DIR / "index.pkl").exists()

    @staticmethod
    def _read_index_meta() -> dict:
        if not INDEX_META_FILE.exists():
            return {}
        try:
            return json.loads(INDEX_META_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_index_meta(self) -> None:
        meta = {
            "index_version": INDEX_VERSION,
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dimension": self.embeddings.dimension,
        }
        INDEX_META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    @staticmethod
    def _clear_index_files() -> None:
        for file_name in ["index.faiss", "index.pkl", "index_meta.json"]:
            file_path = INDEX_DIR / file_name
            if file_path.exists():
                file_path.unlink()

    def _is_compatible(self, store: FAISS) -> bool:
        store_dimension = getattr(getattr(store, "index", None), "d", None)
        if store_dimension is None:
            return False

        meta = self._read_index_meta()
        meta_version = meta.get("index_version")
        meta_dimension = meta.get("embedding_dimension")
        meta_model = meta.get("embedding_model")

        if meta_version is not None and int(meta_version) != int(INDEX_VERSION):
            return False

        if meta_model and meta_model != EMBEDDING_MODEL:
            return False

        return int(store_dimension) == int(self.embeddings.dimension) and (
            meta_dimension is None or int(meta_dimension) == int(self.embeddings.dimension)
        )

    @staticmethod
    def _index_signature() -> Optional[tuple[float, float]]:
        faiss_file = INDEX_DIR / "index.faiss"
        pkl_file = INDEX_DIR / "index.pkl"
        if not (faiss_file.exists() and pkl_file.exists()):
            return None
        return (faiss_file.stat().st_mtime, pkl_file.stat().st_mtime)

    def load(self) -> Optional[FAISS]:
        global _VECTOR_STORE_CACHE, _VECTOR_STORE_CACHE_SIGNATURE

        if not self._index_exists():
            return None
        signature = self._index_signature()
        if _VECTOR_STORE_CACHE is not None and _VECTOR_STORE_CACHE_SIGNATURE == signature:
            return _VECTOR_STORE_CACHE

        try:
            store = FAISS.load_local(
                folder_path=str(INDEX_DIR),
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as ex:
            logger.warning("FAISS index load failed, rebuilding index: %s", ex)
            self._clear_index_files()
            _VECTOR_STORE_CACHE = None
            _VECTOR_STORE_CACHE_SIGNATURE = None
            return None

        if not self._is_compatible(store):
            logger.info("FAISS index incompatible with current embeddings. Rebuilding from scratch.")
            self._clear_index_files()
            _VECTOR_STORE_CACHE = None
            _VECTOR_STORE_CACHE_SIGNATURE = None
            return None

        _VECTOR_STORE_CACHE = store
        _VECTOR_STORE_CACHE_SIGNATURE = signature
        return store

    def add_documents(self, documents: List[Document]) -> int:
        global _VECTOR_STORE_CACHE, _VECTOR_STORE_CACHE_SIGNATURE

        if not documents:
            return 0

        new_store = FAISS.from_documents(documents, self.embeddings)
        existing_store = self.load()

        if existing_store:
            try:
                existing_store.merge_from(new_store)
                existing_store.save_local(str(INDEX_DIR))
                _VECTOR_STORE_CACHE = existing_store
            except Exception as ex:
                logger.warning("FAISS merge failed, recreating index: %s", ex)
                self._clear_index_files()
                new_store.save_local(str(INDEX_DIR))
                _VECTOR_STORE_CACHE = new_store
        else:
            new_store.save_local(str(INDEX_DIR))
            _VECTOR_STORE_CACHE = new_store

        self._write_index_meta()
        _VECTOR_STORE_CACHE_SIGNATURE = self._index_signature()

        return len(documents)

    def reset_index(self) -> None:
        global _VECTOR_STORE_CACHE, _VECTOR_STORE_CACHE_SIGNATURE

        self._clear_index_files()
        _VECTOR_STORE_CACHE = None
        _VECTOR_STORE_CACHE_SIGNATURE = None

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        store = self.load()
        if not store:
            return []
        return store.similarity_search(query=query, k=k)
