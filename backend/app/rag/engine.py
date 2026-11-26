"""
RAG Engine — document ingestion, embedding, FAISS storage and retrieval.
Supports PDF, TXT and DOCX ingestion.
"""
from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGEngine:
    """Singleton RAG engine. Call initialise() once at startup."""

    _instance: Optional["RAGEngine"] = None

    def __init__(self):
        self.index_path = Path(settings.faiss_index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)

        self.embedder = SentenceTransformer(settings.embedding_model)
        self.dim = self.embedder.get_sentence_embedding_dimension()

        self.index: faiss.Index = faiss.IndexFlatL2(self.dim)
        self.chunks: List[str] = []          # parallel list of text chunks
        self.metadata: List[dict] = []       # source, doc_id, chunk_index

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        self._load_from_disk()

    # ── Singleton ─────────────────────────────────────────
    @classmethod
    def get(cls) -> "RAGEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Persistence ───────────────────────────────────────
    def _load_from_disk(self):
        idx_file = self.index_path / "index.faiss"
        meta_file = self.index_path / "meta.pkl"
        if idx_file.exists() and meta_file.exists():
            self.index = faiss.read_index(str(idx_file))
            with open(meta_file, "rb") as f:
                data = pickle.load(f)
                self.chunks = data["chunks"]
                self.metadata = data["metadata"]
            logger.info("RAG: loaded %d chunks from disk", len(self.chunks))

    def _save_to_disk(self):
        faiss.write_index(self.index, str(self.index_path / "index.faiss"))
        with open(self.index_path / "meta.pkl", "wb") as f:
            pickle.dump({"chunks": self.chunks, "metadata": self.metadata}, f)

    # ── Ingestion ─────────────────────────────────────────
    def ingest_file(self, file_path: str, doc_id: str) -> int:
        """Load, split and embed a document. Returns number of chunks added."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            loader = PyPDFLoader(str(path))
        elif ext == ".txt":
            loader = TextLoader(str(path), encoding="utf-8")
        elif ext in (".docx", ".doc"):
            loader = Docx2txtLoader(str(path))
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        documents = loader.load()
        splits = self.splitter.split_documents(documents)

        texts = [doc.page_content for doc in splits]
        if not texts:
            return 0

        embeddings = self.embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        embeddings = embeddings.astype(np.float32)

        self.index.add(embeddings)
        self.chunks.extend(texts)
        self.metadata.extend(
            {"source": path.name, "doc_id": doc_id, "chunk_index": i}
            for i, _ in enumerate(texts)
        )

        self._save_to_disk()
        logger.info("RAG: indexed %d chunks from %s", len(texts), path.name)
        return len(texts)

    # ── Retrieval ─────────────────────────────────────────
    def retrieve(self, query: str, top_k: int = 5) -> List[dict]:
        """Return top_k relevant chunks for a query."""
        if self.index.ntotal == 0:
            return []

        q_emb = self.embedder.encode([query], convert_to_numpy=True).astype(np.float32)
        distances, indices = self.index.search(q_emb, min(top_k, self.index.ntotal))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            results.append({
                "text": self.chunks[idx],
                "score": float(dist),
                "source": self.metadata[idx].get("source", "unknown"),
            })
        return results

    def format_context(self, results: List[dict]) -> str:
        """Format retrieved chunks into a context block for the LLM."""
        if not results:
            return ""
        parts = []
        for r in results:
            parts.append(f"[Source: {r['source']}]\n{r['text']}")
        return "\n\n---\n\n".join(parts)
