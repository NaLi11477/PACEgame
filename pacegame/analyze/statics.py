"""Comparative statics: the sign of a response, and where it changes.

A proposition of the form "profit rises in sigma" is a claim about the sign of a
derivative over a region, and a proposition of the form "there exists a critical
network effect phi* above which the sign reverses" is a claim that the region
splits in two.  Both are computed here from the constrained optimum, which
matters: differentiating the closed form instead gives the response of a point
the model may not even reach.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .equilibrium import equilibrium, _parameter, _interval
from ._crossing import scan_crossing
from ..core.numeric import retained_difference, binary64_real

__all__ = ["Response", "SignMap", "derivative", "sign_map", "critical_value"]

POSITIVE, NEGATIVE, FLAT = "+", "-", "0"


@dataclass
class Response:
    strategy: str
    wrt: str
    point: dict
    slope: float
    stencil: str = "central"

    @property
    def sign(self) -> str:
        import math
        if not math.isfinite(self.slope):
            raise ValueError("non-finite derivative: no sign verdict")
        if self.slope > 1e-10:
            return POSITIVE
        if self.slope < -1e-10:
            return NEGATIVE
        return FLAT

    @property
    def target(self) -> str:
        """What is being differentiated, written the way a proposition writes it."""
        return (self.strategy if "*[" in self.strategy or self.strategy.startswith("pi_")
                else f"pi_{self.strategy}")

    def __str__(self):
        where = ", ".join(f"{k}={v:g}" for k, v in sorted(self.point.items()))
        return (f"d {self.target} / d {self.wrt} = {self.slope:+.6g} "
                f"({self.sign}) at {where}")


@dataclass
class SignMap:
    strategy: str
    wrt: str
    responses: list = field(default_factory=list)

    @property
    def signs(self) -> set:
        return {r.sign for r in self.responses}

    @property
    def uniform(self) -> bool:
        return len(self.signs - {FLAT}) <= 1

    def where(self, sign: str) -> list:
        return [r.point for r in self.responses if r.sign == sign]

    @property
    def target(self) -> str:
        return (self.strategy if "*[" in self.strategy or self.strategy.startswith("pi_")
                else f"pi_{self.strategy}")

    def __str__(self):
        head = (f"d {self.target} / d {self.wrt} over "
                f"{len(self.responses)} points: ")
        if self.uniform:
            s = (self.signs - {FLAT}) or {FLAT}
            return head + f"uniformly {s.pop()}"
        counts = {s: sum(1 for r in self.responses if r.sign == s)
                  for s in sorted(self.signs)}
        body = ", ".join(f"{k}: {v}" for k, v in counts.items())
        return head + f"mixed ({body})"


def _read(game, outcome, strategy, quantity: str):
    """One number out of a solved outcome: a payoff, a gap, or a decision."""
    names = strategy if isinstance(strategy, (tuple, list)) else [strategy]
    if any(name not in outcome.rankable for name in names):
        raise ValueError("comparative statics require valid resolved candidates")
    if isinstance(strategy, (tuple, list)):
        win, lose = strategy
        return retained_difference(outcome.payoff_value(win), outcome.payoff_value(lose))
    if quantity == "payoff":
        return outcome.payoff_value(strategy)
    if quantity in (f"pi_{game.focal}", f"pi_{game.rival}"):
        return outcome.solutions[strategy].payoff_value(quantity[3:])
    sol = outcome.solutions[strategy]
    for sym, val in sol.point.items():
        if str(sym) == quantity:
            return float(val)
    raise KeyError(f"{quantity} is not a decision variable of strategy {strategy}")


def derivative(game, strategy, wrt: str, point: dict,
               quantity: str = "payoff", step: float = 1e-4) -> Response:
    """Response of a payoff, a payoff gap or a decision, at the constrained optimum.

    ``strategy`` is a name, or a pair ``(winner, loser)`` for the gap between
    two strategies. ``quantity`` is ``"payoff"`` (the focal payoff),
    ``"pi_<player>"`` for either current player's payoff, or the name of a
    decision variable. Payoff gaps require ``quantity="payoff"``. Sign claims
    deliberately accept payoff targets only; decisions retain this interface.

    The response is taken at the constrained optimum rather than by
    differentiating a closed form, which would give the response of a point the
    model may never reach.
    """
    import math
    _parameter(game, wrt)
    if isinstance(strategy, (tuple, list)) and quantity != "payoff":
        raise ValueError("payoff gaps require quantity='payoff'")
    if not math.isfinite(step) or step <= 0:
        raise ValueError("step must be positive and finite")
    base = point[wrt]
    h = max(abs(base) * step, step)
    lo, hi = dict(point), dict(point)
    lo[wrt], hi[wrt] = base - h, base + h
    # A central perturbation can leave a declared domain at a boundary.
    # Use a feasible one-sided difference there, and report the stencil.
    stencil = "central"
    try:
        game.numeric(lo)
    except ValueError:
        lo = dict(point)
        stencil = "forward"
    try:
        game.numeric(hi)
    except ValueError:
        hi = dict(point)
        stencil = "backward"
    denom = hi[wrt] - lo[wrt]
    if not math.isfinite(denom) or denom <= 0:
        raise ValueError("no feasible finite finite-difference stencil")
    pool = [s for s in game.strategies if s.name in
            (strategy if isinstance(strategy, (tuple, list)) else [strategy])]
    a = _read(game, equilibrium(game, lo, pool), strategy, quantity)
    b = _read(game, equilibrium(game, hi, pool), strategy, quantity)
    label = strategy if isinstance(strategy, str) else f"({strategy[0]}-{strategy[1]})"
    if quantity in (f"pi_{game.focal}", f"pi_{game.rival}"):
        label = f"{quantity}[{label}]"
    elif quantity != "payoff":
        label = f"{quantity}*[{label}]"
    numerator = retained_difference(b, a)
    # Subtract the constrained solutions first, including each one's parameters.
    # This does not replace backward induction with an unconstrained partial.
    binary64_real(numerator, "finite-difference numerator")
    denominator = retained_difference(hi[wrt], lo[wrt])
    slope = binary64_real(numerator / denominator,
                          "finite-difference slope; no sign verdict")
    return Response(strategy=label, wrt=wrt, point=dict(point),
                    slope=slope, stencil=stencil)


def sign_map(game, strategy, wrt: str, over: dict, fixed: dict,
             n: int = 5, quantity: str = "payoff") -> SignMap:
    """Sign of the response across a grid of the remaining parameters."""
    from .verify import grid
    label = strategy if isinstance(strategy, str) else f"({strategy[0]}-{strategy[1]})"
    if quantity in (f"pi_{game.focal}", f"pi_{game.rival}"):
        label = f"{quantity}[{label}]"
    elif quantity != "payoff":
        label = f"{quantity}*[{label}]"
    out = SignMap(strategy=label, wrt=wrt)
    for pt in grid(over, n):
        full = dict(fixed, **pt)
        if wrt not in full:
            raise KeyError(f"{wrt} must be fixed or swept to differentiate in it")
        out.responses.append(derivative(game, strategy, wrt, full, quantity))
    return out


def critical_value(game, strategy, wrt: str, along: str,
                   lo: float, hi: float, fixed: dict,
                   scan: int = 12, iters: int = 40, tol: float = 1e-12,
                   quantity: str = "payoff"):
    """Value of ``along`` at which the sign of d pi / d ``wrt`` reverses.

    Returns None when the sign never changes over ``[lo, hi]``.  This means no strict crossing was detected at this scan resolution. It
    is not an existence proof over the continuous interval.
    Sampled zeros bracketed by opposite signs are retained; a zero run returns
    a sampled representative rather than a unique boundary.
    """
    _parameter(game, along)
    _parameter(game, wrt)
    _interval(lo, hi, scan, iters)
    def slope(v):
        return derivative(game, strategy, wrt, dict(fixed, **{along: v}),
                          quantity).slope

    return scan_crossing(slope, lo, hi, scan, iters, tol)
