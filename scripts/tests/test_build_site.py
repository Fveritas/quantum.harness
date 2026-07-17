"""Byte-stable check: committed catalog pages match regeneration from cards.

If this fails, a .knowledge/ card (or the generator) changed without
re-running the site build — run: python3 scripts/build_site.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_site  # noqa: E402

TEMPLATE = Path(__file__).resolve().parents[2] / ".github" / "template"


def test_committed_pages_match_regeneration():
    stale = []
    for name, html in build_site.build_all().items():
        committed = TEMPLATE / name
        if not committed.exists() or committed.read_text(encoding="utf-8") != html:
            stale.append(name)
    assert not stale, (f"stale catalog pages: {stale} — "
                       "run: python3 scripts/build_site.py")
