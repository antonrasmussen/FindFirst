from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from alert_historian.ingestion.schema import CanonicalAlertItem


def normalize_whitespace(text: str) -> str:
  return " ".join((text or "").split())


def normalize_url(url: str) -> str:
  parsed = urlparse(url.strip())
  scheme = parsed.scheme.lower() or "https"
  host = (parsed.hostname or "").lower()
  path = parsed.path or "/"
  query_items = sorted(parse_qsl(parsed.query, keep_blank_values=True))
  query = urlencode(query_items)
  return urlunparse((scheme, host, path, "", query, ""))


def topic_slug(topic: str) -> str:
  return normalize_whitespace(topic).lower().replace("/", "-").replace(" ", "-")


def make_item_id(url_normalized: str, title: str, snippet: str) -> str:
  raw = f"{url_normalized}|{normalize_whitespace(title)}|{normalize_whitespace(snippet)}"
  return sha256(raw.encode("utf-8")).hexdigest()


def normalize_item(url: str, title: str, snippet: str) -> CanonicalAlertItem:
  normalized = normalize_url(url)
  domain = urlparse(normalized).hostname or ""
  return CanonicalAlertItem(
      item_id=make_item_id(normalized, title, snippet),
      url=url,
      url_normalized=normalized,
      title=normalize_whitespace(title) or normalized,
      snippet=normalize_whitespace(snippet),
      source_domain=domain,
  )
