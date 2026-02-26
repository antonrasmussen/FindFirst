"""ChromaDB-backed vector store for alert items."""

from pathlib import Path
from typing import Callable

from alert_historian.state.store import PendingSyncItem

COLLECTION_NAME = "alert_items"


def _default_embedding_fn(
    texts: list[str],
    *,
    api_key: str,
    model: str = "text-embedding-3-small",
) -> list[list[float]]:
  """Embed texts using OpenAI API."""
  from openai import OpenAI

  client = OpenAI(api_key=api_key)
  resp = client.embeddings.create(input=texts, model=model)
  return [e.embedding for e in resp.data]


class AlertVectorStore:
  """Thin wrapper around ChromaDB for storing and querying alert items."""

  def __init__(
      self,
      persist_path: Path,
      embedding_fn: Callable[[list[str]], list[list[float]]] | None = None,
      *,
      api_key: str = "",
      embedding_model: str = "text-embedding-3-small",
  ):
    self._persist_path = Path(persist_path)
    self._persist_path.mkdir(parents=True, exist_ok=True)
    self._api_key = api_key
    self._embedding_model = embedding_model

    if embedding_fn is not None:
      self._embed = embedding_fn
    else:
      self._embed = lambda texts: _default_embedding_fn(
          texts, api_key=api_key, model=embedding_model
      )

    import chromadb

    self._client = chromadb.PersistentClient(path=str(self._persist_path))
    self._collection = self._client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

  def upsert_items(self, items: list[PendingSyncItem]) -> int:
    """Embed and store items. Returns count of items upserted."""
    if not items:
      return 0

    ids = [item.item_key for item in items]
    documents = [
        f"{item.title}\n{item.snippet}".strip() or item.url
        for item in items
    ]
    metadatas = [
        {
            "topic": item.topic,
            "day": item.day,
            "url": item.url,
            "title": item.title,
            "snippet": item.snippet[:500] if item.snippet else "",
        }
        for item in items
    ]

    embeddings = self._embed(documents)
    self._collection.upsert(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )
    return len(items)

  def query(
      self,
      text: str,
      n_results: int = 5,
      where: dict | None = None,
  ) -> list[dict]:
    """
    Semantic search. Returns list of dicts with keys:
    id, document, metadata, distance.
    """
    query_embedding = self._embed([text])[0]
    result = self._collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    out: list[dict] = []
    ids = result["ids"][0] if result["ids"] else []
    docs = result["documents"][0] if result["documents"] else []
    metas = result["metadatas"][0] if result["metadatas"] else []
    dists = result["distances"][0] if result["distances"] else []

    for i, id_val in enumerate(ids):
      out.append({
          "id": id_val,
          "document": docs[i] if i < len(docs) else "",
          "metadata": metas[i] if i < len(metas) else {},
          "distance": dists[i] if i < len(dists) else None,
      })
    return out
