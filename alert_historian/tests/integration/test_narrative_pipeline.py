"""Integration test: narrative pipeline produces enriched report with Narrative Delta."""

from datetime import datetime
from pathlib import Path

from alert_historian.ingestion.schema import CanonicalAlertItem, CanonicalAlertPayload, RawRef
from alert_historian.ingestion.pipeline import payloads_to_pending_items
from alert_historian.narrative.chronicle import load_chronicle, update_chronicle
from alert_historian.narrative.delta import generate_delta
from alert_historian.narrative.vector_store import AlertVectorStore
from alert_historian.reporting.daily_report import build_daily_report
from alert_historian.state.store import StateStore


def _make_payload(topic: str, title: str) -> CanonicalAlertPayload:
  return CanonicalAlertPayload(
      source="google_alerts_export",
      source_account="test@example.com",
      source_message_id="<msg1>",
      source_uid=None,
      received_at=datetime.utcnow(),
      alert_topic=topic,
      alert_query_raw=topic,
      items=[
          CanonicalAlertItem(
              item_id="i1",
              url="https://example.com/a",
              url_normalized="https://example.com/a",
              title=title,
              snippet="Vector database company raises Series B.",
              source_domain="example.com",
          )
      ],
      raw_ref=RawRef(store="json_export", path="sample.json"),
  )


def test_narrative_pipeline_enriched_report(tmp_path: Path) -> None:
  """
  With mocked LLM and embeddings, run the narrative pipeline components
  and verify the enriched report contains a Narrative Delta section.
  """
  payloads = [
      _make_payload("vector databases", "Pinecone funding"),
      _make_payload("AI agents", "Agentic workflows"),
  ]
  today_items = payloads_to_pending_items(payloads)
  assert len(today_items) == 2

  def mock_embed(texts: list[str]) -> list[list[float]]:
    return [[0.1] * 8 for _ in texts]

  def mock_llm(user: str, system: str | None) -> str:
    return "## vector databases\n\nContinues the trend from Q1.\n\n## AI agents\n\nNew developments."

  chroma_path = tmp_path / "chroma"
  chronicle_path = tmp_path / "chronicle.md"
  reports_path = tmp_path / "reports"
  db_path = tmp_path / "state.db"

  vector_store = AlertVectorStore(chroma_path, embedding_fn=mock_embed)
  vector_store.upsert_items(today_items)
  past_context = vector_store.query("vector databases funding", n_results=5)

  new_context = "\n\n".join(
      f"[{i.day}] {i.topic}: {i.title}\n{i.snippet[:100]}"
      for i in today_items
  )
  update_chronicle(chronicle_path, new_context, mock_llm)
  chronicle_content = load_chronicle(chronicle_path)

  delta = generate_delta(today_items, past_context, chronicle_content, mock_llm)
  assert "vector databases" in delta or "AI agents" in delta

  store = StateStore(db_path)
  try:
    path = build_daily_report(
        store,
        reports_path,
        "run1",
        inserted_count=2,
        sync_stats={"synced": 2, "duplicate": 0, "retryable_failed": 0, "permanent_failed": 0, "total": 2},
        narrative_delta=delta,
    )
    content = path.read_text(encoding="utf-8")
    assert "## Narrative Delta" in content
    assert "## Ingest Summary" in content
    assert "## Sync Summary" in content
    assert "## Topic Timeline" in content
  finally:
    store.close()
