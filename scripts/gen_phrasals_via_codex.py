#!/usr/bin/env python3
from __future__ import annotations

"""
Generate CSV rows of phrasal verbs via Codex CLI.

This script builds a strict prompt and runs:
    codex exec "<prompt>"

The prompt instructs Codex to write the final CSV directly to --out (overwrite),
THEN self-check row count, and ONLY print "OK" to stdout on success.

Usage:
  python scripts/gen_phrasals_via_codex.py \
    --tags work,travel \
    --count 40 \
    --out data/new.csv \
    --known data/known_phrasals.txt \
    --debug
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Set

EXPECTED_HEADER = [
    "phrasal",
    "meaning_en",
    "examples",
    "tags",
    "sense_uid",
    "separable",
    "intransitive",
]


def _read_known(path: Path) -> tuple[str, Set[str]]:
    raw = path.read_text(encoding="utf-8").strip() if path.exists() else ""
    known_set = {x.strip().lower() for x in raw.split(",") if x.strip()}
    return raw, known_set


def build_codex_prompt(n: int, tags: list[str] | None, known_raw: str, out_path: Path, io_mode: str) -> str:
    """
    Build a single-shot prompt for Codex CLI. It must:
    - write the final CSV (with header + exactly n rows) to out_path
    - verify row count before replying
    - print only 'OK' to stdout
    """
    tags_hint = json.dumps([t.strip() for t in tags if t.strip()], ensure_ascii=False) if tags else "(none)"
    known_list = known_raw if known_raw.strip() else "(none)"
    header_line = ",".join(EXPECTED_HEADER)

    # Максимально чёткие инструкции, чтобы не печатал CSV в stdout и не добавлял мусор
    if io_mode == "codex_write":
        target_hint = f"CREATE/OVERWRITE this relative path (inside current working directory): {out_path.as_posix()}"
        output_rules = f"""
OUTPUT RULES:
- Apply a file edit/patch so that the target file exactly contains the final CSV (overwrite if exists).
- Do NOT print the CSV to stdout.
- After writing, SELF-CHECK header and EXACTLY {n} data rows.
- When correct, print exactly: OK
"""
    else:
        target_hint = "Do NOT write any files."
        output_rules = f"""
OUTPUT RULES:
- Print ONLY the final CSV between the exact markers below.
- No explanations, no chatter, no code fences.
- Start with a line: <<<CSV
- Then the CSV content (header + EXACTLY {n} data rows).
- End with a line: CSV;
"""

    return f"""
You are operating inside a CLI where your stdout is parsed by an automated validator.
{target_hint}

CSV REQUIREMENTS:
- The CSV MUST start with this exact header line:
{header_line}
- Then EXACTLY {n} data rows (no more, no fewer).
- Columns:
  1) phrasal
  2) meaning_en (concise, learner-friendly)
  3) examples (JSON array of exactly 2 short B2-level sentences, compact like ["Example 1","Example 2"])
  4) tags (JSON array, compact like ["work","travel"])
  5) sense_uid (lowercase snake-ish: <phrasal_with_underscores>__<short_sense_slug>, e.g., bring_up__mention)
  6) separable (true|false)
  7) intransitive (true|false)

CONTENT RULES:
- English only for meaning/examples.
- Examples must illustrate usage; include at least one separable-placement example if separable=true.
- Prefer common B2–C1 phrasals; avoid rare/archaic.
- If TAGS provided: prefer senses relevant to those tags; you may add up to 2 extra sensible tags.
- NEW items only: do NOT use any phrasal or sense_uid listed in KNOWN (case-insensitive).

KNOWN (comma-separated, case-insensitive):
{known_list}

TAGS (optional hint):
{tags_hint}

