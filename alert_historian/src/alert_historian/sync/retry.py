import random
import time
from dataclasses import dataclass


BACKOFF_SECONDS = [1, 4, 10, 30, 120]
MAX_ATTEMPTS_PER_RUN = 5


@dataclass
class RetryDecision:
  status: str
  retryable: bool
  reason: str | None = None


def classify_http_status(status_code: int, response_text: str = "") -> RetryDecision:
  msg = (response_text or "").lower()
  if status_code in (200, 201):
    return RetryDecision(status="synced", retryable=False)
  if status_code == 409 or "already exists" in msg:
    return RetryDecision(status="duplicate", retryable=False, reason="duplicate-url")
  if status_code in (401, 429) or 500 <= status_code <= 599:
    return RetryDecision(status="retryable_failed", retryable=True, reason=f"http-{status_code}")
  if 400 <= status_code <= 499:
    return RetryDecision(status="permanent_failed", retryable=False, reason=f"http-{status_code}")
  return RetryDecision(status="retryable_failed", retryable=True, reason=f"http-{status_code}")


def backoff_sleep(attempt_number: int) -> None:
  index = min(max(attempt_number - 1, 0), len(BACKOFF_SECONDS) - 1)
  base = BACKOFF_SECONDS[index]
  time.sleep(base + random.uniform(0, 0.25 * base))
