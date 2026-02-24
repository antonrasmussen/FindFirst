from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from alert_historian.ingestion.schema import CanonicalAlertItem, CanonicalAlertPayload, RawRef
from alert_historian.state.store import StateStore
from alert_historian.sync import engine


@dataclass
class FakeSettings:
  findfirst_base_url: str = "http://localhost:9000"
  findfirst_username: str = "jsmith"
  findfirst_password: str = "test"
  sync_batch_size: int = 100
  use_domain_tags: bool = True
  imap_folder: str = "INBOX"


class FakeResp:
  def __init__(self, status_code: int, data, text: str = ""):
    self.status_code = status_code
    self.data = data
    self.text = text


class FakeClient:
  def __init__(self, _settings):
    self.tags = {"source/google-alerts": 1}

  def signin(self):
    return FakeResp(200, {"ok": True})

  def list_tags(self):
    rows = [{"id": v, "title": k, "bookmarks": []} for k, v in self.tags.items()]
    return FakeResp(200, rows)

  def create_tags(self, titles):
    next_id = max(self.tags.values(), default=0) + 1
    for title in titles:
      if title not in self.tags:
        self.tags[title] = next_id
        next_id += 1
    return FakeResp(200, [])

  def bulk_add_bookmarks(self, payload):
    return FakeResp(200, [{"id": i + 1000} for i, _ in enumerate(payload)])


def test_sync_engine_success(tmp_path: Path, monkeypatch) -> None:
  monkeypatch.setattr(engine, "FindFirstClient", FakeClient)
  db_path = tmp_path / "state.db"
  store = StateStore(db_path)
  try:
    payload = CanonicalAlertPayload(
        source="google_alerts_export",
        source_account="json-export",
        source_message_id="<m1>",
        source_uid=None,
        received_at=datetime.utcnow(),
        alert_topic="vector databases",
        alert_query_raw="vector databases",
        items=[
            CanonicalAlertItem(
                item_id="i1",
                url="https://example.com/a",
                url_normalized="https://example.com/a",
                title="A",
                snippet="S",
                source_domain="example.com",
            )
        ],
        raw_ref=RawRef(store="json_export", path="sample.json"),
    )
    inserted = store.save_payloads([payload])
    assert inserted == 1
    stats = engine.sync_pending_items(FakeSettings(), store, "run-1")
    assert stats["synced"] == 1
    assert stats["total"] == 1
  finally:
    store.close()
