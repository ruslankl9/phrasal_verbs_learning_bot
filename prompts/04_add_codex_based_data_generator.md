**TASK: Switch seed format to CSV + add Codex-powered CSV generator utility (token-efficient, deduped)**

You previously built a Telegram SRS bot (Python 3.11). Implement the following changes:

## 0) Tech & Repo Constraints

* Python 3.11
* Keep existing structure (aiogram, SQLite, etc.) intact
* Use **UTF-8** everywhere
* Add/modify only the files listed below; keep code typed and documented
* Lint: ruff/black; Tests via pytest where applicable

---

## 1) Seed format: JSON → CSV (schema unchanged logically)

### CSV Spec

* File: `data/seed_cards.csv` (replaces `data/seed_cards.json`)
* **Header row is required**
* **Comma-separated**, `quotechar="\""`, escape embedded quotes by doubling `""`, newlines inside cells **not allowed**
* Arrays (`examples`, `tags`) are stored as **compact JSON strings** inside a single CSV cell (no whitespace)
* Booleans are literal `true`/`false` (lowercase)
* Columns (in this exact order):

  1. `phrasal` (string)
  2. `meaning_en` (string; concise)
  3. `examples` (JSON array of 2–3 strings, compact)
  4. `tags` (JSON array of strings, compact)
  5. `sense_uid` (string; unique per (phrasal+sense), e.g. `bring_up__mention`)
  6. `separable` (boolean: `true|false`)
  7. `intransitive` (boolean: `true|false`)

**Example (one line):**

```csv
phrasal,meaning_en,examples,tags,sense_uid,separable,intransitive
bring up,to mention a topic for discussion,["She brought up the budget issue at the meeting.","Don't bring it up now, please."],["work","meetings"],bring_up__mention,true,false
```

### Code changes

* **Replace JSON reads/writes** with CSV in these places:

  * `scripts/seed_cards.py`: import from `data/seed_cards.csv` into SQLite
  * `scripts/export_cards.py`: export current DB to `data/seed_cards.csv`
  * Any other script that referenced `seed_cards.json` must be updated to CSV
* Add robust parsing/validation:

  * Validate examples & tags are valid JSON arrays with the expected types
  * Validate booleans are `true|false`
  * Deduplicate by `(sense_uid)` on import
* Update **README.md** to document the CSV format & example

---

## 2) New utility: Codex-driven CSV generator (token-efficient, deduped)

### Purpose

Create `scripts/gen_phrasals_via_codex.py` that:

* Accepts CLI args:

  * `--tags TAG1,TAG2,...` (optional, comma-separated; filters/topic hints)
  * `--count N` (required; number of **new** rows to generate)
  * `--out PATH` (required; output CSV file to **create** afresh; include header)
  * `--known PATH` (required; path to a small text file containing a **comma-separated list** of already-present **phrasal verbs** and/or `sense_uid`s to avoid; see below)
* **Does not read the existing large CSV** (to save tokens)
* Builds a **compact prompt** for Codex using only:

  * The provided `tags` (if any)
  * The desired `N`
  * The content of the **known list file** (small CSV-safe, comma-separated string)
* Calls Codex (OpenAI API) and **expects CSV output only** with the exact columns above (including header)
* Writes a brand-new CSV file at `--out` with the returned rows (header + N rows)

### Known list file (token saver)

* Path given via `--known` (e.g., `data/known_phrasals.txt`)
* Content: **single line** of comma-separated identifiers to avoid; it may include:

  * plain phrasal forms (e.g., `bring up,get over,look into`)
  * known `sense_uid`s (e.g., `bring_up__mention,get_over__recover`)
* The utility **injects this exact string into the prompt** and asks Codex to avoid generating any row whose `phrasal` or `sense_uid` appears in this list (case-insensitive)
* This avoids sending the whole seed CSV, minimizing input tokens

### Prompt template used by the utility

Create a carefully phrased prompt (multi-line string) embedded in the script, e.g.:

```
SYSTEM / ROLE: You are a careful data generator for a language-learning app. 
TASK: Produce ONLY CSV (UTF-8) with a header row and exactly N rows of NEW English phrasal verbs, each row representing ONE DISTINCT SENSE of a phrasal verb.

CSV COLUMNS (in this exact order):
1) phrasal
2) meaning_en
3) examples (JSON array of 2–3 short B2-level English sentences, compact like ["Example 1","Example 2"])
4) tags (JSON array of topic tags, compact like ["work","travel"])
5) sense_uid (lowercase snake-ish, pattern: <phrasal_with_underscores>__<short_sense_slug>, e.g., bring_up__mention)
6) separable (true|false)
7) intransitive (true|false)

OUTPUT RULES:
- Output CSV ONLY. No explanations, no code fences, no extra lines.
- Use comma as separator, quote fields with double quotes when needed; escape inner quotes by doubling them.
- Keep arrays compact JSON (no spaces/newlines).
- Keep meaning_en concise and non-dictionary-like (plain learner-friendly).
- Examples must illustrate usage; include at least one example showing separable placement if separable=true.
- tags: include the provided topic tags where relevant; add 0–2 extra sensible tags max.
- Each row must be NEW: do NOT reuse any phrasal or sense_uid listed in KNOWN.
- Avoid rare/archaic phrasals; prefer common B2–C1 usage.

CONSTRAINTS:
- Generate EXACTLY {N} rows.
- If TAGS are provided: prefer senses relevant to those tags.
- KNOWN (case-insensitive, comma-separated): {KNOWN_LIST}
- Do NOT include any item in KNOWN either as phrasal or sense_uid.
- Language: English only in meaning and examples.

TAGS (optional hint): {TAGS_HINT}

CSV HEADER (repeat exactly):
phrasal,meaning_en,examples,tags,sense_uid,separable,intransitive
```

