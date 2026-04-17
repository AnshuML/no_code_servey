"""HuggingFace sentence embedding encoder."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np

from survey_system.exceptions import EmbeddingError


@runtime_checkable
class EmbeddingEncoder(Protocol):
    """Protocol for text embedding backends."""

    @property
    def dimension(self) -> int:
        """Vector dimensionality."""
        ...

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return a float32 matrix ``(len(texts), dimension)``."""
        ...


class HuggingFaceEncoder:
    """Sentence embeddings via ``sentence_transformers``."""

    def __init__(self, model_name: str, *, hf_token: str | None = None) -> None:
        """Load a sentence-transformers model.

        Args:
            model_name: HuggingFace model id or local path.
            hf_token: Optional token for private/gated models.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            raise EmbeddingError(
                "sentence_transformers is required for HuggingFaceEncoder",
                details={"error": type(exc).__name__},
            ) from exc

        kwargs: dict[str, Any] = {}
        if hf_token:
            kwargs["token"] = hf_token
        try:
            self._model = SentenceTransformer(model_name, **kwargs)
        except Exception as exc:
            raise EmbeddingError(
                "failed to load embedding model",
                details={"model_name": model_name, "error": type(exc).__name__},
            ) from exc
        dim = self._model.get_sentence_embedding_dimension()
        self._dimension: int = int(dim)

    @property
    def dimension(self) -> int:
        """Embedding vector size."""
        return self._dimension

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts to L2-normalized vectors for cosine similarity via inner product.

        Args:
            texts: Non-empty list of strings.

        Returns:
            Float32 array of shape ``(n, dimension)``.

        Raises:
            EmbeddingError: On encoder failures.
        """
        if not texts:
            raise EmbeddingError(
                "encode requires a non-empty list of texts",
                details={},
            )
        try:
            vectors = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as exc:
            raise EmbeddingError(
                "embedding encode failed",
                details={"error": type(exc).__name__},
            ) from exc
        if not isinstance(vectors, np.ndarray):
            vectors = np.asarray(vectors, dtype=np.float32)
        return vectors.astype(np.float32, copy=False)
