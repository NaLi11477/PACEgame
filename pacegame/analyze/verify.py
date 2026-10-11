"""Checking the claims a paper makes about its own model.

An analytical paper states its results as propositions: this derivative is
positive, that strategy dominates, this optimum is interior.  Each claim is a
statement about a region of the parameter space, and each is checkable.  This
module lets the claim be written down in the form the paper states it and then
tests it, reporting not just pass or fail but *where* it fails.

    from pacegame import models
    from pacegame.analyze import verify

    game = models.preannounce_entry()
    report = verify.check(game, [
        verify.Dominates("RL", "RF"),
        verify.Interior("varsigma", strategy="RL"),
        verify.Feasible(),
        verify.Sign("d pi_x / d sigma", ">", strategy="DF"),
    ], over={"sigma": (0.05, 0.6), "phi": (0.1, 0.95), "hatvarsigma": (0.1, 0.6)})
    print(report)
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

import sympy as sp
from ..core.numeric import exact_numeric, retained_exceeds

from ..core.game import STANDARD_STRATEGIES
from ..solve.engine import INTERIOR, solve

__all__ = ["Claim", "Sign", "Dominates", "Interior", "Feasible", "Bounded",
           "Competitive", "Result", "Report", "check", "grid"]


# ------------------------------------------------------------------- claims
class Claim:
    label: str = "claim"

    def evaluate(self, game, point, cache) -> tuple[bool, str]:
        raise NotImplementedError


@dataclass
class Sign(Claim):
    """A partial derivative of a payoff has a stated sign.

    The grammar is ``d pi_<player> / d <parameter>``. The player must be the
    game's current focal or rival name. Other numerators, including decisions,
    are rejected; use statics.derivative(quantity=...) for decision responses.
    ``strategy`` selects the constrained candidate where the payoff is read.
    """

    expr: str
    relation: str                  # ">" or "<"
    strategy: str = "RL"
    step: float = 1e-4
    #: slopes below this in absolute value are treated as flat, matching
    #: ``analyze.statics.Response.sign``; a flat response is a failure of a
    #: strict sign claim, but it is reported as flat rather than as a reversal.
    flat: float = 1e-10

    def __post_init__(self):
        import math
        if self.relation not in (">", "<"):
            raise ValueError("relation must be > or <")
        if not math.isfinite(self.step) or self.step <= 0:
            raise ValueError("step must be positive and finite")
        if not math.isfinite(self.flat) or self.flat < 0:
            raise ValueError("flat must be nonnegative and finite")
        target, name = self._parse()
        self.label = f"d {target} / d {name} {self.relation} 0  under {self.strategy}"

    def _parse(self):
        match = (re.fullmatch(r"\s*d\s+(pi_[^\s/]+)\s*/\s*d\s+([^\s/]+)\s*", self.expr)
                 if isinstance(self.expr, str) else None)
        if match is None:
            raise ValueError("Sign expects 'd pi_<player> / d <parameter>'")
        return match.groups()

    def validate(self, game):
        """Bind both sides before a sampled run can produce any verdict."""
        target, name = self._parse()
        if target not in (f"pi_{game.focal}", f"pi_{game.rival}"):
            raise ValueError(f"unknown payoff target {target!r}")
        if name not in game.parameters():
            raise ValueError(f"unknown derivative parameter {name!r}")
        if self.strategy not in {s.name for s in game.strategies}:
            raise ValueError(f"unknown strategy {self.strategy!r}")
        self.label = f"d {target} / d {name} {self.relation} 0  under {self.strategy}"
        return target, name

    def _wrt(self):
        return self._parse()[1]

    def evaluate(self, game, point, cache):
        target, name = self.validate(game)
        if name not in point:
            return None, f"{name} is not a swept parameter"
        from .statics import derivative
        slope = derivative(game, self.strategy, name, point,
                           quantity=target, step=self.step).slope
        import math
        if not math.isfinite(slope):
            raise ValueError("non-finite derivative: no sign verdict")
        if abs(slope) <= self.flat:
            return False, f"slope = {slope:+.4g} (flat: no response at all)"
        good = slope > 0 if self.relation == ">" else slope < 0
        return good, f"slope = {slope:+.4g}"


@dataclass
class Dominates(Claim):
    """One strategy yields the focal player more than another."""

    winner: str
    loser: str
    strict: bool = True

    def __post_init__(self):
        self.label = f"pi_{self.winner} {'>' if self.strict else '>='} pi_{self.loser}"

    def evaluate(self, game, point, cache):
        diverged = [n for n in (self.winner, self.loser)
                    if not cache.solution(game, n, point).rankable]
        if diverged:
            # Comparing a number that is whatever the search cap happened to be
            # would return a verdict on a point the model cannot produce. That
            # is the error this package exists to catch, so no verdict is given.
            return None, (f"{', '.join(diverged)} is unresolved or invalid, so the "
                          f"comparison has no verdict")
        a = cache.payoff(game, self.winner, point)
        b = cache.payoff(game, self.loser, point)
        if a is None or b is None:
            return None, "payoff not evaluable"
        from ..core.numeric import retained_difference, retained_exceeds
        gap = retained_difference(a, b)
        good = (retained_exceeds(a, b, 1e-12) if self.strict
                else not retained_exceeds(b, a, 1e-12))
        return good, f"gap = {float(gap):+.6g}"


@dataclass
class Interior(Claim):
    """A decision variable's optimum is interior rather than on a bound."""

    variable: str
    strategy: str = "RL"

    def __post_init__(self):
        self.label = f"{self.variable}* is interior under {self.strategy}"

    def evaluate(self, game, point, cache):
        sol = cache.solution(game, self.strategy, point)
        if sol is None:
            return None, "no solution"
        if not sol.rankable:
            return None, "candidate unresolved, invalid or required checks incomplete; no whole-candidate interior verdict"
        for var, kind in sol.kind.items():
            if str(var) == self.variable:
                return kind == INTERIOR, f"{kind} at {sp.N(sol.point[var], 4)}"
        return None, f"{self.variable} is not a decision variable here"


