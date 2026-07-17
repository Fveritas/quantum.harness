"""Generate the methods.html catalog page from .knowledge/methods/ cards.

Sections are parsed from .knowledge/methods/INDEX.md (the index stays the
source of truth — no re-curation); every row's content is parsed from the
card's METHOD.md. Drift is caught by .knowledge/methods/tests/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import parse, shell

REPO = Path(__file__).resolve().parents[2]
METHODS_DIR = REPO / ".knowledge" / "methods"
INDEX_MD = METHODS_DIR / "INDEX.md"
BLOB = "https://github.com/QuantumBFS/quantum.harness/blob/main/.knowledge/methods/"

ROW_RE = re.compile(
    r"^\|\s*([^|`]+?)\s*\|\s*`([^`]+)`\s*\|([^|]*)\|([^|]*)\|\s*\[@([^\]]+)\]",
    re.M)

ACC_TITLES = {
    "exact": "numerically exact (machine/statistical error)",
    "upper": "variational upper bound",
    "lower": "certified lower bound",
    "controlled": "systematically improvable (convergence knob)",
    "uncontrolled": "no internal convergence parameter",
}


def acc_token(cell: str) -> str:
    """First accuracy-class keyword in an INDEX.md accuracy cell."""
    m = re.search(r"\b(exact|upper|lower|controlled|uncontrolled)\b", cell.lower())
    return m.group(1) if m else "other"


def skill_slug(skill: str) -> str:
    """'`/method-mps`' -> 'method-mps'; 'classical MC (no dedicated skill)' -> 'classical-mc'."""
    s = skill.strip().strip("`").lstrip("/").split("(")[0].strip()
    return re.sub(r"\s+", "-", s).lower()


def parse_methods_index(text: str) -> list:
    """Parse INDEX.md into ordered sections of method rows."""
    sections = []
    for sec in re.split(r"^## ", text, flags=re.M):
        head = re.match(r"(\d+)\.\s+(.+)", sec)
        if not head:
            continue
        rows = [{
            "name": r.group(1).strip(), "slug": r.group(2).strip(),
            "accuracy": r.group(3).strip(), "acc": acc_token(r.group(3)),
            "skill": r.group(4).strip(), "skill_slug": skill_slug(r.group(4)),
            "key": r.group(5).strip(),
        } for r in ROW_RE.finditer(sec)]
        sections.append({"num": head.group(1), "title": head.group(2).strip(),
                         "rows": rows})
    return sections


def parse_method_card(text: str) -> dict:
    """Extract title/M1–M14 table/lists from a METHOD.md card."""
    title = ""
    for ln in re.sub(r"\A(<!--.*?-->\s*)+", "", text, flags=re.S).splitlines():
        m = re.match(r"#\s+(.+?)\s*$", ln)
        if m:
            title = m.group(1)
            break
    keyref_sec = parse.section(text, "Key reference", level=3)
    return {
        "title": title,
        "props": parse.axis_table(
            parse.section(text, "Properties (M1", level=3, prefix=True)),
        "cost": parse.bullets(parse.section(text, "Cost & scaling", level=3)),
        "recommended": parse.bullets(
            parse.section(text, "Recommended for", level=3, prefix=True)),
        "keyref": keyref_sec.splitlines()[0].strip() if keyref_sec else "",
        "benchmarks": parse.bullets(parse.section(text, "Benchmarks", level=3)),
    }


def build_entries() -> list:
    """Parse INDEX.md, then attach each row's parsed METHOD.md card."""
    sections = parse_methods_index(INDEX_MD.read_text(encoding="utf-8"))
    for s in sections:
        for r in s["rows"]:
            card_md = METHODS_DIR / r["slug"] / "METHOD.md"
            r["card"] = parse_method_card(card_md.read_text(encoding="utf-8"))
            if len(r["card"]["props"]) != 14:
                print(f"warning: method '{r['slug']}' parsed "
                      f"{len(r['card']['props'])} M1–M14 rows (expected 14)",
                      file=sys.stderr)
    return sections


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _badges(r: dict) -> str:
    acc_cls = {"exact": "b-ok", "uncontrolled": "b-warn"}.get(r["acc"], "")
    return (
        f'<span class="bset">'
        f'<span class="b {acc_cls}" title="{parse.esc(ACC_TITLES.get(r["acc"], ""))}">'
        f'{parse.esc(r["acc"])}</span>'
        f'<span class="b" title="{parse.esc(r["skill"])}">{parse.esc(r["skill_slug"])}</span>'
        f'<span class="b" title="[@{parse.esc(r["key"])}]">{parse.esc(parse.fmt_cite(r["key"]))}</span>'
        f'</span>'
    )


