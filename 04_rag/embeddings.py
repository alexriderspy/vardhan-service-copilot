"""Turn text into vectors. Local bge-small by default, OpenAI optional (EMBEDDINGS=openai)."""

from functools import lru_cache

from common.config import EMBEDDINGS, LOCAL_EMBED_MODEL

# bge models work best when search queries get this instruction prefix (documents don't).
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache
def _local_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(LOCAL_EMBED_MODEL)


def embed_documents(texts: list[str]) -> list[list[float]]:
    if EMBEDDINGS == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small").embed_documents(texts)
    return _local_model().encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


def embed_query(text: str) -> list[float]:
    if EMBEDDINGS == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small").embed_query(text)
    return _local_model().encode(BGE_QUERY_PREFIX + text, normalize_embeddings=True, show_progress_bar=False).tolist()
