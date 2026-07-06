"""A tiny, dependency-free Markdown -> HTML renderer for the Notes page.

Supports the subset an author needs for field notes: ``#``/``##``/``###``
headings, paragraphs, ``- ``/``* `` unordered lists, ``---`` rules, fenced
``` code blocks, and inline **bold**, *italic*, ``code`` and ``[text](url)``
links. Input is HTML-escaped first, so author text can never inject markup; only
the formatting this module emits is allowed through.
"""

from __future__ import annotations

import html
import re

_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_CODE = re.compile(r"`([^`]+)`")


def _inline(text: str) -> str:
    # text is already HTML-escaped; restore the few inline constructs.
    text = _CODE.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    text = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", text)
    text = _ITALIC.sub(lambda m: f"<em>{m.group(1)}</em>", text)
    text = _LINK.sub(
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )
    return text


def render(md: str) -> str:
    """Render Markdown ``md`` to an HTML fragment string."""
    lines = html.escape(md, quote=False).replace("\r\n", "\n").split("\n")
    out: list[str] = []
    para: list[str] = []
    in_list = False
    in_code = False
    code: list[str] = []

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + _inline(" ".join(para).strip()) + "</p>")
            para = []

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                out.append("<pre><code>" + "\n".join(code) + "</code></pre>")
                code = []
                in_code = False
            else:
                flush_para(); close_list()
                in_code = True
            continue
        if in_code:
            code.append(line)
            continue

        if not stripped:
            flush_para(); close_list()
            continue
        if stripped in ("---", "***", "___"):
            flush_para(); close_list()
            out.append("<hr />")
            continue

        m = re.match(r"(#{1,3})\s+(.*)", stripped)
        if m:
            flush_para(); close_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            continue

        m = re.match(r"[-*]\s+(.*)", stripped)
        if m:
            flush_para()
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append("<li>" + _inline(m.group(1).strip()) + "</li>")
            continue

        para.append(stripped)

    if in_code:  # unterminated fence
        out.append("<pre><code>" + "\n".join(code) + "</code></pre>")
    flush_para(); close_list()
    return "\n".join(out)
