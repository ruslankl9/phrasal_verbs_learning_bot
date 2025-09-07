from __future__ import annotations

from scripts.build_known_list import build_known_line


def test_known_line_building() -> None:
    # build_known_line accepts an iterable of rows where
    # row[0] is phrasal and row[1] is sense_uid, and returns
    # a sorted list of "phrasal(sense_uid)" entries, all lowercased.
    rows = [
        ("Bring up", "bring_up__mention"),
        ("look into", "LOOK_INTO__investigate"),
    ]
    items = build_known_line(rows)
    assert isinstance(items, list)
    assert items == [
        "bring up(bring_up__mention)",
        "look into(look_into__investigate)",
    ]
