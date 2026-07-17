"""Drift tests for the models.html catalog generator (scripts/sitegen/models.py).

These guard the source-of-truth contract: every MODEL.md card appears on the
page exactly once, with data parsed from the card itself.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]          # .knowledge/models

from sitegen import models  # noqa: E402  (conftest puts scripts/ on sys.path)


@pytest.fixture(scope="module")
def entries():
    return models.build_entries()


def _card_slugs():
    return sorted(p.name for p in ROOT.iterdir()
                  if p.is_dir() and (p / "MODEL.md").exists())


def test_families_cover_every_card_exactly_once():
    fam_slugs = [s for _, _, slugs in models.FAMILIES for s in slugs]
    dupes = {s for s in fam_slugs if fam_slugs.count(s) > 1}
    assert not dupes, f"slug assigned to more than one family: {dupes}"
    assert sorted(fam_slugs) == _card_slugs(), (
        "FAMILIES out of sync with .knowledge/models/ — "
        f"only in FAMILIES: {sorted(set(fam_slugs) - set(_card_slugs()))}, "
        f"only on disk: {sorted(set(_card_slugs()) - set(fam_slugs))}")


def test_every_card_has_a_hook(entries):
    missing = [e["slug"] for e in entries if not e["hook"].strip()]
    assert not missing, f"cards missing a HOOKS entry: {missing}"


def test_sign_chip_rule_classifies_every_card(entries):
    bad = [(e["slug"], e["sign"]) for e in entries if e["sign"] == "unknown"]
    assert not bad, f"C12 text the sign_chip rule cannot classify: {bad}"


def test_primary_method_chips_parse_for_every_card(entries):
    bad = [e["slug"] for e in entries if not e["methods"]]
    assert not bad, f"cards with no Primary-method chips: {bad}"


def test_parse_model_card_on_heisenberg():
    card = models.parse_model_card(
        (ROOT / "heisenberg" / "MODEL.md").read_text(encoding="utf-8"))
    assert card["title"] == "Heisenberg"
    assert "\\sum" in card["hamiltonian"] and "$$" not in card["hamiltonian"]
    assert len(card["props"]) == 16
    assert card["props"][0]["axis"].startswith("A1")
    c12 = next(r["value"] for r in card["props"] if r["axis"].startswith("C12"))
    assert "sign-free" in c12
    assert card["phases"] and card["observables"]
    assert card["methods"] and card["benchmarks"]
    assert card["solvable_slug"] == "heisenberg-xxx"


def test_render_contains_card_data(entries):
    page = models.render(entries)
    assert "0.443147" in page                       # heisenberg benchmark
    assert "models/heisenberg/MODEL.md" in page     # source-card link
    assert 'data-sign="mixed"' in page              # heisenberg sign chip
    assert page.count('class="model"') >= 29 or page.count("<details") >= 29
