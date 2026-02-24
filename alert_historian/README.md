# alert_historian

`alert_historian` ingests Google Alerts, normalizes and deduplicates events, syncs links into FindFirst as bookmarks, and produces daily narrative reports.

## MVP v0.1

- Canonical payload schema for IMAP or JSON export ingestion
- SQLite-backed checkpoints and sync attempt tracking
- FindFirst sync client using existing auth, tag, and bookmark APIs
- Retry and classification policy for transient/permanent failures
- Daily markdown report output

## Quick start

```bash
cd alert_historian
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m alert_historian run-once
```

## Commands

```bash
python -m alert_historian ingest
python -m alert_historian sync
python -m alert_historian report
python -m alert_historian run-once
```

## Configuration

Copy `.env.example` to `.env` and set:

- `ALERT_HISTORIAN_INPUT_MODE=json|imap`
- `ALERT_HISTORIAN_JSON_INPUT` when using JSON mode
- `ALERT_HISTORIAN_FINDFIRST_BASE_URL`
- `ALERT_HISTORIAN_FINDFIRST_USERNAME`
- `ALERT_HISTORIAN_FINDFIRST_PASSWORD`

## Output locations

- Canonical artifacts: `./artifacts/canonical-<run_id>.json`
- State DB: `./state/alert_historian.db`
- Daily reports: `./reports/daily/YYYY-MM-DD.md`

## Smoke test against local FindFirst

1. Start FindFirst stack and ensure server is reachable.
2. Set `.env` credentials to the local test user.
3. Run:

```bash
python -m alert_historian run-once
```

If sync succeeds, bookmarks and tags appear in FindFirst, and report output is written to `reports/daily`.
