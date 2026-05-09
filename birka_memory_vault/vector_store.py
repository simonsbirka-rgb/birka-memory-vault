# birka_memory_vault/vector_store.py
import chromadb
from typing import List, Optional, Dict

DEFAULT_PERSIST_DIR = "./chroma_data"

class VectorStore:
    def __init__(self, persist_dir: str = DEFAULT_PERSIST_DIR):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="memory_entries",
            metadata={"hnsw:space": "cosine"}
        )

    def upsert(self, entry_id: int, content: str, metadata: Optional[Dict] = None):
        from .embeddings import embed
        vector = embed(content)
        meta = metadata or {}
        self.collection.upsert(
            ids=[str(entry_id)],
            embeddings=[vector],
            documents=[content],
            metadatas=[{**meta, "entry_id": entry_id}]
        )

    def query(self, query_text: str, n_results: int = 10) -> List[Dict]:
        """Pure semantic similarity search. No tag filtering here — tags are handled by SQL in HybridRetriever."""
        from .embeddings import embed
        query_vector = embed(query_text)
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        return [
            {
                "entry_id": int(m["entry_id"]),
                "content": d,
                "distance": dist,
                "metadata": m,
            }
            for d, m, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def delete(self, entry_ids: List[int]):
        if entry_ids:
            self.collection.delete(ids=[str(eid) for eid in entry_ids])
