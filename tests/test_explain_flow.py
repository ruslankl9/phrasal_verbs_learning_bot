from srsbot.formatters import format_explain_loading_html, format_explain_error_html, html_card_message
from srsbot.keyboards import today_card_kb, kb_explain_back


def test_today_card_keyboard_includes_explain():
    kb = today_card_kb(1)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Again" in texts and "Good" in texts
    assert any("Explain" in t for t in texts)


def test_explain_back_keyboard():
    kb = kb_explain_back(1)
    rows = kb.inline_keyboard
    assert len(rows) == 1 and len(rows[0]) == 1
    assert rows[0][0].text.startswith("◀️ Back")


def test_loading_and_error_texts():
    loading = format_explain_loading_html()
    error = format_explain_error_html()
    assert "Explain" in loading and "Loading" in loading
    assert "Explain" in error and "Sorry" in error

