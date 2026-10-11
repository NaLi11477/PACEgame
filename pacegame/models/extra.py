"""Two further models, so that the framework is not a single-model abstraction.

``logistic_entry`` replaces both the demand path and the share rule: S-shaped
adoption on a clock of its own, users split by a logit, and no signalling at
all.  It exists to show that the solver sees nothing but segments and shares.

``asymmetric_quality`` keeps the preannouncement structure but lets the two
platforms differ in baseline quality.  The motivating study assumes the two are
equal "without loss of generality"; that is a testable claim rather than a
definition, and this model is how it gets tested.
"""
from __future__ import annotations

import sympy as sp

from ..core.game import Game, STANDARD_STRATEGIES
from ..core.lifecycle import Logistic, TwoPhase
from ..core.share import Logit, Proportional

__all__ = ["logistic_entry", "asymmetric_quality",
           "LOGISTIC_POINT", "ASYMMETRIC_POINT"]


def logistic_entry(timing_cost: bool = True) -> Game:
    """Pure entry timing into an S-shaped market, users split by a logit.

    No signal is available, so the only decision is when the follower deploys.
    With a cost of deploying into an immature market the trade-off is real:
    entering early buys share and costs money.
    """
    ceiling = sp.Symbol("kappa", positive=True)       # market size
    rate = sp.Symbol("rho", positive=True)            # adoption speed
    midpoint = sp.Symbol("tau", positive=True)        # inflection
    beta = sp.Symbol("beta", positive=True)           # logit sensitivity
    entry = sp.Symbol("varsigma", nonnegative=True)
    return Game(
        lifecycle=Logistic(ceiling=ceiling, rate=rate, midpoint=midpoint,
                           horizon=sp.Integer(1), keep_stock=True),
        share_rule=Logit(beta=beta),
        entry=entry,
        signal=sp.Symbol("delta", nonnegative=True),   # unused, kept uniform
        timing_cost=sp.Symbol("kappa_t", nonnegative=True) if timing_cost
        else sp.Integer(0),
        # no announcement channel exists here, so only the silent strategies
        strategies=tuple(s for s in STANDARD_STRATEGIES if not s.signals),
    )


LOGISTIC_POINT = {"kappa": 1.0, "rho": 8.0, "tau": 0.5, "beta": 1.2,
                  "kappa_t": 0.05}


def asymmetric_quality(omega: float | None = None, **repairs) -> Game:
    """Preannouncement and entry timing when the platforms differ in quality.

    ``omega`` is the rival's baseline quality relative to the focal platform's,
    which is fixed at 1.  ``omega = 1`` recovers the symmetric model; leaving it
    None keeps it symbolic so it can be swept.
    """
    sigma = sp.Symbol("sigma", positive=True)
    phi = sp.Symbol("phi", positive=True)
    growth_end = sp.Symbol("hatvarsigma", positive=True)
    entry = sp.Symbol("varsigma", nonnegative=True)
    signal = sp.Symbol("delta", nonnegative=True)
    w = sp.Float(omega) if omega is not None else sp.Symbol("omega", positive=True)
    return Game(
        lifecycle=TwoPhase(sigma=sigma, growth_end=growth_end,
                           horizon=sp.Integer(1),
                           keep_stock=repairs.get("keep_stock", True)),
        share_rule=Proportional(phi=phi, quality={"x": sp.Integer(1), "y": w}),
        entry=entry,
        signal=signal,
        signal_accrues=repairs.get("signal_accrues", True),
        signal_cost=(sp.Symbol("kappa_d", nonnegative=True)
                     if repairs.get("signal_cost", True) else sp.Integer(0)),
        timing_cost=(sp.Symbol("kappa_t", nonnegative=True)
                     if repairs.get("timing_cost", False) else sp.Integer(0)),
    )


ASYMMETRIC_POINT = {"sigma": 0.1, "phi": 0.85, "hatvarsigma": 0.3,
                    "kappa_d": 0.05, "omega": 1.0}
