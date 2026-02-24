from alert_historian.state.store import PendingSyncItem, make_item_key, make_message_key
from alert_historian.sync.mappers import tag_titles_for_item, to_add_bkmk_req


def sample_item() -> PendingSyncItem:
  return PendingSyncItem(
      item_key="k1",
      message_key="m1",
      topic="vector databases",
      day="2026-02-24",
      url="https://example.com/story",
      url_normalized="https://example.com/story",
      title="A title",
      snippet="A snippet",
      source_domain="example.com",
      source_message_id="<id>",
  )


def test_message_key_stable() -> None:
  assert make_message_key("u", "m") == make_message_key("u", "m")


def test_item_key_changes_on_topic() -> None:
  k1 = make_item_key("https://example.com", "alpha")
  k2 = make_item_key("https://example.com", "beta")
  assert k1 != k2


def test_mapper_builds_payload() -> None:
  payload = to_add_bkmk_req(sample_item(), [1, 2])
  assert payload["url"] == "https://example.com/story"
  assert payload["tagIds"] == [1, 2]


def test_tag_titles_include_source_topic_timeline_and_domain() -> None:
  titles = tag_titles_for_item(sample_item(), use_domain_tags=True)
  assert "source/google-alerts" in titles
  assert any(t.startswith("topic/") for t in titles)
  assert "timeline/2026-02-24" in titles
  assert "domain/example.com" in titles
