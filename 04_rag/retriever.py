"""Search the manuals. Returns the best chunks with a citation for each."""

from functools import lru_cache

import chromadb
from embeddings import embed_query

from common.config import CHROMA_DIR

COLLECTION = "vardhan_docs"


@lru_cache
def _collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        return client.get_collection(COLLECTION)
    except Exception as err:
        raise FileNotFoundError("No RAG index yet. Run: python 04_rag/build_index.py") from err


def search(query: str, k: int = 4, files: list[str] | None = None) -> list[dict]:
    """Return the top-k chunks: text, citation "[doc § section]" and a similarity score.

    files: optionally only search these documents, e.g. ["vp-100-manual.md", "warranty-policy.md"]
    """
    where = {"source_file": {"$in": files}} if files else None
    result = _collection().query(query_embeddings=[embed_query(query)], n_results=k, where=where)
    hits = []
    for text, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        hits.append({
            "text": text,
            "doc": meta["doc"],
            "section": meta["section"],
            "citation": f"[{meta['doc']} § {meta['section']}]",
            "score": round(1 - distance, 3),   # cosine similarity, higher is better
        })
    return hits