@dataclass
class Feasible(Claim):
    """Every strategy's optimum passes the feasibility checks."""

    strategies: tuple = ()

    def __post_init__(self):
        self.label = "all optima feasible"

    def evaluate(self, game, point, cache):
        names = self.strategies or tuple(
            s.name for s in getattr(game, "strategies", STANDARD_STRATEGIES))
        bad = []
        incomplete = []
        for n in names:
            sol = cache.solution(game, n, point)
            if sol is None or sol.feasibility is None:
                raise ValueError(f"{n}: no feasibility result")
            bad += [f"{n}: {v.detail}" for v in sol.feasibility.violations()]
            if not sol.feasibility.complete:
                incomplete.append(n)
        if not bad and incomplete:
            return None, f"required feasibility checks incomplete: {', '.join(incomplete)}"
        return (not bad), ("; ".join(bad[:2]) if bad else "no violations")


@dataclass
class Bounded(Claim):
    """No payoff exceeds what the model's own demand can produce."""

    strategy: str = "RL"

    def __post_init__(self):
        self.label = f"pi_{self.strategy} within the demand ceiling"

    def evaluate(self, game, point, cache):
        sol = cache.solution(game, self.strategy, point)
        if sol is None:
            return None, "not evaluable"
        if not sol.rankable:
            return None, "candidate unresolved or invalid"
        if game.ceiling_is_endogenous(sol.strategy):
            return None, "ceiling depends on an open decision variable"
        sub = cache.subs(game, point)
        at = dict(sub); at.update(sol.point)
        ceiling = game.demand_ceiling(sol.strategy, at)
        if ceiling is None:
            return None, "not evaluable"
        target = game.payoffs(sol.strategy)[game.focal]
        try:
            above = retained_exceeds(target, ceiling, 1e-12, at)
        except (ValueError, TypeError, ArithmeticError):
            return None, "retained ceiling comparison unavailable"
        gap = exact_numeric(target, at) - exact_numeric(ceiling, at)
        return not above, f"retained payoff minus ceiling {sp.N(gap, 6)}; absolute tolerance 1e-12"


@dataclass
class Competitive(Claim):
    """The share rule still affects the payoff at the optimum.

    ``Feasible`` reports violations only, so a model whose optimum has walked
    off the edge of its own competitive channel passes it.  That is the one
    finding in the report with no way into the verification layer unless it has
    a claim of its own, and a check a researcher cannot assert over a grid is a
    check that will not get used.
    """

    strategy: str = "RL"

    def __post_init__(self):
        self.label = f"the share rule is active under {self.strategy}"

    def evaluate(self, game, point, cache):
        sol = cache.solution(game, self.strategy, point)
        if sol is None or sol.feasibility is None:
            return None, "no solution"
        if not sol.rankable:
            # Same rule as Dominates: no verdict at a point the model cannot
            # produce. A new claim does not inherit that on its own.
            return None, (f"{self.strategy} has no optimum, so whether the "
                          f"share rule bites there has no meaning")
        note = [f for f in sol.feasibility.findings if f.check == "competition"]
        if not note:
            return None, "the model declares no share-rule parameters"
        return note[0].verdict, note[0].detail


# ------------------------------------------------------------------ results
@dataclass
class Result:
    claim: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    reasons: list = field(default_factory=list)
    counterexamples: list = field(default_factory=list)

    @property
    def holds(self) -> bool:
        return self.failed == 0 and self.errors == 0 and self.skipped == 0 and self.passed > 0

    @property
    def rate(self) -> float:
        total = self.passed + self.failed
        return self.passed / total if total else 0.0

    def __str__(self):
        total = self.passed + self.failed
        mark = "holds" if self.holds else ("ERROR" if self.errors else ("FAILS" if self.failed else "partial" if self.passed else "n/a"))
        line = f"  [{mark:5s}] {self.claim}  ({self.passed}/{total}; skipped={self.skipped}, errors={self.errors})"
        if self.counterexamples:
            p, why = self.counterexamples[0]
            pretty = ", ".join(f"{k}={v:g}" for k, v in p.items())
            line += f"\n           counterexample: {pretty}  ->  {why}"
            if len(self.counterexamples) > 1:
                line += f"  (+{len(self.counterexamples) - 1} more)"
        if self.reasons:
            line += f"\n           {self.reasons[0][1]}"
        return line


