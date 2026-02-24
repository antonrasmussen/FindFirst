from alert_historian.ingestion.normalize import topic_slug
from alert_historian.state.store import PendingSyncItem


def tag_titles_for_item(item: PendingSyncItem, use_domain_tags: bool = True) -> list[str]:
  titles = [
      "source/google-alerts",
      f"topic/{topic_slug(item.topic)}",
      f"timeline/{item.day}",
  ]
  if use_domain_tags and item.source_domain:
    titles.append(f"domain/{item.source_domain}")
  return titles


def to_add_bkmk_req(item: PendingSyncItem, tag_ids: list[int]) -> dict[str, object]:
  title = item.title.strip() or item.url
  return {
      "title": title,
      "url": item.url,
      "tagIds": tag_ids,
      "scrapable": True,
  }
