"""Sentence-boundary-aware text chunking for the RAG corpus.

Uses a simple regex sentence splitter (no nltk download required) and a word-count
approximation of tokens (~0.75 words/token is typical for English; we chunk on word
count directly for simplicity, which keeps chunks in the right ballpark size).
"""
from __future__ import annotations

import re

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

CHUNK_SIZE_WORDS = 400  # ~500 tokens
OVERLAP_WORDS = 40  # ~50 tokens


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())
        if current_words + sentence_words > chunk_size and current:
            chunks.append(" ".join(current))
            # start next chunk with overlap: keep trailing sentences worth ~overlap words
            overlap_sentences: list[str] = []
            overlap_words = 0
            for s in reversed(current):
                w = len(s.split())
                if overlap_words + w > overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_words += w
            current = overlap_sentences
            current_words = overlap_words

        current.append(sentence)
        current_words += sentence_words

    if current:
        chunks.append(" ".join(current))

    return chunks
