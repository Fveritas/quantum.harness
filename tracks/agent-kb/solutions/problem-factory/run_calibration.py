#!/usr/bin/env python3
"""Calibration gate (issue #133): the rubric must accept the hand-curated
quality class (#124-#128) and reject candidates outside it. If it cannot
reconstruct the curated set, it is not trusted on new problems."""

import glob

from pf import rubric

POSITIVES = sorted(glob.glob("calibration/issue-*.yaml"))
NEGATIVES = sorted(glob.glob("calibration/neg-*.yaml"))


def main():
    rows, pos_ok, neg_ok = [], 0, 0
    for path in POSITIVES + NEGATIVES:
        c = rubric.load(path)
        g = rubric.grade(c)
        expect = path in POSITIVES
        correct = g["accepted"] == expect
        pos_ok += expect and correct
        neg_ok += (not expect) and correct
        failed = [k for k, v in g["checks"].items() if not v]
        rows.append((c["id"], expect, g["accepted"], correct, ", ".join(failed) or "-"))
        mark = "ok " if correct else "MISS"
        print(f"[{mark}] {c['id']:<28} expect={'accept' if expect else 'reject'} "
              f"got={'accept' if g['accepted'] else 'reject'}  failed: {rows[-1][4]}", flush=True)

    calibrated = pos_ok == len(POSITIVES) and neg_ok == len(NEGATIVES)
    summary = (f"calibration: {pos_ok}/{len(POSITIVES)} positives accepted, "
               f"{neg_ok}/{len(NEGATIVES)} negatives rejected -> "
               f"{'CALIBRATED' if calibrated else 'NOT CALIBRATED'}")
    print("\n" + summary)

    with open("results/calibration.md", "w") as f:
        f.write("# Calibration Gate Report\n\n" + summary + "\n\n")
        f.write("| candidate | expected | got | failed checks |\n|---|---|---|---|\n")
        for cid, expect, accepted, correct, failed in rows:
            f.write(f"| {cid} | {'accept' if expect else 'reject'} | "
                    f"{'accept' if accepted else 'reject'}{' (MISS)' if not correct else ''} | {failed} |\n")


if __name__ == "__main__":
    main()
