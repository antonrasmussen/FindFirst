"""Unit tests for narrative module: vector store, chronicle, delta, daily report."""

from pathlib import Path

import pytest

from alert_historian.narrative.chronicle import load_chronicle, update_chronicle
from alert_historian.narrative.delta import generate_delta
from alert_historian.narrative.vector_store import AlertVectorStore
from alert_historian.reporting.daily_report import build_daily_report
from alert_historian.state.store import PendingSyncItem, StateStore


def _make_item(
    item_key: str = "key1",
    topic: str = "vector databases",
    day: str = "2026-02-26",
    title: str = "Test Title",
    snippet: str = "Test snippet about vectors",
) -> PendingSyncItem:
  return PendingSyncItem(
      item_key=item_key,
      message_key="msg1",
      topic=topic,
      day=day,
      url="https://example.com/a",
      url_normalized="https://example.com/a",
      title=title,
      snippet=snippet,
      source_domain="example.com",
      source_message_id="<m1>",
  )


def test_vector_store_upsert_and_query(tmp_path: Path) -> None:
  """Vector store upserts items and returns them on query."""
  dim = 4
  call_count = 0

  def mock_embed(texts: list[str]) -> list[list[float]]:
    nonlocal call_count
    call_count += 1
    return [[0.1 * (i + 1)] * dim for i in range(len(texts))]

  store = AlertVectorStore(tmp_path / "chroma", embedding_fn=mock_embed)
  items = [_make_item(item_key="k1"), _make_item(item_key="k2", topic="AI")]
  n = store.upsert_items(items)
  assert n == 2
  assert call_count == 1

  results = store.query("vector databases", n_results=2)
  assert len(results) == 2
  assert results[0]["id"] in ("k1", "k2")
  assert "metadata" in results[0]
  assert results[0]["metadata"].get("topic") in ("vector databases", "AI")


def test_vector_store_empty_upsert(tmp_path: Path) -> None:
  """Empty upsert returns 0."""
  store = AlertVectorStore(tmp_path / "chroma", embedding_fn=lambda t: [[]] * len(t))
  assert store.upsert_items([]) == 0


def test_load_chronicle_empty(tmp_path: Path) -> None:
  """load_chronicle returns template when file does not exist."""
  content = load_chronicle(tmp_path / "nonexistent.md")
  assert "# Alert Chronicle" in content
  assert "living timeline" in content


def test_load_chronicle_existing(tmp_path: Path) -> None:
  """load_chronicle returns file content when it exists."""
  path = tmp_path / "chronicle.md"
  path.write_text("# Custom Chronicle\n\nSome content.", encoding="utf-8")
  assert load_chronicle(path) == "# Custom Chronicle\n\nSome content."


def test_update_chronicle(tmp_path: Path) -> None:
  """update_chronicle calls LLM and writes result."""

  def mock_llm(user: str, system: str | None) -> str:
    assert "New context" in user
    assert "Preserve ALL existing" in (system or "")
    return "# Alert Chronicle\n\n## vector databases\n\n- 2026-02-26: New developments."

  path = tmp_path / "chronicle.md"
  path.write_text("# Alert Chronicle\n\n", encoding="utf-8")
  updated = update_chronicle(path, "New: Vector DB funding round.", mock_llm)
  assert "vector databases" in updated
  assert path.read_text(encoding="utf-8") == updated


def test_generate_delta_empty_items() -> None:
  """generate_delta returns empty string when no items."""
  def mock_llm(user: str, system: str | None) -> str:
    return "## Topic\n\nLink."
  assert generate_delta([], [], "", mock_llm) == ""


def test_generate_delta_with_items() -> None:
  """generate_delta produces markdown via LLM."""
  def mock_llm(user: str, system: str | None) -> str:
    assert "story links" in (system or "")
    assert "vector databases" in user
    return "## vector databases\n\nThis continues the trend from last month."

  items = [_make_item()]
  past = [{"metadata": {"topic": "vector databases", "day": "2026-02-20", "title": "Earlier news"}}]
  result = generate_delta(items, past, "Chronicle excerpt", mock_llm)
  assert "vector databases" in result


def test_build_daily_report_without_narrative(tmp_path: Path) -> None:
  """Report without narrative_delta has no Narrative Delta section."""
  db_path = tmp_path / "state.db"
  store = StateStore(db_path)
  try:
    path = build_daily_report(
        store, tmp_path / "reports", "run1", 0, {"synced": 0, "total": 0},
        narrative_delta=None,
    )
    content = path.read_text(encoding="utf-8")
    assert "## Sync Summary" in content
    assert "## Narrative Delta" not in content
    assert "## Topic Timeline" in content
  finally:
    store.close()


def test_build_daily_report_with_narrative(tmp_path: Path) -> None:
  """Report with narrative_delta includes Narrative Delta section."""
  db_path = tmp_path / "state.db"
  store = StateStore(db_path)
  try:
    path = build_daily_report(
        store, tmp_path / "reports", "run1", 0, {"synced": 0, "total": 0},
        narrative_delta="## vector databases\n\nContinues the trend.",
    )
    content = path.read_text(encoding="utf-8")
    assert "## Narrative Delta" in content
    assert "## vector databases" in content
    assert "Continues the trend" in content
  finally:
    store.close()


def test_build_daily_report_ignores_empty_narrative(tmp_path: Path) -> None:
  """Empty or whitespace narrative_delta is not included."""
  db_path = tmp_path / "state.db"
  store = StateStore(db_path)
  try:
    path = build_daily_report(
        store, tmp_path / "reports", "run1", 0, {"synced": 0, "total": 0},
        narrative_delta="   \n  ",
    )
    content = path.read_text(encoding="utf-8")
    assert "## Narrative Delta" not in content
  finally:
    store.close()
