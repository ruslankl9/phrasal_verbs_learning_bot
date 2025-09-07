from srsbot.formatters import markdown_to_html_telegram


def test_md_bold_italic_code_and_links():
    md = "**Bold** *Ital* _AlsoItalic_ ~~gone~~ `x<y` [link](https://ex.com?a=1&b=2)"
    html = markdown_to_html_telegram(md)
    assert "<b>Bold</b>" in html
    assert "<i>Ital</i>" in html
    assert "<i>AlsoItalic</i>" in html
    assert "<s>gone</s>" in html
    assert "<code>x&lt;y</code>" in html
    assert '<a href="https://ex.com?a=1&amp;b=2">link</a>' in html


def test_md_codeblock_and_heading():
    md = "# Title\n\n```py\nprint('x<y')\n```"
    html = markdown_to_html_telegram(md)
    assert "<b>Title</b>" in html
    assert "<pre><code>print(&#x27;x&lt;y&#x27;)</code></pre>" in html

