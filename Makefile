PY=python
POETRY?=poetry

.PHONY: init run seed export lint fmt typecheck test clean hooks-install hooks-run release release-patch release-minor release-major

init:
	$(POETRY) lock
	$(POETRY) install
	$(POETRY) run pre-commit install

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

hooks-install:
	$(POETRY) run pre-commit install

hooks-run:
	$(POETRY) run pre-commit run --all-files

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

release: release-patch

release-patch:
	./bin/bump_version.sh patch

release-minor:
	./bin/bump_version.sh minor

release-major:
	./bin/bump_version.sh major
