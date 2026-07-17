"""Unit tests for sitegen shared parsing helpers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sitegen import parse  # noqa: E402

CARD = r"""\
# Heisenberg

Solve Heisenberg-spin ground-state problems.
Exact solution: see `.knowledge/solvable/heisenberg-xxx/` (oracle card).

## Physics card

### Hamiltonian

$$ H = J \sum_{\langle ij\rangle} \mathbf{S}_i\cdot\mathbf{S}_j $$

### Properties (A1–D16)

| Axis | Value | Note |
|---|---|---|
| A1 dimension & geometry | 1D chain / 2D square | Geometry is the master axis. |
| C12 sign problem | sign-free on bipartite · sign-ful on frustrated | Frustration turns it on. |

### Phases & order parameters

- 1D S=1/2 AFM chain : quasi-long-range order
- 2D square AFM : Néel order

### Benchmarks

- 1D chain (PBC): `E/N = 1/4 − ln 2 ≈ −0.443147` — exact Bethe ansatz [@Hulthen1938].

## Diagnose

Infer the canonical setup.
"""


def test_section_level2():
    body = parse.section(CARD, "Physics card", level=2)
    assert "Hamiltonian" in body
    assert "Diagnose" not in body


def test_section_level3_prefix():
    body = parse.section(CARD, "Properties (A1", level=3, prefix=True)
    assert "| A1 dimension" in body
    assert "Diagnose" not in body


def test_section_missing_returns_empty():
    assert parse.section(CARD, "No such heading") == ""


def test_section_prefix_drops_heading_tail():
    body = parse.section(CARD, "Properties (A1", level=3, prefix=True)
    assert not body.startswith("–D16")
    assert body.lstrip().startswith("| Axis |")


def test_axis_table_skips_header_and_separator():
    rows = parse.axis_table(parse.section(CARD, "Properties (A1", level=3, prefix=True))
    assert len(rows) == 2
    assert rows[0]["axis"].startswith("A1")
    assert rows[0]["value"] == "1D chain / 2D square"
    assert rows[0]["note"] == "Geometry is the master axis."
    assert rows[1]["axis"].startswith("C12")


def test_bullets():
    bl = parse.bullets(parse.section(CARD, "Phases & order parameters", level=3))
    assert bl == ["1D S=1/2 AFM chain : quasi-long-range order",
                  "2D square AFM : Néel order"]


def test_strip_md():
    assert parse.strip_md("**bold** `code` [text](url)") == "bold code text"


def test_md_inline_cites_and_code():
    out = parse.md_inline("[@Pfeuty1970]")
    assert ">Pfeuty 1970<" in out
    assert 'title="[@Pfeuty1970]"' in out
    multi = parse.md_inline("[@LiebSchultzMattis1961; @Kitaev2003]")
    assert "Lieb–Schultz–Mattis 1961" in multi
    assert "Kitaev 2003" in multi
    assert "<code>x</code>" in parse.md_inline("`x`")
    assert parse.md_inline("a < b") == "a &lt; b"


def test_md_inline_bold():
    assert "<b>DMRG/MPS</b>" in parse.md_inline("**DMRG/MPS** works")
    assert "**" not in parse.md_inline("a **b** c **d** e")


def test_fmt_cite_yearless():
    assert parse.fmt_cite("@Baxter") == "Baxter"


def test_fmt_cite_snake_case_degrades_to_key():
    assert parse.fmt_cite("@schollwoeck_2010_density") == "schollwoeck_2010_density"


def test_axis_table_escaped_pipe_stays_in_cell():
    rows = parse.axis_table("| Axis | Value | Note |\n|---|---|---|\n"
                            "| A1 | a \\| b | n |\n")
    assert rows == [{"axis": "A1", "value": "a \\| b", "note": "n"}]


def test_bullets_star_markers():
    assert parse.bullets("* one\n- two\n") == ["one", "two"]


def test_list_block():
    assert parse.list_block("H", ["a **b**"]) == "<h3>H</h3>\n<ul>\n<li>a <b>b</b></li>\n</ul>"
    assert parse.list_block("H", []) == ""
