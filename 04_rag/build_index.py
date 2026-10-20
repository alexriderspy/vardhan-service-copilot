"""Chapter 4a: chunk the manuals + warranty policy and store them in Chroma.

Run:  python 04_rag/build_index.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import chromadb  # noqa: E402
from chunking import chunk_markdown  # noqa: E402
from embeddings import embed_documents  # noqa: E402

from common.config import CHROMA_DIR, CLIENT_DOCS, EMBEDDINGS  # noqa: E402

COLLECTION = "vardhan_docs"


def main() -> None:
    chunks = [c for path in sorted(CLIENT_DOCS.glob("*.md")) for c in chunk_markdown(path)]
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)   # rebuild from scratch every time
    collection = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embed_documents([c["text"] for c in chunks]),
        metadatas=[{"doc": c["doc"], "section": c["section"], "source_file": c["source_file"]} for c in chunks],
    )
    print(f"Indexed {len(chunks)} chunks from {len(list(CLIENT_DOCS.glob('*.md')))} documents "
          f"(embeddings={EMBEDDINGS}) -> {CHROMA_DIR}")


if __name__ == "__main__":
    main()
