"""Generate the models.html catalog page from .knowledge/models/ cards.

Sections are physics families (curated FAMILIES below — presentation only);
every row's content is parsed from the card's MODEL.md, which stays the
single source of truth. Drift is caught by .knowledge/models/tests/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import parse, shell

REPO = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO / ".knowledge" / "models"
BLOB = "https://github.com/QuantumBFS/quantum.harness/blob/main/.knowledge/models/"

FAMILIES = [
    ("spins", "Spin chains & magnets",
     ["heisenberg", "xxz-chain", "spin-1-xxz", "transverse-field-ising",
      "aklt", "potts-clock"]),
    ("frustrated", "Frustrated & topological spin systems",
     ["j1-j2", "shastry-sutherland", "kitaev-honeycomb", "spin-ice-pyrochlore",
      "toric-code"]),
    ("hubbard", "Hubbard & correlated fermions",
     ["hubbard", "attractive-hubbard", "multiorbital-hubbard", "t-j", "t-v",
      "falicov-kimball", "kondo-lattice", "anderson-impurity"]),
    ("topo", "Topological band models",
     ["ssh", "haldane-chern", "hofstadter", "kitaev-chain"]),
    ("disorder", "Disorder, MBL & open systems",
     ["anderson-localization", "mbl-disordered-heisenberg", "sachdev-ye-kitaev",
      "dissipative-spin-lindblad"]),
    ("bosons", "Bosons & Rydberg arrays",
     ["bose-hubbard", "rydberg-pxp"]),
]

FAMILY_SUBTITLES = {
    "spins": "nearest-neighbor quantum magnets — critical chains, Néel order, Haldane physics",
    "frustrated": "competing exchanges and Z₂ topological order — where QMC meets the sign problem",
    "hubbard": "itinerant fermions with on-site repulsion — Mott, pairing, Kondo physics",
    "topo": "quadratic hopping with topology — edge zero modes and Chern numbers",
    "disorder": "random potentials, many-body localization, SYK, and driven-dissipative steady states",
    "bosons": "lattice bosons and Rydberg blockade — superfluid–Mott transition and quantum scars",
}

HOOKS = {
    "heisenberg": "SU(2) quantum magnet; Néel to spin liquid",
    "xxz-chain": "anisotropic chain; Néel–XY–ferro phases",
    "spin-1-xxz": "Haldane gap; string order",
    "transverse-field-ising": "quantum-critical Ising; Wilson–Fisher 2D",
    "aklt": "exact VBS state; Haldane SPT",
    "potts-clock": "q-state symmetry; BKT and ordering",
    "j1-j2": "frustrated chain/square; dimerized, spin-liquid",
    "shastry-sutherland": "orthogonal dimers; SrCu₂(BO₃)₂ plateaus",
    "kitaev-honeycomb": "Kitaev spin liquid; Majorana partons",
    "spin-ice-pyrochlore": "ice rules; emergent monopoles",
    "toric-code": "Z₂ topological order; anyons",
    "hubbard": "Mott physics; d-wave pairing question",
    "attractive-hubbard": "s-wave pairing; BCS–BEC crossover",
    "multiorbital-hubbard": "Hund coupling; orbital-selective Mott",
    "t-j": "doped Mott insulator; no double occupancy",
    "t-v": "extended Hubbard; charge-order competition",
    "falicov-kimball": "localized f-electrons; exact in d=∞",
    "kondo-lattice": "screened local moments; heavy fermions",
    "anderson-impurity": "single magnetic impurity; Kondo singlet",
    "ssh": "dimerized chain; topological edge zero modes",
    "haldane-chern": "Chern insulator; anomalous Hall",
    "hofstadter": "flux per plaquette; butterfly spectrum",
    "kitaev-chain": "p-wave wire; Majorana end modes",
    "anderson-localization": "disordered potential; localized states",
    "mbl-disordered-heisenberg": "many-body localization; ETH violation",
    "sachdev-ye-kitaev": "maximally chaotic; strange metal",
    "dissipative-spin-lindblad": "driven-dissipative; Lindblad steady state",
    "bose-hubbard": "superfluid–Mott transition; lattice bosons",
    "rydberg-pxp": "Rydberg blockade; quantum scars",
}

# display + ≤3-cap priority order
METHOD_TOKENS = [
    "AFQMC", "DQMC", "iPEPS", "CTMRG", "iTEBD", "XTRG", "LTRG", "TEBD",
    "TDVP", "DMRG", "MPS", "PEPS", "MERA", "QMC", "SSE", "VMC", "NQS",
    "DMFT", "PIMC", "MCRG", "NRG", "ED", "HF", "mean-field",
    "free-fermion", "stabilizer", "Schwinger–Dyson",
]

# Tokens that need a looser regex than plain \b<tok>\b.
TOKEN_PATTERNS = {
    "mean-field": r"mean[- ]field",
    # exact quadratic / one-body routes: the cards phrase these as
    # "free-fermion diagonalization", "one-body diagonalization", or
    # "single-particle diagonalization" — one chip for the family.
    "free-fermion": r"free[- ]fermion|one[- ]body|single[- ]particle",
}

SIGN_TITLES = {
    "sign-free": "no sign problem — QMC exact at scale",
    "sign-ful": "sign problem blocks QMC",
    "mixed": "sign-free in some regimes, sign-ful in others",
    "n/a": "not a QMC target — exact, free-fermion, or non-QMC route",
}


def sign_chip(c12_value: str) -> str:
    """Normalize the C12 sign-problem axis to sign-free / sign-ful / mixed / n/a."""
    v = c12_value.lower().replace("no sign problem", "sign-free")
    # Cards whose sign axis is not applicable say so up front
    # ("N/A — free fermions…", "n/a — not a QMC target…").
    if v.lstrip("* ").startswith("n/a"):
        return "n/a"
    free = "sign-free" in v or "sign free" in v
    rest = v.replace("sign-free", "").replace("sign free", "")
    ful = ("sign-ful" in rest or "sign ful" in rest
           or "sign-problematic" in rest or "sign-blocked" in rest
           or "sign problem" in rest or "severe" in rest)
    if free and ful:
        return "mixed"
    if free:
        return "sign-free"
    if ful:
        return "sign-ful"
    return "unknown"


def method_chips(method_bullets: list) -> list:
    """Method tokens from the `Primary` bullets of Recommended methods.

    Bold spans are scanned when present, else the whole bullet; at most 3.
    """
    found = []
    for b in method_bullets:
        if not re.match(r"Primary\b", b):
            continue
        bold = re.findall(r"\*\*([^*]+)\*\*", b)
        hay = " ".join(bold) if bold else b
        for tok in METHOD_TOKENS:
            if tok in TOKEN_PATTERNS:
                hit = re.search(TOKEN_PATTERNS[tok], hay, re.I)
            else:
                hit = re.search(rf"\b{re.escape(tok)}\b", hay)
            if hit and tok not in found:
                found.append(tok)
    return found[:3]


def parse_model_card(text: str) -> dict:
    """Extract title/hamiltonian/property-table/lists from a MODEL.md card."""
    m = re.match(r"#\s+(.+?)\s*$", text.splitlines()[0])
    title = m.group(1) if m else ""
    m = re.search(r"\$\$(.+?)\$\$", text, re.S)
    hamiltonian = m.group(1).strip() if m else ""
    keyref_sec = parse.section(text, "Key reference", level=3)
    m = re.search(r"Exact solution: see `\.knowledge/solvable/([^/`]+)/`", text)
    return {
        "title": title,
        "hamiltonian": hamiltonian,
        "props": parse.axis_table(
            parse.section(text, "Properties (A1", level=3, prefix=True)),
        "phases": parse.bullets(
            parse.section(text, "Phases & order parameters", level=3)),
        "observables": parse.bullets(
            parse.section(text, "Canonical observables", level=3)),
        "methods": parse.bullets(
            parse.section(text, "Recommended methods", level=3)),
        "keyref": keyref_sec.splitlines()[0].strip() if keyref_sec else "",
        "benchmarks": parse.bullets(
            parse.section(text, "Benchmarks", level=3)),
        "solvable_slug": m.group(1) if m else None,
    }


def build_entries() -> list:
    """Parse every card listed in FAMILIES into a render-ready entry."""
    entries = []
    for code, title, slugs in FAMILIES:
        for slug in slugs:
            card_md = MODELS_DIR / slug / "MODEL.md"
            card = parse_model_card(card_md.read_text(encoding="utf-8"))
            c12 = next((r["value"] for r in card["props"]
                        if r["axis"].startswith("C12")), "")
            hook = HOOKS.get(slug, "")
            if not hook.strip():
                print(f"warning: model '{slug}' has no HOOKS entry", file=sys.stderr)
            if len(card["props"]) != 16:
                print(f"warning: model '{slug}' parsed {len(card['props'])} "
                      f"A1–D16 rows (expected 16)", file=sys.stderr)
            entries.append({
                "slug": slug, "name": card["title"] or slug,
                "family": code, "family_title": title,
                "hook": hook, "sign": sign_chip(c12),
                "methods": method_chips(card["methods"]),
                "card": card,
            })
    return entries


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _badges(e: dict) -> str:
    sign_cls = {"sign-free": "b-ok", "sign-ful": "b-warn"}.get(e["sign"], "")
    cls = f"b {sign_cls}" if sign_cls else "b"
    parts = [f'<span class="{cls}" title="{parse.esc(SIGN_TITLES.get(e["sign"], ""))}">'
             f'{parse.esc(e["sign"])}</span>']
    parts += [f'<span class="b">{parse.esc(m)}</span>' for m in e["methods"]]
    return f'<span class="bset">{"".join(parts)}</span>'


def _data_attrs(e: dict) -> str:
    return (f'data-name="{parse.esc(e["slug"] + " " + e["name"])}"'
            f' data-hook="{parse.esc(e["hook"])}"'
            f' data-family="{e["family"]}" data-sign="{e["sign"]}"'
            f' data-method="{parse.esc(" ".join(e["methods"]))}"'
            f' data-extra="{parse.esc(e["family_title"])}"')


def _render_row(e: dict) -> str:
    card = e["card"]
    body = []
    if card["hamiltonian"]:
        body.append(f'<div class="math">$${parse.esc(card["hamiltonian"])}$$</div>')
    if card["props"]:
        rows = "\n".join(
            f'<tr><td>{parse.md_inline(r["axis"])}</td>'
            f'<td>{parse.md_inline(r["value"])}</td>'
            f'<td>{parse.md_inline(r["note"])}</td></tr>'
            for r in card["props"])
        body.append(
            '<div class="tablewrap"><table class="bench">'
            '<thead><tr><th>Axis</th><th>Value</th><th>Note</th></tr></thead>\n'
            f'<tbody>\n{rows}\n</tbody></table></div>')
    body.append(parse.list_block("Phases & order parameters", card["phases"]))
    body.append(parse.list_block("Canonical observables", card["observables"]))
    body.append(parse.list_block("Recommended methods", card["methods"]))
    body.append(parse.list_block("Benchmarks", card["benchmarks"]))
    if card["keyref"]:
        body.append(f'<p class="solv">Key reference: {parse.md_inline(card["keyref"])}</p>')
    links = [f'<a href="{BLOB}{e["slug"]}/MODEL.md">MODEL.md&nbsp;&#8599;</a>']
    if card["solvable_slug"]:
        links.append('<a href="solvable.html">exact-solution oracle&nbsp;&#8599;</a>')
    body.append(f'<p class="cardlinks">{" ".join(links)}</p>')
    body_html = "\n".join(b for b in body if b)
    return (
        f'<details class="model" {_data_attrs(e)}>\n'
        f'<summary><span class="mname">{parse.esc(e["slug"])}</span>'
        f'<span class="hook">{parse.esc(e["hook"])}</span>{_badges(e)}</summary>\n'
        f'<div class="mbody">\n{body_html}\n</div>\n'
        f'</details>'
    )


def render(entries: list) -> str:
    """Render the full models.html page from build_entries entries."""
    total = len(entries)
    order, groups = [], {}
    for e in entries:
        code = e["family"]
        if code not in groups:
            order.append(code)
            groups[code] = {"title": e["family_title"], "rows": []}
        groups[code]["rows"].append(e)

    sections = []
    for code in order:
        g = groups[code]
        rows = "\n".join(_render_row(e) for e in g["rows"])
        sections.append(f'''<section class="tgroup" data-tech="{code}">
<h2><span class="tcode">{code}</span> {parse.esc(g["title"])}
<span class="scount" data-total="{len(g["rows"])}">{len(g["rows"])}</span></h2>
<p class="tsub">{parse.esc(FAMILY_SUBTITLES.get(code, ""))}</p>
{rows}
</section>''')
    sections_html = "\n\n".join(sections)

    family_titles = {c: groups[c]["title"] for c in order}
    used_methods = {m for e in entries for m in e["methods"]}
    method_vals = [t for t in METHOD_TOKENS if t in used_methods]
    chips_html = (
        f'<span class="cgroup"><span class="clabel">Family</span>'
        f'{shell.chips("family", order, family_titles)}</span>\n'
        f'<span class="cgroup"><span class="clabel">Sign problem</span>'
        f'{shell.chips("sign", ["sign-free", "sign-ful", "mixed", "n/a"], SIGN_TITLES)}</span>\n'
        f'<span class="cgroup"><span class="clabel">Method</span>'
        f'{shell.chips("method", method_vals)}</span>'
    )

    return shell.page(
        title="Widely-used models",
        lead=(f"The harness's model zoo: {total} canonical quantum lattice models, "
              "each with its Hamiltonian, a structured A1–D16 property table, "
              "phases, canonical observables, and the methods that work on it. "
              "Every row is generated from the model's knowledge-base card."),
        total=total,
        chips_html=chips_html,
        sections_html=sections_html,
        footer_html=(
            "<p>Sign chips: <b>sign-free</b> QMC works at scale &middot; "
            "<b>sign-ful</b> QMC blocked &middot; <b>mixed</b> depends on "
            "lattice/regime &middot; <b>n/a</b> not a QMC target. Cards live under "
            f'<a href="{BLOB}">.knowledge/models/</a>; exact-solution oracles '
            'are on the <a href="solvable.html">solvable catalog</a>.</p>'),
        here="models.html",
        search_placeholder="search models&hellip;",
    )


def build_page() -> str:
    return render(build_entries())