def _data_attrs(r: dict, num: str) -> str:
    return (f'data-name="{parse.esc(r["slug"] + " " + r["name"])}"'
            f' data-hook=""'
            f' data-family="{num}" data-accuracy="{r["acc"]}"'
            f' data-skill="{parse.esc(r["skill_slug"])}"'
            f' data-extra="{parse.esc(r["skill"] + " " + r["key"])}"')


def _render_row(r: dict, num: str) -> str:
    card = r["card"]
    body = []
    if card["props"]:
        rows = "\n".join(
            f'<tr><td>{parse.md_inline(p["axis"])}</td>'
            f'<td>{parse.md_inline(p["value"])}</td>'
            f'<td>{parse.md_inline(p["note"])}</td></tr>'
            for p in card["props"])
        body.append(
            '<div class="tablewrap"><table class="bench">'
            '<thead><tr><th>Axis</th><th>Value</th><th>Note</th></tr></thead>\n'
            f'<tbody>\n{rows}\n</tbody></table></div>')
    body.append(parse.list_block("Cost & scaling", card["cost"]))
    body.append(parse.list_block("Recommended for", card["recommended"]))
    body.append(parse.list_block("Benchmarks", card["benchmarks"]))
    if card["keyref"]:
        body.append(f'<p class="solv">Key reference: {parse.md_inline(card["keyref"])}</p>')
    body.append(f'<p class="cardlinks">'
                f'<a href="{BLOB}{r["slug"]}/METHOD.md">METHOD.md&nbsp;&#8599;</a></p>')
    body_html = "\n".join(b for b in body if b)
    return (
        f'<details class="model" {_data_attrs(r, num)}>\n'
        f'<summary><span class="mname">{parse.esc(r["name"])}</span>'
        f'<span class="hook">{parse.esc(r["slug"])}</span>{_badges(r)}</summary>\n'
        f'<div class="mbody">\n{body_html}\n</div>\n'
        f'</details>'
    )


def render(sections: list) -> str:
    """Render the full methods.html page from build_entries sections."""
    total = sum(len(s["rows"]) for s in sections)

    rendered = []
    for s in sections:
        rows = "\n".join(_render_row(r, s["num"]) for r in s["rows"])
        rendered.append(f'''<section class="tgroup" data-tech="{s["num"]}">
<h2><span class="tcode">{s["num"]}</span> {parse.esc(s["title"])}
<span class="scount" data-total="{len(s["rows"])}">{len(s["rows"])}</span></h2>
{rows}
</section>''')
    sections_html = "\n\n".join(rendered)

    family_titles = {s["num"]: s["title"] for s in sections}
    acc_vals = [a for a in ["exact", "upper", "lower", "controlled", "uncontrolled"]
                if any(r["acc"] == a for s in sections for r in s["rows"])]
    skill_vals, skill_titles = [], {}
    for s in sections:
        for r in s["rows"]:
            if r["skill_slug"] not in skill_titles:
                skill_vals.append(r["skill_slug"])
                skill_titles[r["skill_slug"]] = r["skill"].strip("`")
    chips_html = (
        f'<span class="cgroup"><span class="clabel">Family</span>'
        f'{shell.chips("family", [s["num"] for s in sections], family_titles)}</span>\n'
        f'<span class="cgroup"><span class="clabel">Accuracy</span>'
        f'{shell.chips("accuracy", acc_vals, ACC_TITLES)}</span>\n'
        f'<span class="cgroup"><span class="clabel">Skill</span>'
        f'{shell.chips("skill", skill_vals, skill_titles)}</span>'
    )

    return shell.page(
        title="Computational methods",
        lead=(f"The harness's method zoo: {total} computational methods for "
              "quantum many-body problems, each with its accuracy class, an "
              "M1–M14 property table (tasks, regime, cost, scaling, failure "
              "modes), and verified benchmarks. Every row is generated from "
              "the method's knowledge-base card."),
        total=total,
        chips_html=chips_html,
        sections_html=sections_html,
        footer_html=(
            "<p>Accuracy: <b>exact</b> numerically exact &middot; <b>upper</b> "
            "variational upper bound &middot; <b>lower</b> certified lower bound "
            "&middot; <b>controlled</b> systematically improvable &middot; "
            "<b>uncontrolled</b> no convergence knob. Cards live under "
            f'<a href="{BLOB}INDEX.md">.knowledge/methods/</a>; the models they '
            'solve are on the <a href="models.html">models catalog</a>.</p>'),
        here="methods.html",
        search_placeholder="search methods&hellip;",
    )


def build_page() -> str:
    return render(build_entries())
