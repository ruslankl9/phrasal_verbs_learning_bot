PY=python
POETRY?=poetry

.PHONY: run seed export lint fmt typecheck test clean


run:
	$(POETRY) run $(PY) -m srsbot.main

seed:
	$(POETRY) run $(PY) scripts/seed_cards.py data/seed_cards.csv

export:
	$(PY) scripts/export_cards.py data/export_cards.csv

known:
	$(POETRY) run $(PY) scripts/build_known_list.py --out data/known_phrasals.txt

gen:
	$(POETRY) run $(PY) scripts/gen_phrasals_via_codex.py --tags $(TAGS) --count $(N) --out $(OUT) --known data/known_phrasals.txt

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
