# MVP Contract v0.1

This document defines the integration contract between `alert_historian` and FindFirst for the initial implementation.

## Canonical payload

Each ingested alert is normalized to a versioned payload.

```json
{
  "schema_version": "0.1",
  "source": "google_alerts_imap",
  "source_account": "me@example.com",
  "source_message_id": "<msg-id>",
  "source_uid": "INBOX:42",
  "received_at": "2026-02-24T16:00:00Z",
  "alert_topic": "vector databases",
  "alert_query_raw": "\"vector databases\" funding",
  "items": [
    {
      "item_id": "sha256(url_normalized|title|snippet)",
      "url": "https://example.com/news",
      "url_normalized": "https://example.com/news",
      "title": "News title",
      "snippet": "Snippet text",
      "published_at": null,
      "source_domain": "example.com"
    }
  ],
  "raw_ref": {
    "store": "imap",
    "folder": "INBOX",
    "uid": 42
  }
}
```

## Dedup keys

- Message key: `sha256(source_account|source_message_id)`
- Item key: `sha256(url_normalized|topic_slug)`

Message key prevents replay of the same source message.
Item key enforces topic-aware URL dedup before remote sync.

## FindFirst sync mapping

Each canonical item maps to `AddBkmkReq`:

```json
{
  "title": "News title",
  "url": "https://example.com/news",
  "tagIds": [1, 2, 3],
  "scrapable": true
}
```

Tag strategy:
- `source/google-alerts`
- `topic/<slug>`
- `timeline/YYYY-MM-DD`
- `domain/<host>` (optional)

## Failure matrix

| Condition | Classification | Retry |
|---|---|---|
| 200/201 | `synced` | no |
| 409 or duplicate message | `duplicate` | no |
| 401, 429, 5xx | `retryable_failed` | yes |
| other 4xx | `permanent_failed` | no |
| retryable beyond max attempts | `permanent_failed` | no |

Backoff schedule per attempt: `1s, 4s, 10s, 30s, 120s` with jitter.

## Checkpoint semantics

- Checkpoint source is mailbox + max observed UID.
- Checkpoint advances only when every tracked item is in a terminal state:
  - `synced`, `duplicate`, `permanent_failed`.
- If any item is non-terminal (`retryable_failed` or no attempt), checkpoint remains unchanged.
