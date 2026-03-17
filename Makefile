.PHONY: help weather history ski alert install test lint
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "  weather-finder — available commands"
	@echo ""
	@echo "  make weather    → current weather dashboard (Streamlit)"
	@echo "  make history    → historical analysis dashboard (Streamlit)"
	@echo "  make ski        → ski season dashboard (Streamlit)"
	@echo "  make alert      → run weather alert CLI (run-once)"
	@echo "  make install    → install package with all extras"
	@echo "  make test       → run test suite"
	@echo "  make lint       → run ruff linter"
	@echo ""

weather:
	.venv/bin/streamlit run app/app.py

history:
	.venv/bin/streamlit run app/history.py

ski:
	.venv/bin/streamlit run app/ski.py

alert:
	.venv/bin/weather-alert run-once

install:
	.venv/bin/pip install -e ".[ui,dev]"

test:
	.venv/bin/pytest tests/ -q

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .
