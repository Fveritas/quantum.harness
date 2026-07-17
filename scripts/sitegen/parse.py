"""Shared markdown-card parsing for the catalog generators.

All helpers are pure string functions — the cards under .knowledge/ are the
single source of truth, and these are the only places card markdown is read.
"""
from __future__ import annotations

import html
import re


def section(text: str, heading: str, level: int = 2, prefix: bool = False) -> str:
    """Body of the markdown section `heading` (literal, at `level`).

    prefix=True matches headings that merely start with `heading`
    (e.g. "Properties (A1" for "Properties (A1–D16)"). The section ends at
    the next heading of the same or higher level, or at end of text.
    """
    hashes = "#" * level
    tail = r"[^\n]*" if prefix else r"\s*$"
    m = re.search(rf"^{hashes} {re.escape(heading)}{tail}(.*?)(?=^#{{1,{level}}} |\Z)",
                  text, re.M | re.S)
    return m.group(1).strip() if m else ""


def strip_md(text: str) -> str:
    """Markdown → plain text: drop emphasis/code markers and link targets."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # [text](url) -> text
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def axis_table(body: str) -> list:
    """Parse a 3-column `| Axis | Value | Note |` table into dict rows."""
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) < 3:
            continue
        if cells[0] in ("Axis", "") or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append({"axis": cells[0], "value": cells[1], "note": cells[2]})
    return rows


def bullets(body: str) -> list:
    """`- item` / `* item` lines of a section, stripped of the marker."""
    out = []
    for line in body.splitlines():
        m = re.match(r"\s*[-*]\s+(.*)", line)
        if m:
            out.append(m.group(1).strip())
    return out


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def fmt_cite(key: str) -> str:
    """'@LiebSchultzMattis1961' -> 'Lieb–Schultz–Mattis 1961' (readable citekey).

    Snake_case keys with a mid-string year (e.g. 'schollwoeck_2010_density')
    degrade to the key unchanged — still readable, and the raw key is kept
    alongside in a title= attribute by cite_spans for provenance.
    """
    key = key.strip().lstrip("@")
    m = re.match(r"(.*?)(\d{4}[a-z]?)?$", key)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", "–", m.group(1))
    year = m.group(2)
    return f"{name} {year}" if year else name


def cite_spans(escaped: str) -> str:
    """Replace [@Key] / [@Key1; @Key2] tokens with readable spans.

    The raw citekey token is kept as a title= attribute for provenance.
    Input must already be HTML-escaped.
    """
    def repl(m):
        keys = [k for k in m.group(1).split(";") if k.strip()]
        pretty = ", ".join(fmt_cite(k) for k in keys)
        return f'<span class="cite" title="{esc(m.group(0))}">{esc(pretty)}</span>'
    return re.sub(r"\[@([^\]]+)\]", repl, escaped)


def md_inline(s: str) -> str:
    """Inline markdown for an HTML cell: escape, humanize cites, `code` -> <code>,
    **bold** -> <b>."""
    s = s.replace("\\|", "|")
    out = cite_spans(esc(s))
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)


def list_block(heading: str, items: list) -> str:
    """`<h3>heading</h3><ul>…</ul>` block from bullet strings; "" when empty."""
    if not items:
        return ""
    lis = "\n".join(f"<li>{md_inline(i)}</li>" for i in items)
    return f"<h3>{esc(heading)}</h3>\n<ul>\n{lis}\n</ul>"
