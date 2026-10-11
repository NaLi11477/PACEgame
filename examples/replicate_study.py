#!/usr/bin/env python3
"""Re-evaluate a supplied legacy claim inventory (source publication not supplied).

    python3 examples/replicate_study.py [outdir]

Regenerates the supplied inventory's Figures 3 to 9 from the repaired model, prints a table
of its twenty-six sub-claims with a verdict on each, and writes the same table
to ``study_replication.json`` so that a manuscript or a revision memo can quote
it without recomputing.  The figures need matplotlib; the table does not.

The repaired model is the supplied baseline with four primitives changed.  Three
were forced by the audit: the late entrant keeps its installed base, the
announcement accrues over the wait, and announcing is costly.  The fourth, a
readiness lag before the rival can deploy, is what gives a pioneer any monopoly
window at all -- without it a rival always enters at once and no first-mover
advantage can exist.
"""
from __future__ import annotations

import json
import os
import sys

try:
    import pacegame as pg
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pacegame as pg

from pacegame import plot
from pacegame.analyze import critical_value, derivative, equilibrium, sweep
from pacegame.solve import solve

#: the supplied inventory's numerical setting, plus the two coefficients the repairs add
POINT = {"sigma": 0.1, "phi": 0.85, "hatvarsigma": 0.3,
         "kappa_d": 0.05, "lambda": 0.1}

SIGMAS = [0.02 + 0.04 * i for i in range(13)]
GROWTHS = [0.1 + 0.05 * i for i in range(11)]
RULE = "=" * 78


def model():
    return pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                       signal_cost=True, entry_floor=True)


def strat(name):
    return next(s for s in pg.STANDARD_STRATEGIES if s.name == name)


def solutions_along(game, name, wrt, values):
    out = []
    for v in values:
        pt = dict(POINT, **{wrt: v})
        out.append(solve(game, strat(name), game.numeric(pt)))
    return out


# ------------------------------------------------------------------ figures
def figures(game, outdir):
    if not plot.available():
        print("matplotlib is not installed; skipping the figures")
        return []
    os.makedirs(outdir, exist_ok=True)
    written = []
    pairs = [("sigma", SIGMAS, "consumer growth rate"),
             ("hatvarsigma", GROWTHS, "rapid growth period")]

    for tag, subset, caption in [("3", ("RF", "RL"), "announcing"),
                                 ("4", ("DF", "DL"), "staying silent"),
                                 ("5", ("RF", "RL", "DF", "DL"), "all four")]:
        picked = [s for s in pg.STANDARD_STRATEGIES if s.name in subset]
        for panel, (wrt, values, label) in zip("ab", pairs):
            outs = sweep(game, wrt, values, POINT, strategies=picked)
            p = plot.payoff_sweep(values, outs, label,
                                  os.path.join(outdir, f"fig{tag}{panel}.png"),
                                  title=f"Optimal profit, {caption}")
            written.append(p)

    for tag, (wrt, values, label) in zip("67", pairs):
        series = {n: solutions_along(game, n, wrt, values) for n in ("RF", "RL")}
        written.append(plot.decision_map(
            values, series, label, "delta", os.path.join(outdir, f"fig{tag}.png"),
            title="Optimal announcement level"))

    for tag, (wrt, values, label) in zip("89", pairs):
        series = {n: solutions_along(game, n, wrt, values) for n in ("RL", "DL")}
        written.append(plot.decision_map(
            values, series, label, "varsigma", os.path.join(outdir, f"fig{tag}.png"),
            title="Optimal deployment time"))
    return written


