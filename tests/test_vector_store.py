import os
import shutil
import pytest
from birka_memory_vault.vector_store import VectorStore

@pytest.fixture
def vs():
    test_dir = "/tmp/test_chroma_suite"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    vs = VectorStore(test_dir)
    yield vs
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

def test_upsert_query(vs):
    vs.upsert(101, "The capital of France is Paris", {"country": "France"})
    results = vs.query("What is the capital of France?")
    assert len(results) > 0
    assert results[0]["entry_id"] == 101
    assert "Paris" in results[0]["content"]

def test_delete(vs):
    vs.upsert(102, "Testing delete functionality")
    results = vs.query("Testing delete")
    assert any(r["entry_id"] == 102 for r in results)

    vs.delete([102])
    results = vs.query("Testing delete")
    assert not any(r["entry_id"] == 102 for r in results)
