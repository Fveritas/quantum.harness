# Problem Factory — a rocket-test approach to issue #133

**One command:** `python3 run_demo.py`

## The idea

Issue #133 asks for a factory that generates, solves, and publishes new quantum
many-body research problems. The hard part is not generating problems — it is
judging them. Multi-agent debate about "which problem is good" drifts into
plausible-sounding vagueness, so this factory does not let agents judge at all.
**Problems are judged by experiments**, the way SpaceX judges rockets:

| rocket test | problem factory |
|---|---|
| success criteria frozen before launch | gate frozen in the card before any solve |
| static fire | first-principles checks: Bethe-ansatz energy, [H, Sz] = 0 |
| hop test | small-size ED grid over the declared parameters |
| telemetry or it didn't happen | one machine-readable JSON per card |
| explosion is data | every dead card is recorded with a root cause |

The demo launches 5 cards and shows the factory has teeth in both directions:

```
launched 5: survivor 1, deferred 1, dead 3
  xxz-j2-gap-001       survivor  — J2=0.3 shifts the gap 5.5σ above finite-size noise
  xxz-j2-deferred-004  deferred  — J2=0.05 visible (0.93) but indecisive: launch bigger
  xxz-j2-tiny-002      dead      — no_signal: J2=0.001 invisible at these sizes
  xxz-bad-setup-003    dead      — setup_error: pauli/spin convention mix-up caught
                                   by the Bethe oracle (E/N off by 4×)
  xxz-j2-gap-001-dup   dead      — duplicate_fingerprint
```

Three distinct death causes, each detected by a different mechanism — that is
the deliverable, not the one survivor.

## Layout

- `pf/ed.py` — minimal XXZ+J2 exact diagonalization (Sz=0 sector, scipy, ~50 lines)
- `pf/cards.py` — template-generated demo cards + fingerprint dedup (interface A)
- `pf/static_fire.py` — first-principles checks (Bethe E/N at Δ=1, Sz conservation)
- `pf/probe.py` — hop test: full (L, Δ, J2) grid, decisiveness vs finite-size noise
- `pf/verdict.py` — three-state verdict + battle report (`results/report.md`)
- `AGENTS.md` — card schema, telemetry schema, coding style for agent sessions

## Key design decisions

1. **Gate-first.** A card without a frozen, executable gate never enters the
   pipeline. Gates are declared per card (`gate.kill_if`), never edited after launch.
2. **Decisiveness, not discussion.** The quality metric is
   |gap(J2) − gap(J2=0)| measured against the baseline's own finite-size noise.
   No agent opinion appears anywhere in the verdict path.
3. **Deferred is a first-class verdict.** Signals that are visible but
   indecisive at small sizes are not killed and not passed — they go back to
   the human with a "launch bigger" recommendation. (One lesson already learned:
   in a gapless phase both the gap and its perturbation shrink as 1/L, so a
   raw "effect must grow with L" criterion is wrong for gap observables.)
4. **Failures are assets.** `results/telemetry.jsonl` + the mishap review are
   the seed of the heuristic library issue #133 asks for.

## Next steps (Day 2+)

- Scale hop tests to the cluster via `scripts/harness_array_sbatch.sh`
  (L=12–16, more Δ/J2 points) for deferred cards.
- Replace `pf/cards.py` templates with an LLM generator behind the same schema
  (interface A is the contract; the generator is swappable).
- Turn repeated death causes into heuristic-library entries.
