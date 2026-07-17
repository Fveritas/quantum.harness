"""Unit tests for the sitegen shared page shell."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sitegen import shell  # noqa: E402


def test_nav_links_and_here_marker():
    n = shell.nav("models.html")
    for href, label in [("index.html", "Home"), ("solvable.html", "Solvable"),
                        ("models.html", "Models"), ("methods.html", "Methods")]:
        assert f'href="{href}"' in n and f">{label}<" in n
    assert '<a href="models.html" class="here">' in n
    assert '<a href="methods.html">' in n  # no class on non-current links


def test_chips_buttons():
    out = shell.chips("sign", ["sign-free", "sign-ful"],
                      {"sign-free": "no sign problem"})
    assert 'data-group="sign"' in out and 'data-val="sign-free"' in out
    assert 'aria-pressed="false"' in out
    assert 'title="no sign problem"' in out


def test_page_assembles_all_parts():
    page = shell.page(title="T", lead="L", total=3, chips_html="CHIPS",
                      sections_html="SECTIONS", footer_html="FOOT",
                      here="models.html", search_placeholder="search…")
    assert page.startswith("<!DOCTYPE html>")
    for needle in ("CHIPS", "SECTIONS", "FOOT", ">T</h1>", ">L</p>",
                   '3 of 3', 'placeholder="search…"',
                   'class="topnav"', 'id="q"', 'renderMathInElement'):
        assert needle in page
    assert shell.CSS in page and shell.FILTER_JS in page and shell.KATEX_HEAD in page
