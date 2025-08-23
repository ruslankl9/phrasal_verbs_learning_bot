from __future__ import annotations

import json
from typing import Iterable


def render_card(phrasal: str, meaning_en: str, examples_json: str) -> str:
    examples: list[str] = []
    try:
        examples = list(json.loads(examples_json))
    except Exception:
        pass
    lines = [phrasal, f"— {meaning_en}"]
    for i, ex in enumerate(examples[:3], start=1):
        lines.append(f"Ex{i}: {ex}")
    return "\n".join(lines)

