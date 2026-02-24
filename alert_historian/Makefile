.PHONY: install test unit integration smoke run-once

install:
	pip install -e ".[dev]"

test:
	pytest tests

unit:
	pytest tests/unit

integration:
	pytest tests/integration

run-once:
	python -m alert_historian run-once

smoke:
	python -m alert_historian run-once
