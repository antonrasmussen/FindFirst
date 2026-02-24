import json
from datetime import datetime
from pathlib import Path

from alert_historian.config.settings import Settings
from alert_historian.ingestion.imap_adapter import fetch_from_imap
from alert_historian.ingestion.json_export_adapter import load_json_export
from alert_historian.ingestion.schema import CanonicalAlertPayload
from alert_historian.state.store import StateStore


def _artifact_path(root: Path, run_id: str) -> Path:
  root.mkdir(parents=True, exist_ok=True)
  return root / f"canonical-{run_id}.json"


def ingest(settings: Settings, store: StateStore, run_id: str | None = None) -> tuple[str, int]:
  run = run_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
  if settings.input_mode.lower() == "imap":
    since_uid = store.get_checkpoint(settings.imap_folder)
    payloads = fetch_from_imap(settings, since_uid)
  else:
    payloads = load_json_export(settings.json_input)

  inserted = store.save_payloads(payloads)
  artifact = _artifact_path(settings.artifacts_dir, run)
  serializable = [p.model_dump(mode="json") for p in payloads]
  artifact.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
  return run, inserted


def load_canonical_from_artifact(path: Path) -> list[CanonicalAlertPayload]:
  data = json.loads(path.read_text(encoding="utf-8"))
  return [CanonicalAlertPayload.model_validate(item) for item in data]
