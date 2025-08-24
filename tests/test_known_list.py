from __future__ import annotations

from pathlib import Path

from scripts.build_known_list import build_known_line


def test_known_line_building() -> None:
    content = build_known_line(
        ["Bring up", "look into", ""], ["bring_up__mention", "LOOK_INTO__investigate"]
    )
    assert "\n" not in content
    parts = [p.strip() for p in content.split(",")]
    assert set(parts) == {
        "bring up",
        "look into",
        "bring_up__mention",
        "look_into__investigate",
    }
