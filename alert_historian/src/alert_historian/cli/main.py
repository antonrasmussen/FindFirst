import argparse
from datetime import datetime

from alert_historian.config.settings import get_settings
from alert_historian.ingestion.pipeline import (
    load_canonical_from_artifact,
    payloads_to_pending_items,
)
from alert_historian.ingestion.pipeline import ingest
from alert_historian.narrative.chronicle import (
    create_openai_llm_client,
    load_chronicle,
    update_chronicle,
)
from alert_historian.narrative.delta import generate_delta
from alert_historian.narrative.vector_store import AlertVectorStore
from alert_historian.reporting.daily_report import build_daily_report
from alert_historian.state.store import StateStore
from alert_historian.sync.engine import sync_pending_items


def run_ingest() -> tuple[str, int]:
  settings = get_settings()
  store = StateStore(settings.state_db)
  try:
    run_id, inserted = ingest(settings, store)
    print(f"[ingest] run_id={run_id} inserted={inserted}")
    return run_id, inserted
  finally:
    store.close()


def run_sync(run_id: str | None = None) -> dict[str, int]:
  settings = get_settings()
  run = run_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
  store = StateStore(settings.state_db)
  try:
    stats = sync_pending_items(settings, store, run)
    print(f"[sync] run_id={run} stats={stats}")
    return stats
  finally:
    store.close()


def run_report(
    run_id: str,
    inserted_count: int,
    sync_stats: dict[str, int],
    narrative_delta: str | None = None,
) -> str:
  settings = get_settings()
  store = StateStore(settings.state_db)
  try:
    path = build_daily_report(
        store,
        settings.reports_dir,
        run_id,
        inserted_count,
        sync_stats,
        narrative_delta=narrative_delta,
    )
    print(f"[report] path={path}")
    return str(path)
  finally:
    store.close()


def _run_narrative_pipeline(
    settings,
    run_id: str,
    today_items: list,
) -> str:
  """Run Chronicle update and Narrative Delta generation. Returns delta markdown."""
  artifact_path = settings.artifacts_dir / f"canonical-{run_id}.json"
  if not artifact_path.exists():
    return ""

  vector_store = AlertVectorStore(
      persist_path=settings.chroma_path,
      api_key=settings.openai_api_key,
      embedding_model=settings.embedding_model,
  )
  vector_store.upsert_items(today_items)

  query_text = " ".join(
      f"{item.title} {item.snippet}" for item in today_items[:10]
  ).strip() or "recent alerts"
  past_context = vector_store.query(query_text, n_results=10)

  chronicle_path = settings.chronicle_path
  llm_client = create_openai_llm_client(
      api_key=settings.openai_api_key,
      model=settings.llm_model,
  )

  new_context = "\n\n".join(
      f"[{item.day}] {item.topic}: {item.title}\n{item.snippet[:200]}"
      for item in today_items[:15]
  )
  update_chronicle(chronicle_path, new_context, llm_client)
  chronicle_content = load_chronicle(chronicle_path)

  return generate_delta(
      today_items,
      past_context,
      chronicle_content,
      llm_client,
  )


def run_once(no_narrative: bool = False) -> int:
  run_id, inserted = run_ingest()
  stats = run_sync(run_id)

  narrative_delta: str | None = None
  if not no_narrative:
    settings = get_settings()
    if settings.openai_api_key:
      artifact_path = settings.artifacts_dir / f"canonical-{run_id}.json"
      if artifact_path.exists():
        payloads = load_canonical_from_artifact(artifact_path)
        today_items = payloads_to_pending_items(payloads)
        if today_items:
          try:
            narrative_delta = _run_narrative_pipeline(settings, run_id, today_items)
          except Exception as e:
            print(f"[narrative] skipped: {e}")

  run_report(run_id, inserted, stats, narrative_delta=narrative_delta)
  return 0


def main() -> int:
  parser = argparse.ArgumentParser(prog="alert_historian")
  sub = parser.add_subparsers(dest="command")
  sub.add_parser("ingest")
  sub.add_parser("sync")
  sub.add_parser("report")
  run_once_parser = sub.add_parser("run-once")
  run_once_parser.add_argument(
      "--no-narrative",
      action="store_true",
      help="Skip narrative engine (Chronicle, Delta) even when API key is set",
  )
  args = parser.parse_args()

  if args.command == "ingest":
    run_ingest()
    return 0
  if args.command == "sync":
    run_sync()
    return 0
  if args.command == "report":
    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    run_report(run_id, inserted_count=0, sync_stats={})
    return 0
  if args.command in ("run-once", None):
    no_narrative = getattr(args, "no_narrative", False)
    return run_once(no_narrative=no_narrative)
  return 0
