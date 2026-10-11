"""Comparing strategies, and finding where a comparison turns over.

Two things a paper does by hand after it has solved each strategy separately:
rank them to find the equilibrium, and differentiate the ranking to see which
parameter flips it.  Both are mechanical once the solutions exist.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ._crossing import scan_crossing

from ..core.game import STANDARD_STRATEGIES, Strategy
from ..solve.engine import solve
from ..core.numeric import (finite_real, retained_difference, retained_exceeds,
                            binary64_real)

__all__ = ["Outcome", "rank_strategies", "equilibrium", "sweep", "threshold"]


@dataclass
class Outcome:
    point: dict
    payoffs: dict = field(default_factory=dict)
    solutions: dict = field(default_factory=dict)
    #: the payoff the *other* player receives under each label. The rival's
    #: role is fixed by the focal player's choice, so this is what says whether
    #: the ranking is a profile both players would sit still in.
    rival_payoffs: dict = field(default_factory=dict)
    #: per strategy, whether the two players are interchangeable under it,
    #: which decides whether :meth:`role_conflict` means anything
    alike: dict = field(default_factory=dict)
    retained_payoffs: dict = field(default_factory=dict)
    retained_rival_payoffs: dict = field(default_factory=dict)

    def payoff_value(self, name):
        """Retained focal payoff, with a fallback for legacy manual outcomes."""
        return finite_real(self.retained_payoffs.get(name, self.payoffs[name]))

    @property
    def symmetric(self) -> bool:
        return self.alike.get(self.best, True)

    @property
    def best(self) -> str | None:
        """Best valid numerical candidate; None when none are rankable."""
        best = None
        for name in self.rankable:
            value = self.payoff_value(name)
            if best is None or retained_exceeds(value,
                                               self.payoff_value(best)):
                best = name
        return best

    @property
    def unbounded(self) -> list:
        return sorted(n for n, s in self.solutions.items() if s.unbounded)

    @property
    def excluded(self) -> list:
        return sorted(k for k in self.payoffs if k not in self.rankable)

    @property
    def complete(self) -> bool:
        try:
            return not self.excluded and bool(self.payoffs) and self.best is not None
        except (TypeError, ValueError, ArithmeticError):
            return False

    @property
    def rankable(self) -> list:
        return sorted(k for k, sol in self.solutions.items()
                      if sol.rankable and math.isfinite(self.payoffs[k]))

    def ties(self, tol: float = 1e-9) -> list:
        if self.best is None:
            return []
        top = self.payoff_value(self.best)
        return sorted(k for k in self.rankable
                      if not retained_exceeds(abs(retained_difference(
                          self.payoff_value(k), top)), 0, tol))

    def role_conflict(self, tol: float = 1e-12):
        """Descriptive payoff gap for interchangeable silent players.

        This is not a unilateral deviation test or a Nash certificate.
        """
        best = self.best
        if best is None or not self.alike.get(best, False):
            return None
        theirs = self.rival_payoffs.get(best)
        if theirs is None or not math.isfinite(theirs):
            return None
        theirs = self.retained_rival_payoffs.get(best, theirs)
        gap = retained_difference(self.payoff_value(best), theirs)
        return binary64_real(gap, "role payoff gap") if retained_exceeds(gap, 0) else 0.0

    def __str__(self):
        body = "  ".join(f"{k}={v:.6g}" for k, v in sorted(self.payoffs.items()))
        if self.best is None:
            return f"{body}   -> no ranking: no valid resolved candidates"
        tie = self.ties()
        label = self.best if len(tie) == 1 else f"tie({', '.join(tie)})"
        note = f"; excluded: {', '.join(self.excluded)}" if self.excluded else ""
        return f"{body}   -> candidate ranking: {label}{note} [not Nash-certified]"


def _subs(game, point):
    return game.numeric(point)


def _strategies(game, strategies):
    admitted = tuple(getattr(game, "strategies", STANDARD_STRATEGIES))
    selected = admitted if strategies is None else tuple(strategies)
    if not selected:
        raise ValueError("strategies must be nonempty and have unique names")
    if not all(isinstance(s, Strategy) for s in selected):
        raise ValueError("strategies must contain admitted Strategy instances")
    if len({s.name for s in selected}) != len(selected):
        raise ValueError("strategies must be nonempty and have unique names")
    if any(s not in admitted for s in selected):
        raise ValueError("strategy is not admitted by this game")
    return selected


def rank_strategies(game, point: dict, strategies=None) -> Outcome:
    """Solve and rank a nonempty, unique iterable of admitted strategies."""
    strategies = _strategies(game, strategies)
    subs = _subs(game, point)
    out = Outcome(point=dict(point))
    for st in strategies:
        sol = solve(game, st, subs)
        out.solutions[st.name] = sol
        out.payoffs[st.name] = float(sol.payoffs[game.focal])
        out.rival_payoffs[st.name] = float(sol.payoffs[game.rival])
        out.retained_payoffs[st.name] = sol.retained_payoffs.get(game.focal, sol.payoffs[game.focal])
        out.retained_rival_payoffs[st.name] = sol.retained_payoffs.get(game.rival, sol.payoffs[game.rival])
        out.alike[st.name] = game.players_alike(st)
    return out


def equilibrium(game, point: dict, strategies=None) -> Outcome:
    """Compatibility alias for rank_strategies; does not compute a Nash game."""
    return rank_strategies(game, point, strategies)


def _parameter(game, name):
    if name not in game.parameters():
        raise ValueError(f"{name!r} is not a parameter of this model")


def _interval(lo, hi, scan, iters):
    if (not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi
            or not isinstance(scan, int) or scan < 1
            or isinstance(scan, bool) or isinstance(iters, bool)
            or not isinstance(iters, int) or iters < 1):
        raise ValueError("finite lo < hi and positive integer scan/iters required")


def sweep(game, name: str, values, fixed: dict, strategies=None) -> list:
    """Candidate rankings as a parameter moves; consume the strategy pool once.

    Empty values return []; the strategy pool is still validated before search.
    """
    _parameter(game, name)
    strategies = _strategies(game, strategies)
    return [equilibrium(game, dict(fixed, **{name: v}), strategies)
            for v in values]


def threshold(game, name: str, lo: float, hi: float, fixed: dict,
              winner: str, loser: str, scan: int = 12, iters: int = 50,
              tol: float = 1e-12):
    """Find the parameter value where two strategies swap rank.

    A coarse scan brackets a strict sign change first, then bisection refines it.
    A sampled zero between opposing nonzero signs is retained. For a sampled
    zero run, returns one sampled representative, not a unique plateau boundary.
    Scanning before bisecting matters because two strategies often *tie* over a
    whole region -- a corner solution makes them the same outcome -- and an
    endpoint tie is not a crossing.  Returns None when the ranking never
    strictly reverses, which means no crossing was detected at the sampled resolution; it
    does not prove that no crossing exists between sample points.
    """
    _parameter(game, name)
    _interval(lo, hi, scan, iters)
    def gap(v):
        o = equilibrium(game, dict(fixed, **{name: v}),
                        [s for s in getattr(game, "strategies", STANDARD_STRATEGIES)
                         if s.name in (winner, loser)])
        if winner not in o.rankable or loser not in o.rankable:
            raise ValueError("threshold requires valid resolved candidates")
        return retained_difference(o.payoff_value(winner), o.payoff_value(loser))

    return scan_crossing(gap, lo, hi, scan, iters, tol)
