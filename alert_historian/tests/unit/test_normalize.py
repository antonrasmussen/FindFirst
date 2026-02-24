from alert_historian.ingestion.normalize import normalize_url, topic_slug


def test_normalize_url_orders_query_params() -> None:
  got = normalize_url("https://example.com/path?z=2&a=1")
  assert got == "https://example.com/path?a=1&z=2"


def test_topic_slug_basic() -> None:
  assert topic_slug("Vector Databases / Funding") == "vector-databases---funding"
