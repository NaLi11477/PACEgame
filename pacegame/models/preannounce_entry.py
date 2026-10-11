"""Preannouncement and entry timing on competing platforms.

The model a platform faces when a new technology arrives: announce the
deployment plan or stay silent, and deploy before or after the rival.  Users
arrive at a constant rate while the market grows, split between the platforms
according to their installed bases, and stop arriving once the market matures.

The supplied baseline specification is reproduced by ``preannounce_entry()`` with no
arguments.  The keyword arguments switch on the seven alternative primitives
discussed in ``docs/model.md``; each is one primitive, not a different model,
and every one of them defaults to off, so the no-argument call is the supplied baseline
model exactly:

    keep_stock      the late entrant carries its installed base into its own
                    demand rather than only into its share
    signal_accrues  the announcement builds a stock over the wait
    signal_cost     announcing is costly (quadratic)
    timing_cost     deploying into an immature market is costly
    entry_floor     the rival cannot deploy before a readiness lag, which is
                    what gives the pioneer a monopoly window to be first into
    rival_signals   the rival matches the announcement, so the channel is not
                    the focal player's alone
    signal_ceiling  a chosen exogenous signal bound sigma*horizon, retained
                    from the supplied variant; not a credibility certificate
"""
from __future__ import annotations

import sympy as sp

from ..core.game import Game
from ..core.lifecycle import TwoPhase
from ..core.share import Proportional

__all__ = ["symbols", "preannounce_entry", "BASELINE", "REPAIRED"]


def symbols():
    """The model's symbols, as a namespace."""
    return dict(
        sigma=sp.Symbol("sigma", positive=True),        # user arrival rate
        phi=sp.Symbol("phi", positive=True),            # network effect
        zeta=sp.Symbol("varsigma", nonnegative=True),   # deployment time
        zeta_hat=sp.Symbol("hatvarsigma", positive=True),  # growth period
        delta=sp.Symbol("delta", nonnegative=True),     # announcement level
        kappa_d=sp.Symbol("kappa_d", nonnegative=True),
        kappa_t=sp.Symbol("kappa_t", nonnegative=True),
        lag=sp.Symbol("lambda", nonnegative=True),   # technology readiness lag
    )


def preannounce_entry(keep_stock=False, signal_accrues=False,
                      signal_cost=False, timing_cost=False,
                      entry_floor=False, rival_signals=False,
                      signal_ceiling=False) -> Game:
    s = symbols()
    life = TwoPhase(sigma=s["sigma"], growth_end=s["zeta_hat"],
                    horizon=sp.Integer(1), keep_stock=keep_stock)
    share = Proportional(phi=s["phi"])
    return Game(
        lifecycle=life,
        share_rule=share,
        entry=s["zeta"],
        signal=s["delta"],
        signal_accrues=signal_accrues,
        signal_cost=s["kappa_d"] if signal_cost else sp.Integer(0),
        timing_cost=s["kappa_t"] if timing_cost else sp.Integer(0),
        entry_floor=s["lag"] if entry_floor else sp.Integer(0),
        rival_signals=rival_signals,
        # Retain the chosen exogenous variant bound, independently of the
        # cumulative-demand capacity used for payoff diagnostics.
        signal_ceiling=life.sigma * life.horizon if signal_ceiling else sp.oo,
    )


#: the numerical setting used for the figures of the supplied model
BASELINE = {"sigma": 0.1, "phi": 0.85, "hatvarsigma": 0.3,
            "kappa_d": 0.0, "kappa_t": 0.0}

REPAIRED = {"sigma": 0.1, "phi": 0.85, "hatvarsigma": 0.3,
            "kappa_d": 0.05, "kappa_t": 0.0}


def numeric(params: dict) -> dict:
    """Map a plain-string parameter dict onto the model's symbols."""
    s = symbols()
    by_name = {str(v): v for v in s.values()}
    return {by_name[k]: sp.Float(v) for k, v in params.items() if k in by_name}
