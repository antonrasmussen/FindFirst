"""Narrative Delta: links today's alerts to historical context."""

from collections import defaultdict
from typing import Callable

from alert_historian.state.store import PendingSyncItem


def generate_delta(
    today_items: list[PendingSyncItem],
    past_context: list[dict],
    chronicle_content: str,
    llm_client: Callable[[str, str | None], str],
    *,
    date_str: str | None = None,
) -> str:
  """
  Produce 1-2 sentence "story links" per topic, connecting today's alerts to historical context.
  Returns formatted markdown suitable for inclusion in the daily report.
  """
  from datetime import datetime

  if not today_items:
    return ""

  date_str = date_str or datetime.utcnow().date().isoformat()

  by_topic: dict[str, list[PendingSyncItem]] = defaultdict(list)
  for item in today_items:
    by_topic[item.topic].append(item)

  today_summary = []
  for topic, items in sorted(by_topic.items()):
    titles = [item.title for item in items[:5]]
    today_summary.append(f"**{topic}** ({len(items)} items): " + "; ".join(titles[:3]))

  past_summary = []
  for r in past_context[:15]:
    meta = r.get("metadata") or {}
    topic = meta.get("topic", "?")
    title = meta.get("title", "")
    day = meta.get("day", "")
    if title:
      past_summary.append(f"- [{day}] {topic}: {title}")

  system = """You write brief "story links" that connect today's Google Alert items to past context.
For each topic with new items today, write 1-2 sentences that:
- Link today's news to what we've seen before in the Chronicle
- Note continuations, shifts, or emerging patterns
- Be specific and concise
Output valid markdown. Use ## for topic headings and bullets for the story links."""

  user = f"""Today's date: {date_str}

Today's new items (by topic):
{"\n".join(today_summary)}

Relevant past items from the vector store:
{"\n".join(past_summary) if past_summary else "(none)"}

Chronicle excerpt:
---
{chronicle_content[:4000] if chronicle_content else "(empty)"}
---

Write the Narrative Delta section. For each topic with new items, provide a ## heading and 1-2 sentence story link(s)."""

  return llm_client(user, system)
