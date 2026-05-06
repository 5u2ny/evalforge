.PHONY: install install-dev run test typecheck clean

PY ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYTHON := $(VENV)/bin/python

$(VENV):
	$(PY) -m venv $(VENV)

install: $(VENV)
	$(PIP) install -r requirements.txt

install-dev: $(VENV)
	$(PIP) install -r requirements-dev.txt

run:
	$(VENV)/bin/streamlit run app.py

test:
	$(PYTHON) -m pytest tests/ -v

typecheck:
	$(PYTHON) -m py_compile app.py eval_engine.py scorers.py utils.py

clean:
	rm -rf __pycache__ .pytest_cache
	find . -name "__pycache__" -path "./tests/*" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
