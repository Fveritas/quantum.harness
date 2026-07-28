"""First-principles checks. Any failure kills the card before the hop test."""

import numpy as np
import scipy.sparse as sp

from . import ed

BETHE_E_PER_SITE = 0.25 - np.log(2)  # -0.4431, Heisenberg PBC thermodynamic limit


def check_bethe(convention, tol=0.01):
    """E/N at L=10, delta=1, j2=0 vs Bethe ansatz (finite-size corrected)."""
    e_per_site = ed.low_spectrum(10, 1.0, 0.0, convention=convention)[0] / 10
    return abs(e_per_site - BETHE_E_PER_SITE) < tol, f"E/N={e_per_site:.6f} vs {BETHE_E_PER_SITE:.6f}"


def check_sz_conservation():
    """[H, Sz_tot] = 0 in the full basis of a small chain."""
    L = 4
    H = ed.hamiltonian(L, 1.0, 0.3)
    d = np.array([sum(0.5 if s >> i & 1 else -0.5 for i in range(L)) for s in range(1 << L)])
    comm = H @ sp.diags(d) - sp.diags(d) @ H
    norm = abs(comm).max()
    return norm < 1e-12, f"|[H,Sz]|={norm:.2e}"


CHECKS = {"bethe_delta1": check_bethe, "sz_conservation": check_sz_conservation}


def run(card):
    """Returns (ok, detail). Stops at the first failed check."""
    for name in card["static_fire"]:
        check = CHECKS[name]
        ok, detail = check(card["convention"]) if name == "bethe_delta1" else check()
        if not ok:
            return False, f"{name} failed: {detail}"
    return True, "all static-fire checks passed"