@dataclass
class Report:
    results: list = field(default_factory=list)
    points: int = 0

    @property
    def ok(self) -> bool:
        """No claim failed.  A claim that was skipped at every point is not a
        failure: it did not apply to this model, and reporting it as one turns
        an inapplicable claim into a false alarm in a script's exit code."""
        return not any(r.failed or r.errors for r in self.results)

    @property
    def complete(self) -> bool:
        return bool(self.results) and self.points > 0 and all(
            r.skipped == 0 and r.errors == 0 and
            r.passed + r.failed + r.skipped + r.errors == self.points
            for r in self.results)

    @property
    def inapplicable(self) -> list:
        return [r.claim for r in self.results if not r.failed and not r.passed and not r.errors]

    def __str__(self):
        head = (f"verification over {self.points} parameter points: "
                f"{'no claim fails' if self.ok else 'some claims fail'}")
        if self.ok and self.inapplicable:
            head += (f" ({len(self.inapplicable)} did not apply to this model)")
        head += f"; complete={self.complete}"
        return "\n".join([head] + [str(r) for r in self.results])

    def to_markdown(self) -> str:
        rows = ["| claim | holds | passed | failed | skipped | errors | evidence |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in self.results:
            evidence = r.counterexamples or r.reasons
            ce = str(evidence[0]) if evidence else ""
            rows.append(f"| {r.claim} | {'yes' if r.holds else 'no'} | {r.passed} "
                        f"| {r.failed} | {r.skipped} | {r.errors} | {ce} |")
        return "\n".join(rows)


# ------------------------------------------------------------------- engine
class _Cache:
    """Solutions are reused across claims at the same parameter point."""

    def __init__(self):
        self._sol = {}

    def subs(self, game, point):
        return game.numeric(point)

    def solution(self, game, strategy_name, point):
        key = (strategy_name, tuple(sorted(point.items())))
        if key not in self._sol:
            pool = getattr(game, "strategies", STANDARD_STRATEGIES)
            strat = next((s for s in pool if s.name == strategy_name), None)
            if strat is None:
                raise ValueError(f"unknown strategy {strategy_name!r}")
            self._sol[key] = solve(game, strat, self.subs(game, point))
        return self._sol[key]

    def payoff(self, game, strategy_name, point):
        sol = self.solution(game, strategy_name, point)
        if sol is None or not sol.rankable:
            return None
        try:
            return sol.payoff_value(game.focal)
        except Exception:
            return None


def grid(over: dict, n: int = 3) -> list:
    """Cartesian grid of parameter points from ``{name: (lo, hi)}`` ranges."""
    import math
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("n must be a positive integer")
    axes = []
    for name, spec in over.items():
        if isinstance(spec, (list, tuple)) and len(spec) == 2:
            lo, hi = spec
            vals = [lo + (hi - lo) * i / (n - 1) for i in range(n)] if n > 1 else [lo]
        else:
            vals = list(spec)
        if not vals or any(not math.isfinite(v) for v in vals):
            raise ValueError(f"grid axis {name} must be nonempty and finite")
        if isinstance(spec, (list, tuple)) and len(spec) == 2 and spec[0] > spec[1]:
            raise ValueError(f"grid axis {name} must be increasing")
        axes.append([(name, v) for v in vals])
    return [dict(combo) for combo in itertools.product(*axes)]


def check(game, claims, over: dict, n: int = 3, fixed: dict | None = None,
          max_counterexamples: int = 3) -> Report:
    """Test every claim at every point of the grid."""
    claims = tuple(claims)
    if not claims:
        raise ValueError("at least one claim is required")
    if not all(isinstance(c, Claim) for c in claims):
        raise TypeError("claims must contain Claim instances")
    for claim in claims:
        if isinstance(claim, Sign):
            claim.validate(game)
    unknown = set(over) - set(game.parameters())
    if unknown:
        raise ValueError(f"unknown grid parameters: {sorted(unknown)}")
    points = grid(over, n)
    if fixed:
        points = [dict(fixed, **p) for p in points]
    cache = _Cache()
    results = [Result(claim=c.label) for c in claims]
    for point in points:
        for claim, res in zip(claims, results):
            try:
                ok, why = claim.evaluate(game, point, cache)
            except Exception as exc:            # a claim must never crash a run
                res.errors += 1
                if len(res.reasons) < max_counterexamples:
                    res.reasons.append((dict(point), f"{type(exc).__name__}: {exc}"))
                continue
            if ok is None:
                res.skipped += 1
                if len(res.reasons) < max_counterexamples:
                    res.reasons.append((dict(point), why))
            elif ok:
                res.passed += 1
            else:
                res.failed += 1
                if len(res.counterexamples) < max_counterexamples:
                    res.counterexamples.append((dict(point), why))
    return Report(results=results, points=len(points))