{output_rules}
""".strip()


def _parse_csv_strict(csv_text: str, known_set: Set[str]) -> Tuple[List[str], List[List[str]]]:
    """
    Return (header_row, rows). Validate structure and values.
    Raise SystemExit on validation errors.
    """
    lines = [ln for ln in csv_text.splitlines() if ln.strip() != ""]
    reader = csv.reader(lines)
    try:
        header = next(reader)
    except StopIteration:
        raise SystemExit("Empty CSV file")

    if header != EXPECTED_HEADER:
        raise SystemExit(f"Invalid header. Expected {EXPECTED_HEADER}, got {header}")

    seen_sense: set[str] = set()
    rows: list[list[str]] = []
    for i, row in enumerate(reader, start=2):
        if len(row) != 7:
            raise SystemExit(f"Row {i}: expected 7 columns, got {len(row)}")
        phrasal, meaning_en, examples, tags, sense_uid, separable, intransitive = row
        if not phrasal.strip():
            raise SystemExit(f"Row {i}: empty phrasal")
        if not meaning_en.strip():
            raise SystemExit(f"Row {i}: empty meaning_en")
        # arrays
        try:
            ex = json.loads(examples)
            if not (isinstance(ex, list) and len(ex) == 2 and all(isinstance(x, str) for x in ex)):
                raise ValueError
        except Exception:
            raise SystemExit(f"Row {i}: invalid examples array (needs exactly 2 strings)")
        try:
            tg = json.loads(tags)
            if not (isinstance(tg, list) and all(isinstance(x, str) for x in tg)):
                raise ValueError
        except Exception:
            raise SystemExit(f"Row {i}: invalid tags array")
        su = sense_uid.strip().lower()
        if not su:
            raise SystemExit(f"Row {i}: empty sense_uid")
        if su in seen_sense or su in known_set or phrasal.strip().lower() in known_set:
            raise SystemExit(f"Row {i}: duplicate or KNOWN item: {su}")
        seen_sense.add(su)
        if separable.strip().lower() not in {"true", "false"}:
            raise SystemExit(f"Row {i}: separable must be true|false")
        if intransitive.strip().lower() not in {"true", "false"}:
            raise SystemExit(f"Row {i}: intransitive must be true|false")
        rows.append(row)
    return EXPECTED_HEADER, rows


def run_codex_exec(prompt: str, codex_bin: str, debug: bool, timeout: int) -> tuple[int, str, str]:
    """
    Run codex exec "<prompt>" with optional realtime debug output.
    Returns (returncode, stdout, stderr) where stdout/stderr are full collected strings.
    """
    proc = subprocess.Popen(
        [codex_bin, "exec", "--full-auto", prompt],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # line-buffered
    )

    stdout_buf = []
    stderr_buf = []

    try:
        import threading

        def reader(stream, buf, is_err: bool):
            for line in iter(stream.readline, ''):
                buf.append(line)
                if debug:
                    if is_err:
                        print(line, end='', file=sys.stderr, flush=True)
                    else:
                        print(line, end='', flush=True)
            stream.close()

        threads = [
            threading.Thread(target=reader, args=(proc.stdout, stdout_buf, False)),
            threading.Thread(target=reader, args=(proc.stderr, stderr_buf, True)),
        ]
        for t in threads:
            t.daemon = True
            t.start()

        rc = proc.wait(timeout if timeout > 0 else None)
        for t in threads:
            t.join()
    except Exception:
        proc.kill()
        raise

    return rc, ''.join(stdout_buf).strip(), ''.join(stderr_buf).strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tags", type=str, default="", help="Comma-separated tags (optional)")
    p.add_argument("--count", type=int, required=True, help="Number of rows to generate (N)")
    p.add_argument("--out", type=Path, required=True, help="Output CSV path (will be overwritten)")
    p.add_argument("--known", type=Path, required=True, help="Known list file (comma-separated, one line)")
    p.add_argument("--codex-bin", type=str, default="codex", help="Codex CLI binary name or path")
    p.add_argument("--timeout", type=int, default=600, help="Subprocess timeout in seconds (0 = no timeout)")
    p.add_argument("--debug", action="store_true", help="Print raw Codex stdout/stderr")
    p.add_argument("--io-mode", choices=["stdout","codex_write"], default="stdout",
                   help="stdout: Codex prints CSV between markers; codex_write: Codex writes the file itself")
    args = p.parse_args()

    known_raw, known_set = _read_known(args.known)
    tags_list = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    # Формируем промпт
    # Сделаем путь относительным к CWD, чтобы он точно лежал в рабочей папке Codex
    rel_out = Path(args.out).resolve().relative_to(Path.cwd())
    prompt = build_codex_prompt(args.count, tags_list or None, known_raw, rel_out, args.io_mode)

    # Запускаем Codex CLI
    rc, out, err = run_codex_exec(prompt, args.codex_bin, args.debug, args.timeout)
    if rc != 0:
        print("Codex CLI returned non-zero exit code.", file=sys.stderr)
        if err:
            print(err, file=sys.stderr)
        sys.exit(rc)

    csv_text: str | None = None
    if args.io_mode == "stdout":
        # Ищем блок между <<<CSV ... CSV;
        lines = out.splitlines()
        try:
            start = lines.index("<<<CSV") + 1
            end = lines.index("CSV;", start)
            csv_text = "\n".join(lines[start:end]).strip()
        except ValueError:
            print("Did not find CSV markers in stdout.", file=sys.stderr)
            if out:
                print(f"STDOUT (truncated):\n{out[:2000]}", file=sys.stderr)
            if err:
                print(f"STDERR:\n{err}", file=sys.stderr)
            sys.exit(2)
        # Пишем файл сами
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(csv_text, encoding="utf-8")
    else:
        # Ожидаем ровно 'OK' в режиме записи самим Codex
        if out.strip() != "OK":
            print("Unexpected Codex CLI output (expected 'OK').", file=sys.stderr)
            if out:
                print(f"STDOUT:\n{out}", file=sys.stderr)
            if err:
                print(f"STDERR:\n{err}", file=sys.stderr)
            # всё равно проверим файл ниже

    # Читаем и валидируем готовый файл
    if not args.out.exists():
        print(f"Output file not found: {args.out}", file=sys.stderr)
        sys.exit(1)

    if csv_text is None:
        csv_text = args.out.read_text(encoding="utf-8")
    header, rows = _parse_csv_strict(csv_text, known_set)

    # Дополнительная проверка: ровно N строк
    if len(rows) != args.count:
        raise SystemExit(f"Row count mismatch: expected {args.count}, got {len(rows)}")

    print(f"OK: wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
