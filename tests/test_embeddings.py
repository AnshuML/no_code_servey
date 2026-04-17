"""Tests for embeddings + FAISS store (without downloading models)."""

from __future__ import annotations

import numpy as np
import pytest

from survey_system.embeddings.store import FAISSQuestionStore
from survey_system.exceptions import EmbeddingError


class _FakeEncoder:
    """Deterministic pseudo-embeddings for unit tests."""

    def __init__(self, dim: int = 8) -> None:
        """Set vector size."""
        self._dim = dim

    @property
    def dimension(self) -> int:
        """Vector dimension."""
        return self._dim

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return identical normalized vectors so search order is stable in tests."""
        v = np.ones((len(texts), self._dim), dtype=np.float32)
        faiss = __import__("faiss")
        faiss.normalize_L2(v)
        return v


def test_faiss_store_search_returns_results() -> None:
    """Indexing and search return scored chunks."""
    store = FAISSQuestionStore(_FakeEncoder(dim=4))
    store.add_texts(
        ["hello world", "goodbye moon"],
        metadatas=[{"id": "a"}, {"id": "b"}],
    )
    results = store.search("hello", top_k=1)
    assert len(results) == 1
    chunk, score = results[0]
    assert chunk.text == "hello world"
    assert score > 0


def test_empty_index_errors() -> None:
    """Searching an empty index raises ``EmbeddingError``."""
    store = FAISSQuestionStore(_FakeEncoder(dim=4))
    with pytest.raises(EmbeddingError):
        store.search("x")
