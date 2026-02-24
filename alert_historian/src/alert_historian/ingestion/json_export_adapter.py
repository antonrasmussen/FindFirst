import json
from pathlib import Path
from typing import Any

from alert_historian.ingestion.normalize import normalize_item
from alert_historian.ingestion.schema import CanonicalAlertPayload, RawRef


def _get_items(raw: dict[str, Any]) -> list[dict[str, Any]]:
  items = raw.get("items")
  if isinstance(items, list):
    return items

  links = raw.get("urls", [])
  snippets = raw.get("snippets", [])
  titles = raw.get("titles", [])
  out: list[dict[str, Any]] = []
  for idx, url in enumerate(links):
    out.append({
        "url": url,
        "title": titles[idx] if idx < len(titles) else url,
        "snippet": snippets[idx] if idx < len(snippets) else "",
    })
  return out


def load_json_export(path: Path) -> list[CanonicalAlertPayload]:
  payload = json.loads(path.read_text(encoding="utf-8"))
  entries = payload if isinstance(payload, list) else [payload]
  out: list[CanonicalAlertPayload] = []
  for entry in entries:
    items = []
    for item in _get_items(entry):
      if not item.get("url"):
        continue
      items.append(
          normalize_item(
              url=str(item["url"]),
              title=str(item.get("title") or item["url"]),
              snippet=str(item.get("snippet") or ""),
          ))
    if not items:
      continue
    source_message_id = str(entry.get("source_message_id") or entry.get("id") or "")
    if not source_message_id:
      source_message_id = f"json:{hash(str(entry))}"
    out.append(
        CanonicalAlertPayload(
            source="google_alerts_export",
            source_account=str(entry.get("source_account") or "json-export"),
            source_message_id=source_message_id,
            source_uid=None,
            alert_topic=str(entry.get("alert_topic") or entry.get("topic") or "unknown-topic"),
            alert_query_raw=str(entry.get("alert_query_raw") or entry.get("query") or ""),
            items=items,
            raw_ref=RawRef(store="json_export", path=str(path)),
        ))
  return out
