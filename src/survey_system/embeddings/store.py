"""FAISS-backed storage for question text chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import faiss  # type: ignore[import-untyped]
import numpy as np

from survey_system.embeddings.encoder import EmbeddingEncoder
from survey_system.exceptions import EmbeddingError


@dataclass(frozen=True)
class StoredChunk:
    """A retrievable text chunk with metadata."""

    text: str
    metadata: dict[str, Any]


class FAISSQuestionStore:
    """In-memory FAISS index over normalized embedding vectors."""

    def __init__(self, encoder: EmbeddingEncoder) -> None:
        """Create an empty store.

        Args:
            encoder: Embedding backend (dimension defines index shape).
        """
        self._encoder = encoder
        self._dim = encoder.dimension
        self._index = faiss.IndexFlatIP(self._dim)
        self._chunks: list[StoredChunk] = []

    @property
    def dimension(self) -> int:
        """Index vector dimension."""
        return self._dim

    def __len__(self) -> int:
        """Number of indexed vectors."""
        return int(self._index.ntotal)

    def add_texts(self, texts: list[str], metadatas: list[dict[str, Any]] | None = None) -> None:
        """Add texts and optional per-row metadata.

        Args:
            texts: Strings to embed and index.
            metadatas: Optional parallel list of metadata dicts.

        Raises:
            EmbeddingError: On shape mismatch or embedding failures.
        """
        if not texts:
            raise EmbeddingError("add_texts requires non-empty texts", details={})
        if metadatas is not None and len(metadatas) != len(texts):
            raise EmbeddingError(
                "metadatas length must match texts",
                details={"texts": len(texts), "metadatas": len(metadatas)},
            )
        vectors = self._encoder.encode(texts)
        if vectors.shape[0] != len(texts) or vectors.shape[1] != self._dim:
            raise EmbeddingError(
                "unexpected embedding shape",
                details={"shape": getattr(vectors, "shape", None)},
            )
        faiss.normalize_L2(vectors)
        self._index.add(vectors)
        for i, t in enumerate(texts):
            meta = metadatas[i] if metadatas else {}
            self._chunks.append(StoredChunk(text=t, metadata=dict(meta)))

    def search(self, query: str, *, top_k: int = 5) -> list[tuple[StoredChunk, float]]:
        """Return the top similar chunks for a query string.

        Args:
            query: Natural language query.
            top_k: Number of results.

        Returns:
            List of ``(chunk, score)`` pairs (higher is better for inner product).

        Raises:
            EmbeddingError: When the index is empty or search fails.
        """
        if self._index.ntotal == 0:
            raise EmbeddingError("index is empty", details={})
        if top_k < 1:
            raise EmbeddingError("top_k must be >= 1", details={"top_k": top_k})
        q = self._encoder.encode([query])
        if q.shape != (1, self._dim):
            raise EmbeddingError("unexpected query embedding shape", details={})
        faiss.normalize_L2(q)
        k = min(top_k, self._index.ntotal)
        try:
            scores, indices = self._index.search(q, k)
        except Exception as exc:
            raise EmbeddingError(
                "faiss search failed",
                details={"error": type(exc).__name__},
            ) from exc
        out: list[tuple[StoredChunk, float]] = []
        for score, idx in zip(scores[0].tolist(), indices[0].tolist(), strict=True):
            if idx < 0:
                continue
            out.append((self._chunks[idx], float(score)))
        return out
