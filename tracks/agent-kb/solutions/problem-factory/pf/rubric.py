"""Quality-class rubric: does a candidate belong to the #124-#128 class?

The hand-curated calibration set shares a fingerprint:
  1. literature_anchor  - a named target with a pinned published number + reference
  2. certificate_gate   - gate family is one of issue #133's machine-checkable kinds
  3. single_scalar      - one figure of merit with a push direction
  4. publishable_unit   - the improvement-over-SOTA statement that makes passing a paper

Presence of fields is only the structural layer. Whether the pinned number is
real and the checker actually runs is verified downstream (static fire / hop).
"""

import yaml

GATE_FAMILIES = {"certificate", "fresh_sample", "interval_arithmetic", "cost_arithmetic"}


def load(path):
    with open(path) as f:
        return yaml.safe_load(f)


def grade(c):
    checks = {
        "literature_anchor": bool(c["target"].get("pinned_number")) and bool(c["target"].get("reference")),
        "certificate_gate": c["gate"].get("family") in GATE_FAMILIES and bool(c["gate"].get("checker")),
        "single_scalar": bool(c["merit"].get("scalar")) and c["merit"].get("direction") in ("up", "down"),
        "publishable_unit": bool(c.get("publishable_unit")),
    }
    return {"accepted": all(checks.values()), "checks": checks}
