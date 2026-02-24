import imaplib
import re
from email import message_from_bytes
from email.message import Message

from alert_historian.config.settings import Settings
from alert_historian.ingestion.normalize import normalize_item
from alert_historian.ingestion.schema import CanonicalAlertPayload, RawRef


HREF_RE = re.compile(r'href=[\'"](?P<url>https?://[^\'"]+)[\'"]', re.IGNORECASE)


def _header(msg: Message, key: str) -> str:
  return str(msg.get(key, "")).strip()


def _extract_text_body(msg: Message) -> str:
  if msg.is_multipart():
    for part in msg.walk():
      content_type = part.get_content_type()
      if content_type in {"text/plain", "text/html"}:
        payload = part.get_payload(decode=True)
        if payload:
          return payload.decode(errors="ignore")
    return ""
  payload = msg.get_payload(decode=True)
  return payload.decode(errors="ignore") if payload else ""


def _extract_urls_and_items(body: str) -> list[tuple[str, str, str]]:
  urls = list(dict.fromkeys([m.group("url") for m in HREF_RE.finditer(body)]))
  items: list[tuple[str, str, str]] = []
  for url in urls:
    items.append((url, url, ""))
  return items


def _is_google_alert(msg: Message, settings: Settings) -> bool:
  sender = _header(msg, "From").lower()
  list_id = _header(msg, "List-ID").lower()
  return settings.alert_sender.lower() in sender or settings.alert_list_id.lower() in list_id


def fetch_from_imap(settings: Settings, since_uid: int) -> list[CanonicalAlertPayload]:
  results: list[CanonicalAlertPayload] = []
  with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
    client.login(settings.imap_username, settings.imap_password)
    client.select(settings.imap_folder)
    status, data = client.uid("search", None, f"UID {since_uid + 1}:*")
    if status != "OK":
      return results
    uid_list = data[0].decode().split() if data and data[0] else []
    for uid in uid_list:
      f_status, fetched = client.uid("fetch", uid, "(RFC822)")
      if f_status != "OK" or not fetched or not fetched[0]:
        continue
      raw = fetched[0][1]
      msg = message_from_bytes(raw)
      if not _is_google_alert(msg, settings):
        continue
      body = _extract_text_body(msg)
      item_tuples = _extract_urls_and_items(body)
      items = [normalize_item(url=u, title=t, snippet=s) for (u, t, s) in item_tuples]
      if not items:
        continue
      payload = CanonicalAlertPayload(
          source="google_alerts_imap",
          source_account=settings.imap_username,
          source_message_id=_header(msg, "Message-ID") or f"uid:{uid}",
          source_uid=f"{settings.imap_folder}:{uid}",
          alert_topic=_header(msg, "Subject") or "google-alert",
          alert_query_raw=_header(msg, "Subject"),
          items=items,
          raw_ref=RawRef(store="imap", folder=settings.imap_folder, uid=int(uid)),
      )
      results.append(payload)
  return results
