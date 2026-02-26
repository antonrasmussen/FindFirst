from datetime import datetime
from pathlib import Path

from alert_historian.state.store import StateStore


def build_daily_report(
    store: StateStore,
    report_dir: Path,
    run_id: str,
    inserted_count: int,
    sync_stats: dict[str, int],
    narrative_delta: str | None = None,
) -> Path:
  report_dir.mkdir(parents=True, exist_ok=True)
  today = datetime.utcnow().date().isoformat()
  out_path = report_dir / f"{today}.md"

  by_topic = store.topic_links()

  lines = [
      f"# Alert Historian Daily Report ({today})",
      "",
      "## Ingest Summary",
      f"- Canonical items inserted: {inserted_count}",
      "",
      "## Sync Summary",
  ]
  for key in ["synced", "duplicate", "retryable_failed", "permanent_failed", "total"]:
    lines.append(f"- {key}: {sync_stats.get(key, 0)}")

  if narrative_delta and narrative_delta.strip():
    lines.extend(["", "## Narrative Delta", "", narrative_delta.strip(), ""])

  lines.extend(["", "## Topic Timeline"])
  if by_topic:
    for topic, links in sorted(by_topic.items()):
      lines.append(f"- {topic}")
      for link in links[:10]:
        lines.append(f"  - {link}")
  else:
    lines.append("- No pending timeline links; all current items are terminal.")

  out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
  return out_path
