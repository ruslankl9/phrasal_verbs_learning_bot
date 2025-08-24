from __future__ import annotations

from scripts.gen_phrasals_via_codex import build_prompt


def test_prompt_contains_constraints() -> None:
    p = build_prompt(5, ["work", "travel"], "bring up,bring_up__mention")
    assert "Generate EXACTLY 5 rows" in p
    assert "KNOWN (case-insensitive, comma-separated): bring up,bring_up__mention" in p
    assert 'TAGS (optional hint): ["work", "travel"]' in p
    # Header is present and exact
    assert "phrasal,meaning_en,examples,tags,sense_uid,separable,intransitive" in p

