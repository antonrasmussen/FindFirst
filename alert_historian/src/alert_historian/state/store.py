import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from alert_historian.ingestion.normalize import topic_slug
from alert_historian.ingestion.schema import CanonicalAlertPayload


TERMINAL_STATUSES = {"synced", "duplicate", "permanent_failed"}


@dataclass
class PendingSyncItem:
  item_key: str
  message_key: str
  topic: str
  day: str
  url: str
  url_normalized: str
  title: str
  snippet: str
  source_domain: str
  source_message_id: str


def make_message_key(source_account: str, source_message_id: str) -> str:
  return sha256(f"{source_account}|{source_message_id}".encode("utf-8")).hexdigest()


def make_item_key(url_normalized: str, topic: str) -> str:
  return sha256(f"{url_normalized}|{topic_slug(topic)}".encode("utf-8")).hexdigest()


class StateStore:
  def __init__(self, db_path: Path):
    self.db_path = db_path
    self.db_path.parent.mkdir(parents=True, exist_ok=True)
    self.conn = sqlite3.connect(str(self.db_path))
    self.conn.row_factory = sqlite3.Row
    self._init_schema()

  def close(self) -> None:
    self.conn.close()

  def _init_schema(self) -> None:
    cur = self.conn.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS sync_checkpoint (
        mailbox TEXT PRIMARY KEY,
        last_uid INTEGER NOT NULL,
        updated_at TEXT NOT NULL
      )
    """)
    cur.execute("""
      CREATE TABLE IF NOT EXISTS seen_messages (
        msg_key TEXT PRIMARY KEY,
        source_message_id TEXT NOT NULL,
        source_account TEXT NOT NULL,
        received_at TEXT NOT NULL,
        max_uid INTEGER
      )
    """)
    cur.execute("""
      CREATE TABLE IF NOT EXISTS items (
        item_key TEXT PRIMARY KEY,
        message_key TEXT NOT NULL,
        topic TEXT NOT NULL,
        day TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL
      )
    """)
    cur.execute("""
      CREATE TABLE IF NOT EXISTS sync_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_key TEXT NOT NULL,
        run_id TEXT NOT NULL,
        status TEXT NOT NULL,
        attempts INTEGER NOT NULL,
        last_error TEXT,
        findfirst_bookmark_id INTEGER,
        updated_at TEXT NOT NULL
      )
    """)
    self.conn.commit()

  def get_checkpoint(self, mailbox: str) -> int:
    cur = self.conn.execute("SELECT last_uid FROM sync_checkpoint WHERE mailbox = ?", (mailbox,))
    row = cur.fetchone()
    return int(row["last_uid"]) if row else 0

  def set_checkpoint(self, mailbox: str, last_uid: int) -> None:
    now = datetime.utcnow().isoformat()
    self.conn.execute(
        """
        INSERT INTO sync_checkpoint(mailbox, last_uid, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(mailbox) DO UPDATE SET last_uid=excluded.last_uid, updated_at=excluded.updated_at
        """,
        (mailbox, last_uid, now))
    self.conn.commit()

  def is_message_seen(self, msg_key: str) -> bool:
    cur = self.conn.execute("SELECT 1 FROM seen_messages WHERE msg_key = ?", (msg_key,))
    return cur.fetchone() is not None

  def record_message(self, msg_key: str, source_message_id: str, source_account: str, max_uid: int | None) -> None:
    self.conn.execute(
        """
        INSERT OR IGNORE INTO seen_messages(msg_key, source_message_id, source_account, received_at, max_uid)
        VALUES (?, ?, ?, ?, ?)
        """,
        (msg_key, source_message_id, source_account, datetime.utcnow().isoformat(), max_uid))
    self.conn.commit()

  def save_payloads(self, payloads: Iterable[CanonicalAlertPayload]) -> int:
    created = 0
    for payload in payloads:
      msg_key = make_message_key(payload.source_account, payload.source_message_id)
      if self.is_message_seen(msg_key):
        continue
      max_uid = payload.raw_ref.uid if payload.raw_ref.uid is not None else None
      self.record_message(msg_key, payload.source_message_id, payload.source_account, max_uid)
      for item in payload.items:
        item_key = make_item_key(item.url_normalized, payload.alert_topic)
        now = datetime.utcnow().isoformat()
        day = payload.received_at.date().isoformat()
        payload_json = json.dumps({
            "topic": payload.alert_topic,
            "source_message_id": payload.source_message_id,
            "url": item.url,
            "url_normalized": item.url_normalized,
            "title": item.title,
            "snippet": item.snippet,
            "source_domain": item.source_domain,
            "day": day,
        })
        cur = self.conn.execute(
            """
            INSERT OR IGNORE INTO items(item_key, message_key, topic, day, payload_json, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (item_key, msg_key, payload.alert_topic, day, payload_json, now, now))
        if cur.rowcount:
          created += 1
        else:
          self.conn.execute("UPDATE items SET last_seen_at=? WHERE item_key=?", (now, item_key))
      self.conn.commit()
    return created

  def get_pending_items(self, run_id: str) -> list[PendingSyncItem]:
    cur = self.conn.execute("""
      SELECT i.item_key, i.message_key, i.topic, i.day, i.payload_json
      FROM items i
      LEFT JOIN (
        SELECT item_key, status
        FROM sync_attempts
        WHERE id IN (SELECT MAX(id) FROM sync_attempts GROUP BY item_key)
      ) sa ON sa.item_key = i.item_key
      WHERE sa.status IS NULL OR sa.status NOT IN ('synced', 'duplicate', 'permanent_failed')
      ORDER BY i.first_seen_at ASC
    """)
    items: list[PendingSyncItem] = []
    for row in cur.fetchall():
      payload = json.loads(row["payload_json"])
      items.append(PendingSyncItem(
          item_key=row["item_key"],
          message_key=row["message_key"],
          topic=row["topic"],
          day=row["day"],
          url=payload["url"],
          url_normalized=payload["url_normalized"],
          title=payload["title"],
          snippet=payload["snippet"],
          source_domain=payload["source_domain"],
          source_message_id=payload["source_message_id"],
      ))
    return items

  def record_sync_attempt(self, item_key: str, run_id: str, status: str, attempts: int, last_error: str | None = None,
      bookmark_id: int | None = None) -> None:
    self.conn.execute(
        """
        INSERT INTO sync_attempts(item_key, run_id, status, attempts, last_error, findfirst_bookmark_id, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (item_key, run_id, status, attempts, last_error, bookmark_id, datetime.utcnow().isoformat()))
    self.conn.commit()

  def get_attempt_count(self, item_key: str) -> int:
    cur = self.conn.execute("SELECT MAX(attempts) as attempts FROM sync_attempts WHERE item_key = ?", (item_key,))
    row = cur.fetchone()
    return int(row["attempts"]) if row and row["attempts"] is not None else 0

  def checkpoint_if_terminal(self, mailbox: str) -> bool:
    cur = self.conn.execute("""
      SELECT COUNT(*) AS pending_cnt
      FROM items i
      LEFT JOIN (
        SELECT item_key, status
        FROM sync_attempts
        WHERE id IN (SELECT MAX(id) FROM sync_attempts GROUP BY item_key)
      ) sa ON sa.item_key = i.item_key
      WHERE sa.status IS NULL OR sa.status NOT IN ('synced', 'duplicate', 'permanent_failed')
    """)
    if int(cur.fetchone()["pending_cnt"]) > 0:
      return False
    cur = self.conn.execute("SELECT COALESCE(MAX(max_uid), 0) as max_uid FROM seen_messages")
    max_uid = int(cur.fetchone()["max_uid"])
    self.set_checkpoint(mailbox, max_uid)
    return True

  def run_stats(self, run_id: str) -> dict[str, int]:
    cur = self.conn.execute("""
      SELECT status, COUNT(*) AS cnt
      FROM sync_attempts
      WHERE run_id = ?
      GROUP BY status
    """, (run_id,))
    stats = {row["status"]: int(row["cnt"]) for row in cur.fetchall()}
    total = sum(stats.values())
    stats["total"] = total
    return stats

  def topic_links(self) -> dict[str, list[str]]:
    cur = self.conn.execute("SELECT topic, payload_json FROM items ORDER BY first_seen_at ASC")
    out: dict[str, list[str]] = {}
    for row in cur.fetchall():
      payload = json.loads(row["payload_json"])
      topic = row["topic"]
      if topic not in out:
        out[topic] = []
      out[topic].append(payload["url"])
    return out
