#!/usr/bin/env python3
"""Write the figures for the built-in model, before and after the repairs.

    python3 examples/make_figures.py [outdir]

Needs matplotlib; everything else in the package does not.
"""
from __future__ import annotations

import os
import sys

try:
    import pacegame as pg
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pacegame as pg

from pacegame import plot
from pacegame.analyze import sign_map, sweep
from pacegame.solve import solve

REP = {"sigma": 0.1, "phi": 0.85, "hatvarsigma": 0.3, "kappa_d": 0.05}


def main(outdir="figures"):
    if not plot.available():
        print("matplotlib is not installed; nothing to draw")
        return 1
    os.makedirs(outdir, exist_ok=True)
    published = pg.models.preannounce_entry()
    repaired = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                           signal_cost=True)
    values = [0.05 + 0.05 * i for i in range(12)]

    a = plot.payoff_sweep(
        values, sweep(published, "hatvarsigma", values, REP), "growth period",
        os.path.join(outdir, "fig1_published.png"),
        title="Baseline: signalling search unresolved")
    b = plot.payoff_sweep(
        values, sweep(repaired, "hatvarsigma", values, REP), "growth period",
        os.path.join(outdir, "fig2_repaired.png"),
        title="Stock-cost variant: candidate payoffs")

    subs = {}
    for obj in (repaired.lifecycle, repaired.share_rule):
        for p in getattr(obj, "params", ()):
            subs[str(p)] = p
    import sympy as sp
    for sym in sp.sympify(repaired.signal_cost).free_symbols:
        subs[str(sym)] = sym
    sols = [solve(repaired, next(s for s in pg.STANDARD_STRATEGIES if s.name == "RL"),
                  {subs[k]: sp.Float(v) for k, v in dict(REP, hatvarsigma=z).items()
                   if k in subs})
            for z in values]
    c = plot.decision_map(values, sols, "growth period", "varsigma",
                          os.path.join(outdir, "fig3_timing.png"),
                          title="Deployment time, corners marked")

    maps = [sign_map(repaired, st, wrt, over={"phi": (0.3, 0.95)}, fixed=REP, n=5)
            for st, wrt in (("RL", "sigma"), ("DF", "sigma"),
                            ("RL", "hatvarsigma"), ("DF", "hatvarsigma"))]
    d = plot.sign_heatmap(maps, os.path.join(outdir, "fig4_signs.png"),
                          title="Response signs across the network effect")
    for p in (a, b, c, d):
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "figures"))
