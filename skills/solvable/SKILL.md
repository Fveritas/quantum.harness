---
name: solvable
user-invocable: false
description: |
  Use when the user wants a numerical result (ED / DMRG / QMC / VMC / any
  method) checked against an exact solution, or names a model from the
  solvable-models catalog in a verification context. Trigger phrases:
  "verify against the exact solution", "check my DMRG/ED/QMC result",
  "benchmark <method> on <model>", "is this energy right", "does this match
  the exact answer", "sanity-check this against Bethe ansatz / Onsager /
  free-fermion solution". Also fires when the user names any of the 63
  catalog models below in a verification context — not only when they use
  the word "verify":
  - T1 quadratic/free-particle: tfim-chain (TFIM), xy-chain, kitaev-chain,
    ssh-chain, kitaev-honeycomb, hofstadter-harper, haldane-chern,
    anderson-1d, harmonic-chain
  - T2 2D classical/transfer matrix: ising-2d-onsager (Onsager / 2D Ising),
    ising-triangular, dimer-kasteleyn, six-vertex, eight-vertex,
    hard-hexagons
  - T3 Bethe ansatz/Yang–Baxter: xxz-chain, heisenberg-xxx,
    hubbard-1d-lieb-wu (Lieb–Wu / 1D Hubbard), lieb-liniger, yang-gaudin,
    richardson-pairing, chiral-potts, kondo-bethe
  - T4 commuting projector/stabilizer: toric-code, color-code, x-cube,
    haah-code, cluster-spt
  - T5 frustration-free/exact eigenstates: aklt-chain, majumdar-ghosh,
    shastry-sutherland-dimer, rk-quantum-dimer, pxp-scars
  - T6 collective/large-N/random: lmg, dicke-tavis-cummings, quantum-rabi,
    syk, random-matrix-stats
  - T7 dualities & solvable dynamics: kramers-wannier (KW),
    dual-unitary-circuits, kicked-ising-floquet
  Full roster of 63 models: `.knowledge/solvable/INDEX.md`. Fires for each
  named model the user touches in a verification context, not just the
  first match.
---

# solvable dispatcher

Auto-triggered. The user does not type `/solvable`; the description above
fires the skill when their prose asks for a numerical result to be checked
against an exact solution, or names a solvable-catalog model in that
context.

## Audience definition (binding)

<audience>
The reader is a working physicist with no harness-internal context. They
want the verification verdict with embedded reasoning (what oracle, what
convention, what tolerance), not the agent's process. They do NOT know
harness vocabulary (ORACLE.md, S/P/T flag, tier). Every user-facing line is
anchored to this audience.
</audience>

## Workflow

1. **Match.** Resolve the user's prose to one canonical catalog slug via
   `.knowledge/solvable/INDEX.md`. Handle aliases (TFIM → `tfim-chain`,
   Onsager / 2D Ising → `ising-2d-onsager`, Lieb–Wu / 1D Hubbard →
   `hubbard-1d-lieb-wu`, KW → `kramers-wannier`, SIAM/Kondo →
   `anderson-impurity-bethe` or `kondo-bethe`, …). If the model isn't in the
   catalog, say so plainly rather than fabricating an oracle.

2. **Read the card.** `.knowledge/solvable/<slug>/ORACLE.md` is
   authoritative; agent memory is not. Work through the following checklist
   before comparing any numbers:

   <checklist name="card-read">
   - Hamiltonian and sign/normalization conventions read
   - Convention DICTIONARY built and reconciled against the user's
     convention BEFORE comparing numbers (Pauli `σ` vs spin-1/2 `S`,
     `J`/`Δ` sign and scale, PBC vs OBC) — a factor-of-4 Pauli-vs-`S` slip
     is the #1 way a correct numerical run looks "wrong"
   - Exact result(s) and their regime of validity noted (e.g. an XXZ
     formula pinned to `Δ>1` only, or a thermodynamic-limit value that a
     finite-`L` run only approaches)
   - Script flag noted: **S** full oracle script, **P** partial script +
     tabulated rest, **T** tabulated only, no script
   - Stated tolerance for the comparison noted
   </checklist>

3. **Execute.**
   - **S/P cards:** run the oracle from the catalog root —
     `cd .knowledge/solvable && uv run python <slug>/oracle.py --<params>`
     (use `--help` first if the parameter names aren't already known from
     the card). For P cards, only part of the card's claims are scriptable
     — the rest are read off the card's benchmark table.
   - **T cards:** no script exists; read the exact value directly off the
     card's benchmark table, matching the user's parameters exactly (size,
     coupling, convention) — do not extrapolate or interpolate values the
     card didn't tabulate.

4. **Compare.** Use the tolerance the card states (often `1e-8` for exact
   finite-size results, a stated percentage for finite-size ED brackets
   around a thermodynamic limit, or an explicit "upper bound, descends as
   `L→∞`" caveat). A user value outside a stated regime of validity is not
   a pass or a fail — say the comparison doesn't apply and point to the
   right regime.

5. **Report.** ≤3 lines: oracle value (with source line/params), user's
   deviation, pass/fail plus one-line reasoning. No harness jargon.

## Anti-patterns

<checklist name="anti-patterns">
- Comparing energies before reconciling the convention dictionary — fail. `σ` vs `S` alone is a factor of 4 per bond; silently "close enough" numbers are usually a convention mismatch, not a real deviation.
- Trusting agent memory ("XXZ ground energy at Δ=1 is about -0.44") over re-reading the card — fail. Memory drifts; cards don't.
- Quoting a closed form outside its stated regime (e.g. the XXZ `Δ>1` series at `Δ=0.5`, or a thermodynamic-limit value as if it were the finite-`L` answer) — fail.
- Treating a Tier-C card's exact-ground-state guarantee as full-spectrum exactness — fail. C-tier cards (AKLT, Majumdar–Ghosh, PXP scars, …) pin the ground state or a few eigenstates exactly; excited-state or dynamical claims outside that set are not covered.
</checklist>

<example name="convention-skip bad">
"Oracle says e0 = -0.443147, your DMRG got -1.7726 — that's way off, DMRG must be broken."
(Never checked whether the user ran Pauli `σ^aσ^a` instead of `S^aS^a`; -1.7726 ≈ 4 × -0.443147.)
</example>

<example name="convention-skip good">
"Card uses `S`-operators (`S=σ/2`); your code uses Pauli `σ^zσ^z`. Converting: oracle e0=-0.443147 in `S`-convention → -1.772588 in Pauli convention. Your DMRG got -1.77254 at L=100, PBC — deviation 4e-4, within the L=100 finite-size gap. Pass."
</example>

<example name="regime-violation bad">
"XXZ oracle at Δ=0.5 gives e0=-0.5432 (used the Δ>1 series formula)."
(The Δ>1 series doesn't apply at Δ=0.5 — gapless regime needs the integral formula instead.)
</example>

<example name="regime-violation good">
"Δ=0.5 is in the gapless regime (|Δ|<1); reading the integral-form e0 from oracle.py, not the Δ>1 series which doesn't apply here."
</example>
