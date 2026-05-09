import asyncio
import pytest
from birka_memory_vault.embeddings import embed, embed_batch

def test_embed():
    v = embed("hello world")
    assert len(v) == 384
    assert isinstance(v[0], float)

def test_embed_batch():
    texts = ["hello", "world"]
    vectors = embed_batch(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
