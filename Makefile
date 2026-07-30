# One documented way to do each thing.
# Everything runs against the repo's virtualenv without needing it activated.

PY := .venv/bin/python
RUFF := .venv/bin/ruff

.DEFAULT_GOAL := help
.PHONY: help test lint format check run docs docs-serve clean

help:  ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

test:  ## Run the test suite
	$(PY) -m pytest

lint:  ## Check style and import hygiene
	$(RUFF) check .

format:  ## Apply the safe lint fixes and format
	$(RUFF) check . --fix
	$(RUFF) format .

check: lint test  ## What CI should run: lint, then tests

run:  ## Start the web app on http://localhost:5000
	cd poggio_webapp && ../$(PY) app.py

docs:  ## Build the documentation site into site/
	.venv/bin/mkdocs build

docs-serve:  ## Serve the documentation with live reload
	.venv/bin/mkdocs serve

clean:  ## Remove caches and build output
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache site