Where:

* `{N}` ← integer from `--count`
* `{KNOWN_LIST}` ← the raw string read from `--known` (or “(none)” if empty)
* `{TAGS_HINT}` ← a concise string (e.g., `["work","travel"]`) or “(none)”

### API integration

* Implement `gen_phrasals_via_codex.py` using the official OpenAI Python client (env var `OPENAI_API_KEY`). If you already have a helper, use it.
* Model: use your Codex/GP\* code model of choice; pass the prompt as a single message; set temperature modestly (e.g., 0.3–0.5)
* Validate the response:

  * Ensure header present and correct order of columns
  * Parse rows with `csv` module; ensure:

    * `phrasal` non-empty
    * `meaning_en` concise
    * `examples` parses as JSON array of 2–3 strings
    * `tags` parses as JSON array of strings
    * `sense_uid` unique within the batch and not in KNOWN (case-insensitive check)
    * `separable` and `intransitive` are `true|false`
* If validation fails, print a concise error and exit with non-zero status
* On success, write `--out` with header and rows

### CLI examples

* `python scripts/gen_phrasals_via_codex.py --tags work,meetings --count 40 --out data/new_work_pack.csv --known data/known_phrasals.txt`
* `python scripts/gen_phrasals_via_codex.py --count 50 --out data/new_mixed.csv --known data/known_phrasals.txt`

---

## 3) Update existing scripts to use CSV

### `scripts/seed_cards.py`

* Input: `data/seed_cards.csv`
* Parse rows; arrays from JSON strings; booleans from `true|false`
* Upsert into DB; enforce uniqueness by `sense_uid`
* CLI: `python scripts/seed_cards.py data/seed_cards.csv`

### `scripts/export_cards.py`

* Export from DB to CSV with the exact column order and rules
* CLI: `python scripts/export_cards.py data/export_cards.csv`

---

## 4) Add a helper to refresh the known list (optional but useful)

Add `scripts/build_known_list.py` that exports a **comma-separated** list to `data/known_phrasals.txt` combining:

* All `phrasal` values from DB
* All `sense_uid` values from DB
* De-duplicate, lowercase, join by comma onto **one line**
  CLI: `python scripts/build_known_list.py --out data/known_phrasals.txt`

---

## 5) Files to add/modify

* **Add**

  * `scripts/gen_phrasals_via_codex.py`  ← new generator utility
  * `scripts/build_known_list.py`         ← optional helper (described above)
  * `data/seed_cards.csv`                 ← replace JSON; include \~40 initial rows
* **Modify**

  * `scripts/seed_cards.py`               ← read CSV instead of JSON
  * `scripts/export_cards.py`             ← write CSV instead of JSON
  * `README.md`                           ← document CSV schema, generator usage, known list
  * `Makefile`                            ← add targets:

    * `make gen TAGS=work,travel N=40 OUT=data/new.csv`
      → runs `gen_phrasals_via_codex.py --tags $(TAGS) --count $(N) --out $(OUT) --known data/known_phrasals.txt`
    * `make known` → build/update known list
    * `make seed`  → import `data/seed_cards.csv`

---

## 6) Validation & Tests

* Add `tests/test_csv_schema.py`:

  * Validate parsing of `data/seed_cards.csv` (header, types, arrays, booleans)
  * Round-trip: export → parse → compare columns present
* Add `tests/test_known_list.py`:

  * Build known list, ensure it contains both `phrasal` and `sense_uid`, single line, comma-separated
* Add `tests/test_generator_prompt.py`:

  * Unit test the prompt template rendering (N, tags, known inject correctly; header present)

---

## 7) Acceptance Criteria

1. `data/seed_cards.csv` exists, follows the exact column order & encoding; seeding works; arrays are JSON strings; booleans `true|false`.
2. `scripts/seed_cards.py` imports CSV into DB with validation and `sense_uid` uniqueness; `scripts/export_cards.py` exports the same schema.
3. `scripts/gen_phrasals_via_codex.py` generates a **new CSV** (with header + N rows) **without reading any large CSV**; uses `--known` as a compact dedupe source; rejects rows that collide with known list; writes only the CSV.
4. The generator’s prompt instructs Codex to output **CSV only**, with correct header, compact arrays, and no extra text.
5. (Optional) `scripts/build_known_list.py` produces a single-line, comma-separated, lowercase known list combining `phrasal` and `sense_uid`.
6. README and Makefile updated; commands run as shown.

Please implement all code, prompts, and docs.
