PY=python
POETRY?=poetry

.PHONY: run seed export lint fmt typecheck test clean

run:
	$(POETRY) run $(PY) -m srsbot.main

seed:
	$(POETRY) run $(PY) scripts/seed_cards.py data/seed_cards.json

export:
	$(PY) scripts/export_cards.py data/seed_cards.json

lint:
	$(POETRY) run ruff check .

fmt:
	$(POETRY) run black .

typecheck:
	$(POETRY) run mypy srsbot

test:
	$(POETRY) run pytest -q

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

