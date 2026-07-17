"""Drift tests for the methods.html catalog generator (scripts/sitegen/methods.py).

Guards the source-of-truth contract: sections come from methods/INDEX.md,
and every row's data is parsed from the METHOD.md card it links.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]          # .knowledge/methods

from sitegen import methods  # noqa: E402  (conftest puts scripts/ on sys.path)


@pytest.fixture(scope="module")
def sections():
    return methods.build_entries()


def test_index_sections_and_counts(sections):
    assert len(sections) == 7
    assert sections[0]["title"] == "Exact methods"
    assert sum(len(s["rows"]) for s in sections) == 36


def test_every_index_slug_has_a_card(sections):
    missing = [r["slug"] for s in sections for r in s["rows"]
               if not (ROOT / r["slug"] / "METHOD.md").exists()]
    assert not missing, f"INDEX.md slugs without a METHOD.md card: {missing}"


def test_accuracy_normalizes(sections):
    bad = [(r["slug"], r["accuracy"]) for s in sections for r in s["rows"]
           if r["acc"] == "other"]
    assert not bad, f"accuracy cells the acc_token rule cannot classify: {bad}"


def test_parse_method_card_on_dmrg():
    card = methods.parse_method_card(
        (ROOT / "dmrg" / "METHOD.md").read_text(encoding="utf-8"))
    assert "Density-Matrix Renormalization Group" in card["title"]
    assert len(card["props"]) == 14
    assert card["props"][0]["axis"].startswith("M1")
    assert card["cost"] and card["recommended"] and card["benchmarks"]
    assert "schollwoeck_2010_density" in card["keyref"]


def test_render_contains_card_data(sections):
    page = methods.render(sections)
    assert "methods/dmrg/METHOD.md" in page                 # source-card link
    assert "schollwoeck_2010_density" in page               # raw key (title attr)
    assert 'data-accuracy="controlled"' in page
    assert "Exact methods" in page
