# One documented way to do each thing.
# Everything runs against the repo's virtualenv without needing it activated.

PY := .venv/bin/python
RUFF := .venv/bin/ruff
MKDOCS := .venv/bin/mkdocs

# The JavaScript suite is addressed by glob, never by directory. `node --test`
# on a directory collects every .js file it finds, including the browser-only
# glue that imports three from an import map Node cannot read -- which fails
# with ERR_MODULE_NOT_FOUND and looks like a broken install. This glob is the
# same one CI uses; static/module-layering.test.mjs keeps the split honest.
JS_TESTS := "poggio_webapp/static/**/*.test.mjs" "docs/javascripts/**/*.test.mjs"

.DEFAULT_GOAL := help
.PHONY: help test test-js lint format check check-docs diagrams run docs docs-serve clean demo demo-run demo-list

help:  ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

test:  ## Run the Python test suite
	$(PY) -m pytest

test-js:  ## Run the JavaScript test suite
	node --test $(JS_TESTS)

lint:  ## Check style and import hygiene
	$(RUFF) check .

format:  ## Apply the safe lint fixes and format
	$(RUFF) check . --fix
	$(RUFF) format .

check-docs:  ## Run the four documentation checkers and build the site strictly
	$(PY) tools/docs/check_docs.py .
	$(PY) tools/docs/check_coverage.py .
	$(PY) tools/docs/validate_visual_manifest.py .
	$(PY) tools/docs/check_readme_sync.py .
	$(MKDOCS) build --strict

diagrams:  ## Regenerate the diagrams and fail if the committed files are stale
	$(PY) tools/docs/generate_diagrams.py .
	@git diff --quiet -- docs/assets/diagrams || { \
		echo "Generated diagrams differ from the committed files."; \
		git diff --stat -- docs/assets/diagrams; \
		exit 1; \
	}

check: lint check-docs test test-js diagrams  ## Everything CI runs, in CI's order

run:  ## Start the web app on http://localhost:5000
	cd poggio_webapp && ../$(PY) app.py

# The demo writes into poggio_webapp/{jobs,trenches,matrices}, the same three
# gitignored roots the application uses for your own work. Reseeding removes
# the previous run's trenches and leaves everything else alone.
#
# PYTHONPATH rather than `cd poggio_webapp` as `run` does: the storage roots
# resolve from storage.py's own location either way, and staying at the repo
# root keeps the venv's sys.prefix consistent. `cd` there makes Python warn
# about the ../ in its own prefix on every line of output, which is noise in a
# command whose whole job is to be read.
demo:  ## Seed both demonstration trenches (T905 refuses, T906 builds)
	PYTHONPATH=poggio_webapp $(PY) -m demo.seed stops
	PYTHONPATH=poggio_webapp $(PY) -m demo.seed complete

demo-run:  ## Build both demonstration trenches and report where each lands
	PYTHONPATH=poggio_webapp $(PY) -m demo.run T905
	PYTHONPATH=poggio_webapp $(PY) -m demo.run T906

demo-list:  ## List the record sets the demo can be run against
	PYTHONPATH=poggio_webapp $(PY) -m demo.seed --list

docs:  ## Build the documentation site into site/
	.venv/bin/mkdocs build

docs-serve:  ## Serve the documentation with live reload
	.venv/bin/mkdocs serve

clean:  ## Remove caches and build output
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache site
