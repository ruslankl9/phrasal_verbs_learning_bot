from __future__ import annotations

from srsbot.formatters import html_card_message


def test_html_card_message_format_and_escape() -> None:
    phrasal = 'act <on> & "this"'
    meaning = 'to take action based on advice & info'
    examples = '["We acted on the feedback.", "The police acted on a tip & didn\'t wait."]'
    tags = ["Work", "daily stuff", ""]
    txt = html_card_message(phrasal, meaning, examples, is_new=True, tags=tags)
    # New badge line
    assert txt.startswith("🆕\n")
    # Bold phrasal and italic meaning
    assert "<b>act &lt;on&gt; &amp; &quot;this&quot;</b>" in txt
    assert "<i>to take action based on advice &amp; info</i>" in txt
    # Examples bullets
    assert "Examples:" in txt
    assert "- We acted on the feedback." in txt
    assert "- The police acted on a tip &amp; didn\'t wait." in txt
    # Tags normalized and hashed
    assert "Tags: #work #daily_stuff" in txt

