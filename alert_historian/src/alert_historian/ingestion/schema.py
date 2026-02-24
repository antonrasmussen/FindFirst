from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
  return datetime.utcnow()


class RawRef(BaseModel):
  store: Literal["imap", "json_export"]
  folder: str | None = None
  uid: int | None = None
  path: str | None = None


class CanonicalAlertItem(BaseModel):
  item_id: str
  url: str
  url_normalized: str
  title: str
  snippet: str
  published_at: datetime | None = None
  source_domain: str


class CanonicalAlertPayload(BaseModel):
  schema_version: Literal["0.1"] = "0.1"
  source: Literal["google_alerts_imap", "google_alerts_export"]
  source_account: str
  source_message_id: str
  source_uid: str | None = None
  received_at: datetime = Field(default_factory=utc_now)
  alert_topic: str
  alert_query_raw: str | None = None
  items: list[CanonicalAlertItem]
  raw_ref: RawRef
