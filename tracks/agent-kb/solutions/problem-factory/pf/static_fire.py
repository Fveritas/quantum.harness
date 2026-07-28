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


def check_sawtooth_flat_band():
    """One-magnon lowest band exactly flat at -4*J1 when J2=2*J1 (N=12)."""
    N = 12
    H = ed.sawtooth_hamiltonian(N, j2=2.0, j1=1.0, h=0.0, n_up=N - 1)
    w = np.linalg.eigvalsh(H.toarray())
    e_pol = (1.0 + 2 * 2.0) * (N // 2) / 4  # (j1 + 2*j2) * N_c / 4
    band = w[: N // 2] - e_pol
    spread = band.max() - band.min()
    return abs(band.mean() + 4.0) < 1e-8 and spread < 1e-8, \
        f"band mean={band.mean():.6f} (expect -4), spread={spread:.2e}"


def check_sawtooth_hsat_degeneracy():
    """Total GS degeneracy at h_sat=4*J1 equals Lucas(N/2); N=12 -> 18."""
    N = 12
    e0 = (1.0 + 2 * 2.0) * (N // 2) / 4 - 4.0 * N / 2
    total = 0
    for k in range(N // 2 + 1):
        H = ed.sawtooth_hamiltonian(N, j2=2.0, j1=1.0, h=4.0, n_up=N - k)
        w = np.linalg.eigvalsh(H.toarray())
        total += int(np.sum(np.abs(w - e0) < 1e-8))
    return total == 18, f"degeneracy={total} (expect Lucas(6)=18)"


CHECKS = {"bethe_delta1": check_bethe, "sz_conservation": check_sz_conservation,
          "sawtooth_flat_band": check_sawtooth_flat_band,
          "sawtooth_hsat_degeneracy": check_sawtooth_hsat_degeneracy}


def run(card):
    """Returns (ok, detail). Stops at the first failed check."""
    for name in card["static_fire"]:
        check = CHECKS[name]
        ok, detail = check(card["convention"]) if name == "bethe_delta1" else check()
        if not ok:
            return False, f"{name} failed: {detail}"
    return True, "all static-fire checks passed"