# --------------------------------------------------------------- the claims
CLAIMS = [
    # (proposition, written form, target, wrt, quantity, claimed sign)
    ("P1(1)", "d delta*_RF / d growth", "RF", "hatvarsigma", "delta", "+"),
    ("P1(1)", "d pi_RF / d growth", "RF", "hatvarsigma", "payoff", "+"),
    ("P1(2)", "d delta*_RF / d sigma", "RF", "sigma", "delta", "-"),
    ("P1(2)", "d pi_RF / d sigma", "RF", "sigma", "payoff", "+"),
    ("P2(1)", "d delta*_RL / d growth", "RL", "hatvarsigma", "delta", "+"),
    ("P2(1)", "d pi_RL / d growth", "RL", "hatvarsigma", "payoff", "+"),
    ("P2(2)", "d delta*_RL / d sigma", "RL", "sigma", "delta", "+"),
    ("P2(2)", "d varsigma*_RL / d sigma", "RL", "sigma", "varsigma", "+"),
    ("P3", "d pi_DF / d growth", "DF", "hatvarsigma", "payoff", "+"),
    ("P3", "d pi_DF / d sigma", "DF", "sigma", "payoff", "+"),
    ("P4(1)", "d varsigma*_DL / d growth", "DL", "hatvarsigma", "varsigma", "+"),
    ("P4(1)", "d varsigma*_DL / d sigma", "DL", "sigma", "varsigma", "-"),
    ("P4(2)", "d pi_DL / d growth", "DL", "hatvarsigma", "payoff", "+"),
    ("P4(2)", "d pi_DL / d sigma", "DL", "sigma", "payoff", "-"),
    ("P5(2)", "d (pi_RL - pi_RF) / d sigma", ("RL", "RF"), "sigma", "payoff", "-"),
    ("P5(2)", "d (pi_RL - pi_RF) / d phi", ("RL", "RF"), "phi", "payoff", "-"),
    ("P5(3)", "d (pi_RL - pi_RF) / d growth", ("RL", "RF"), "hatvarsigma", "payoff", "+"),
    ("P6(2)", "d (pi_DF - pi_DL) / d sigma", ("DF", "DL"), "sigma", "payoff", "+"),
    ("P6(2)", "d (pi_DF - pi_DL) / d phi", ("DF", "DL"), "phi", "payoff", "+"),
    ("P6(3)", "d (pi_DF - pi_DL) / d growth", ("DF", "DL"), "hatvarsigma", "payoff", "+"),
    ("P7(2)", "d (pi_RL - pi_DF) / d sigma", ("RL", "DF"), "sigma", "payoff", "-"),
    ("P7(2)", "d (pi_RL - pi_DF) / d phi", ("RL", "DF"), "phi", "payoff", "-"),
    ("P7(3)", "d (pi_RL - pi_DF) / d growth", ("RL", "DF"), "hatvarsigma", "payoff", "+"),
]

RANKINGS = [("P5(1)", "pi_RL > pi_RF", "RL", "RF"),
            ("P6(1)", "pi_DF > pi_DL", "DF", "DL"),
            ("P7(1)", "pi_RL > pi_DF", "RL", "DF")]


def propositions(game):
    record = {"software_version": pg.__version__, "provenance": "supplied legacy inventory; no external publication verified", "point": dict(POINT), "rankings": [], "claims": []}
    print(RULE)
    print("The supplied claim inventory, recomputed at the constrained optimum")
    print(RULE)
    print(f"  {'prop':7s}{'claim':36s}{'claimed':>9s}{'found':>8s}"
          f"{'slope':>13s}   verdict")
    out = equilibrium(game, POINT)
    for tag, text, win, lose in RANKINGS:
        gap = out.payoffs[win] - out.payoffs[lose]
        ok = gap > 1e-12
        record["rankings"].append(dict(prop=tag, claim=text, gap=gap,
                                       verdict="holds" if ok else "FAILS"))
        print(f"  {tag:7s}{text:36s}{'>':>9s}{('>' if ok else '<='):>8s}"
              f"{gap:+13.7f}   {'holds' if ok else 'FAILS'}")
    agree = disagree = 0
    for tag, text, target, wrt, quantity, claimed in CLAIMS:
        r = derivative(game, target, wrt, POINT, quantity)
        found = r.sign
        ok = found == claimed
        agree += ok
        disagree += not ok
        verdict = "holds" if ok else ("flat" if found == "0" else "FAILS")
        record["claims"].append(dict(prop=tag, claim=text, claimed=claimed,
                                     found=found, slope=r.slope, verdict=verdict))
        print(f"  {tag:7s}{text:36s}{claimed:>9s}{found:>8s}"
              f"{r.slope:+13.6g}   {verdict}")
    print(f"  -> {agree} of {agree + disagree} sign claims reproduce")
    record["agree"], record["total"] = agree, agree + disagree

    cut = critical_value(game, "RL", "sigma", "phi", 0.05, 0.99, POINT)
    record["critical_phi"] = cut
    print()
    print("  P2(3) claims a critical network effect above which d pi_RL / d sigma")
    print(f"  turns negative. Searching phi in [0.05, 0.99]: "
          f"{'phi* = %.4f' % cut if cut else 'no strict crossing detected at this scan resolution'}")
    return record


def main(outdir="figures_study"):
    game = model()
    print(f"pacegame {pg.__version__}  -- re-evaluation of supplied claim inventory\n")
    print("  parameters: " + ", ".join(f"{k}={v:g}" for k, v in sorted(POINT.items())))
    out = equilibrium(game, POINT)
    print(f"  candidate ranking at that point: {out}\n")
    record = propositions(game)
    record["equilibrium"] = {k: float(v) for k, v in out.payoffs.items()}
    record["best"] = out.best
    record["version"] = pg.__version__
    os.makedirs(outdir, exist_ok=True)
    target = os.path.join(outdir, "study_replication.json")
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, allow_nan=False)
    print()
    print("  wrote", target)
    for p in figures(game, outdir):
        print("  wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "figures_study"))
