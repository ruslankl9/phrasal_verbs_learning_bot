#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dedupe_phrasals.py

Удаляет дубликаты из CSV по sense_uid, сортирует по phrasal,
и фиксирует конфликты (одинаковый phrasal с разными sense_uid).

Usage:
  python dedupe_phrasals.py input.csv output_clean.csv --conflicts conflicts.csv
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

def read_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames or []
    return header, rows

def write_rows(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def normalize_key(s):
    return (s or "").casefold().strip()

def main():
    ap = argparse.ArgumentParser(description="Dedupe by sense_uid, sort by phrasal, report multi-sense conflicts.")
    ap.add_argument("input", help="Входной CSV (с колонками минимум: phrasal, sense_uid)")
    ap.add_argument("output", help="Выходной CSV без дубликатов и отсортированный")
    ap.add_argument("--conflicts", default="phrasal_conflicts.csv",
                    help="CSV для конфликтов (одинаковый phrasal с разными sense_uid). По умолчанию phrasal_conflicts.csv")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    conf_path = Path(args.conflicts)

    if not in_path.exists():
        print(f"[ERR] Не найден входной файл: {in_path}", file=sys.stderr)
        sys.exit(1)

    header, rows = read_rows(in_path)
    if not header:
        print("[ERR] Пустой или некорректный CSV (нет заголовка).", file=sys.stderr)
        sys.exit(1)

    # Проверим наличие ключевых колонок
    required_cols = {"phrasal", "sense_uid"}
    missing = [c for c in required_cols if c not in header]
    if missing:
        print(f"[ERR] В CSV отсутствуют обязательные колонки: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # 1) Сбор конфликтов: один phrasal -> несколько sense_uid
    phrasal_to_senses = defaultdict(set)
    phrasal_to_rows = defaultdict(list)
    for r in rows:
        ph = normalize_key(r.get("phrasal"))
        su = r.get("sense_uid", "")
        if ph:
            if su:
                phrasal_to_senses[ph].add(su)
            phrasal_to_rows[ph].append(r)

    # Список конфликтов
    conflicts = []
    for ph_norm, sense_set in phrasal_to_senses.items():
        if len(sense_set) > 1:
            # Добавим все строки по этому phrasal для удобства ревью
            for r in phrasal_to_rows[ph_norm]:
                conflicts.append({
                    "phrasal": r.get("phrasal", ""),
                    "sense_uid": r.get("sense_uid", ""),
                    "meaning_en": r.get("meaning_en", ""),
                    "examples": r.get("examples", ""),
                    "tags": r.get("tags", "")
                })

    # 2) Дедуп по sense_uid (берем первую встретившуюся строку)
    seen_sense = set()
    deduped_rows = []
    for r in rows:
        su = r.get("sense_uid", "")
        if not su:
            # Если sense_uid отсутствует — оставим такие строки в конце (отдельно)
            # чтобы их не парил дедуп. Отметим флагом.
            r["_missing_sense_uid"] = "1"
            deduped_rows.append(r)
            continue
        if su not in seen_sense:
            seen_sense.add(su)
            deduped_rows.append(r)
        # иначе — дубликат по sense_uid, пропускаем

    # 3) Сортировка: сначала по phrasal (A→Z), затем по sense_uid
    # Строки без sense_uid оставим, но они тоже отсортируются по phrasal и пустому sense_uid.
    def sort_key(r):
        return (normalize_key(r.get("phrasal")),
                normalize_key(r.get("sense_uid")))
    deduped_rows.sort(key=sort_key)

    # 4) Запись чистого CSV (без служебной колонки)
    final_header = list(header)
    if "_missing_sense_uid" in final_header:
        final_header.remove("_missing_sense_uid")
    for r in deduped_rows:
        r.pop("_missing_sense_uid", None)

    write_rows(out_path, final_header, deduped_rows)

    # 5) Запись конфликтов (если есть)
    if conflicts:
        # Минимально полезный набор колонок для ревью
        conf_header = ["phrasal", "sense_uid", "meaning_en", "examples", "tags"]
        # Отсортируем конфликты по phrasal, затем sense_uid
        conflicts.sort(key=lambda r: (normalize_key(r.get("phrasal")),
                                      normalize_key(r.get("sense_uid"))))
        write_rows(conf_path, conf_header, conflicts)

    # 6) Итоговые сообщения
    print(f"[OK] Прочитано строк: {len(rows)}")
    print(f"[OK] Уникальных sense_uid: {len(seen_sense)}")
    print(f"[OK] Записано в очищенный CSV: {out_path} (строк: {len(deduped_rows)})")
    if conflicts:
        print(f"[WARN] Найдены конфликты (одинаковый phrasal с разными sense_uid): {len(set([c['phrasal'] for c in conflicts]))} phrasal")
        print(f"[INFO] См. файл для ручного ревью: {conf_path}")
        # Краткий пронумерованный вывод первых N конфликтов в консоль:
        preview = []
        last_ph = None
        for c in conflicts:
            ph = c["phrasal"]
            su = c["sense_uid"]
            if ph != last_ph:
                preview.append(f"\n{ph}:")
                last_ph = ph
            preview.append(f"  - {su} :: {c.get('meaning_en','')[:80]}")
        print("\n".join(preview))  # ограничим вывод, чтобы не заспамить терминал
    else:
        print("[OK] Конфликтов не обнаружено.")

if __name__ == "__main__":
    main()
