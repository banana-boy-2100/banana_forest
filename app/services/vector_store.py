import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

_client: chromadb.Client | None = None
COLLECTION_NAME = "sales_knowledge"


def get_chroma() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection() -> chromadb.Collection:
    client = get_chroma()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_knowledge(doc_id: str, content: str, metadata: dict) -> None:
    col = get_collection()
    col.upsert(
        ids=[doc_id],
        documents=[content],
        metadatas=[metadata],
    )


def search_knowledge(query: str, n_results: int = 5, where: dict | None = None) -> list[dict]:
    col = get_collection()
    kwargs = dict(query_texts=[query], n_results=min(n_results, col.count() or 1))
    if where:
        kwargs["where"] = where

    results = col.query(**kwargs)
    items = []
    for i, doc_id in enumerate(results["ids"][0]):
        items.append({
            "id": doc_id,
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return items


def delete_knowledge(doc_id: str) -> None:
    col = get_collection()
    col.delete(ids=[doc_id])
