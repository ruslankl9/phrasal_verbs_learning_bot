from __future__ import annotations

from srsbot.handlers import settings as settings_mod


def test_quiz_limit_field_present_and_validates():
    assert "quiz_question_limit" in settings_mod.FIELD_META
    title, desc, validator = settings_mod.FIELD_META["quiz_question_limit"]
    assert "Quiz questions" in title
    ok, err = validator("10")
    assert ok and err is None
    ok, err = validator("4")
    assert not ok and "integer" in (err or "").lower()


def test_fmt_settings_text_includes_quiz_limit():
    text = settings_mod._fmt_settings_text((8, 35, "09:00", "", 3, 12))
    assert "Quiz questions per session: 12" in text
