from pathlib import Path
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from utils.config import CHUNK_OVERLAP, CHUNK_SIZE


def extract_pdf_documents(file_path: Path, source_name: str) -> List[Document]:
    """Load PDF with PyPDFLoader and split page text into chunks."""
    loader = PyPDFLoader(str(file_path))
    pages_as_docs = loader.load()

    for page in pages_as_docs:
        page.metadata["source"] = source_name

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(pages_as_docs)
