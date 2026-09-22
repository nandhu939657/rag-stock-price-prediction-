"""Local embedding model for RAG. Groq does not serve an embeddings endpoint, so we run
all-MiniLM-L6-v2 (384 dims, CPU-friendly, no external API/cost) via sentence-transformers.
Loaded once as a module-level singleton - first call downloads the model (~90MB).
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()

EMBEDDING_DIM = 384


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model sentence-transformers/all-MiniLM-L6-v2 ...")
                _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
