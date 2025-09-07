from srsbot.formatters import build_card_prompt_text


def test_build_card_prompt_text_includes_core_fields():
    phrasal = "look up"
    meaning = "to search for information"
    examples_json = '["I looked up the word.", "She looked up the address."]'
    txt = build_card_prompt_text(phrasal, meaning, examples_json, tags=["work", "Projects"]) 

    assert "look up" in txt
    assert "to search for information" in txt
    assert "I looked up the word." in txt
    assert "She looked up the address." in txt
    # Normalized tag appears as hashtag
    assert "#work" in txt
    assert "#projects" in txt

