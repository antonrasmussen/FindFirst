from alert_historian.sync.retry import classify_http_status


def test_retry_classification_for_5xx() -> None:
  decision = classify_http_status(503)
  assert decision.status == "retryable_failed"
  assert decision.retryable is True


def test_duplicate_classification_409() -> None:
  decision = classify_http_status(409)
  assert decision.status == "duplicate"
  assert decision.retryable is False


def test_permanent_400() -> None:
  decision = classify_http_status(400)
  assert decision.status == "permanent_failed"
  assert decision.retryable is False
