import argparse
from datetime import datetime

from alert_historian.config.settings import get_settings
from alert_historian.ingestion.pipeline import ingest
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


def run_report(run_id: str, inserted_count: int, sync_stats: dict[str, int]) -> str:
  settings = get_settings()
  store = StateStore(settings.state_db)
  try:
    path = build_daily_report(store, settings.reports_dir, run_id, inserted_count, sync_stats)
    print(f"[report] path={path}")
    return str(path)
  finally:
    store.close()


def run_once() -> int:
  run_id, inserted = run_ingest()
  stats = run_sync(run_id)
  run_report(run_id, inserted, stats)
  return 0


def main() -> int:
  parser = argparse.ArgumentParser(prog="alert_historian")
  sub = parser.add_subparsers(dest="command")
  sub.add_parser("ingest")
  sub.add_parser("sync")
  sub.add_parser("report")
  sub.add_parser("run-once")
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
    return run_once()
  return 0
