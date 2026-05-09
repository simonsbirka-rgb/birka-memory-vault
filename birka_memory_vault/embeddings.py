# birka_memory_vault/embeddings.py
from sentence_transformers import SentenceTransformer
from functools import lru_cache
from typing import List

DEFAULT_MODEL = "all-MiniLM-L6-v2"  # 80MB, 384-dim, fast

@lru_cache(maxsize=1)
def get_encoder(model_name: str = DEFAULT_MODEL) -> SentenceTransformer:
    return SentenceTransformer(model_name)

def embed(text: str, model_name: str = DEFAULT_MODEL) -> List[float]:
    return get_encoder(model_name).encode(text).tolist()

def embed_batch(texts: List[str], model_name: str = DEFAULT_MODEL) -> List[List[float]]:
    return get_encoder(model_name).encode(texts).tolist()
