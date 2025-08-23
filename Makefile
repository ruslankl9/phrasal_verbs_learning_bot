PY=python
POETRY?=poetry

.PHONY: run seed export lint fmt typecheck test

run:
	$(POETRY) run $(PY) -m srsbot.main

seed:
	$(PY) scripts/seed_cards.py data/seed_cards.json

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

