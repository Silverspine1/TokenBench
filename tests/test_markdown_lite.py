from tokenbench.analysis.markdown_lite import render


def test_headings_and_paragraph():
    h = render("# Title\n\nHello world.")
    assert "<h1>Title</h1>" in h
    assert "<p>Hello world.</p>" in h


def test_list_and_inline():
    h = render("- one **bold**\n- two `code`\n- [link](https://x.io)")
    assert h.count("<li>") == 3
    assert "<strong>bold</strong>" in h
    assert "<code>code</code>" in h
    assert '<a href="https://x.io" target="_blank" rel="noopener">link</a>' in h


def test_code_fence_and_rule():
    h = render("```\nx = 1\n```\n\n---\n\nafter")
    assert "<pre><code>x = 1</code></pre>" in h
    assert "<hr />" in h
    assert "<p>after</p>" in h


def test_html_is_escaped():
    h = render("watch <script>alert(1)</script> out")
    assert "<script>" not in h
    assert "&lt;script&gt;" in h
