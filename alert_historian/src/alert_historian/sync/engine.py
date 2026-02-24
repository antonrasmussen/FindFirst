from collections import defaultdict
from itertools import islice

from alert_historian.config.settings import Settings
from alert_historian.state.store import PendingSyncItem, StateStore
from alert_historian.sync.findfirst_client import FindFirstClient
from alert_historian.sync.mappers import tag_titles_for_item, to_add_bkmk_req
from alert_historian.sync.retry import MAX_ATTEMPTS_PER_RUN, backoff_sleep, classify_http_status


def chunked(seq: list[PendingSyncItem], size: int):
  it = iter(seq)
  while True:
    chunk = list(islice(it, size))
    if not chunk:
      return
    yield chunk


def _tag_id_map(client: FindFirstClient) -> dict[str, int]:
  resp = client.list_tags()
  if resp.status_code != 200:
    return {}
  out: dict[str, int] = {}
  for t in resp.data:
    if isinstance(t, dict) and "title" in t and "id" in t:
      out[str(t["title"])] = int(t["id"])
  return out


def _ensure_tags(client: FindFirstClient, titles: list[str]) -> dict[str, int]:
  tag_map = _tag_id_map(client)
  missing = [t for t in titles if t not in tag_map]
  if missing:
    client.create_tags(missing)
    tag_map = _tag_id_map(client)
  return tag_map


def sync_pending_items(settings: Settings, store: StateStore, run_id: str) -> dict[str, int]:
  client = FindFirstClient(settings)
  signin_resp = client.signin()
  if signin_resp.status_code != 200:
    raise RuntimeError(f"FindFirst signin failed ({signin_resp.status_code})")

  pending = store.get_pending_items(run_id)
  if not pending:
    return {"synced": 0, "duplicate": 0, "retryable_failed": 0, "permanent_failed": 0, "total": 0}

  all_tag_titles: set[str] = set()
  for item in pending:
    all_tag_titles.update(tag_titles_for_item(item, settings.use_domain_tags))
  tag_map = _ensure_tags(client, sorted(all_tag_titles))

  counters = defaultdict(int)
  batch_size = max(1, min(100, settings.sync_batch_size))
  for batch in chunked(pending, batch_size):
    payload: list[dict[str, object]] = []
    for item in batch:
      tag_titles = tag_titles_for_item(item, settings.use_domain_tags)
      tag_ids = [tag_map[t] for t in tag_titles if t in tag_map]
      payload.append(to_add_bkmk_req(item, tag_ids))

    resp = client.bulk_add_bookmarks(payload)
    decision = classify_http_status(resp.status_code, resp.text)

    if resp.status_code == 200 and isinstance(resp.data, list):
      # Bulk endpoint can return null entries for failures; resolve per item.
      for idx, item in enumerate(batch):
        result_obj = resp.data[idx] if idx < len(resp.data) else None
        attempt = store.get_attempt_count(item.item_key) + 1
        if isinstance(result_obj, dict) and result_obj.get("id"):
          store.record_sync_attempt(item.item_key, run_id, "synced", attempt, bookmark_id=int(result_obj["id"]))
          counters["synced"] += 1
        elif attempt >= MAX_ATTEMPTS_PER_RUN:
          store.record_sync_attempt(item.item_key, run_id, "permanent_failed", attempt, "bulk-item-null-max-attempts")
          counters["permanent_failed"] += 1
        else:
          store.record_sync_attempt(item.item_key, run_id, "retryable_failed", attempt, "bulk-item-null")
          counters["retryable_failed"] += 1
      continue

    # Non-200 on bulk call affects all items in the batch.
    for item in batch:
      attempt = store.get_attempt_count(item.item_key) + 1
      status = decision.status
      if status == "retryable_failed" and attempt < MAX_ATTEMPTS_PER_RUN:
        backoff_sleep(attempt)
      elif status == "retryable_failed" and attempt >= MAX_ATTEMPTS_PER_RUN:
        status = "permanent_failed"
      store.record_sync_attempt(item.item_key, run_id, status, attempt, decision.reason)
      counters[status] += 1

  store.checkpoint_if_terminal(settings.imap_folder)
  counters["total"] = sum(v for k, v in counters.items() if k != "total")
  return dict(counters)
