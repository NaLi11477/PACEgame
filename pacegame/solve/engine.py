"""Backward induction, symbolically where possible and numerically otherwise.

``solve`` walks the game's decision order from the last mover back to the first.
Each stage maximises that mover's payoff while the stages below it respond, so a
leader's objective is evaluated along the follower's reaction rather than at
fixed values -- which is what backward induction means and what a naive
substitution gets wrong.

Two properties of the answer matter as much as the answer itself.  A payoff that
is monotone on the feasible set has no stationary point, and reporting the root
of its derivative anyway is the most common way an entry-timing model goes
wrong; every candidate is therefore labelled interior, cornered or search-limited.  And
a closed form is only useful once it is known to be feasible, so the numeric
path runs regardless and the symbolic root is carried alongside for comparison.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from .feasible import FAIL, OK, WARN, FeasibilityReport, Finding, check_point, _bound_tolerance
from ._domains import retained_interval, require_distinguishable, exact_numeric
from ..core.numeric import finite_real

__all__ = ["Solution", "solve", "solve_symbolic",
           "INTERIOR", "LOWER", "UPPER", "FIXED", "UNBOUNDED", "SEARCH_LIMIT"]

INTERIOR = "interior"
LOWER = "lower corner"
UPPER = "upper corner"
FIXED = "fixed"
UNBOUNDED = "unbounded"
SEARCH_LIMIT = "search limit"

_SIGNAL_CAP = 1e6
#: share of search points that may fail to evaluate before the optimum stops
#: being a statement about the declared domain
_EVAL_FAILURE_LIMIT = 0.02
#: below this many evaluations a rate says nothing; the non-optimising player
#: is evaluated once, and a percentage on one sample is noise dressed as data
_EVAL_MIN_SAMPLE = 10
#: a route that fails is skipped for this many calls before being tried again,
#: which bounds the cost of a persistent failure to one exception per this many
#: points and the cost of a transient one to this many points of a slower route
_RETRY_AFTER = 32


@dataclass
class Solution:
    strategy: object
    point: dict = field(default_factory=dict)        # symbol -> optimal value
    payoffs: dict = field(default_factory=dict)      # player -> payoff there
    kind: dict = field(default_factory=dict)         # symbol -> INTERIOR/...
    method: str = ""
    feasibility: FeasibilityReport | None = None
    stationary: dict = field(default_factory=dict)   # unconstrained roots
    #: Final symbolic values with this solution's parameters and candidate bound.
    #: Float payoffs remain the compatibility/display values, not comparison inputs.
    retained_payoffs: dict = field(default_factory=dict)

    def payoff_value(self, player):
        """Finite-real retained payoff; legacy manually built solutions fall back."""
        return finite_real(self.retained_payoffs.get(player, self.payoffs[player]))

    @property
    def unbounded(self) -> bool:
        return UNBOUNDED in self.kind.values()

    @property
    def unresolved(self) -> bool:
        return SEARCH_LIMIT in self.kind.values() or self.unbounded

    @property
    def rankable(self) -> bool:
        import math
        return (not self.unresolved and bool(self.payoffs)
                and all(math.isfinite(v) for v in self.payoffs.values())
                and self.feasibility is not None and self.feasibility.ok
                and self.feasibility.complete)

    def __str__(self):
        bits = ", ".join(f"{k}*={float(v):.4g} ({self.kind.get(k, '?')})"
                         for k, v in self.point.items())
        pay = ", ".join(f"pi_{j}={float(v):.6g}" for j, v in self.payoffs.items())
        return f"<{self.strategy} {bits} | {pay}>"


# ------------------------------------------------------------------ helpers
class _Evaluator:
    """Float evaluation of one payoff, escalating per point rather than once.

    ``lambdify`` compiles against ``math``, whose ``exp`` overflows where an
    expression is merely written awkwardly: a payoff assembled over a logistic
    path arrives as one fraction whose numerator and denominator each leave the
    float range while their quotient is ordinary.  Three routes are available --
    the compiled form, the same expression cancelled, then SymPy's own
    evaluation, which is slow but cannot overflow.

    0.1.5 chose between them once, from two probe points inside the box.  A
    form that is finite at the probes and overflows at the optimum then never
    escalated: the search saw None, treated the point as not better, and
    returned the best of whatever it could evaluate.

    0.1.6 escalated per call but kept the rescuing route afterwards, on the
    reasoning that a form failing once will fail again.  That was a guess
    written as a decision: one bad point early in a grid moved every later
    point onto SymPy and roughly doubled a solve.  0.1.7 retried the cheapest
    route on every call instead, on the reasoning that a failure costs one
    caught exception -- also a guess, and measurement put it at thirty times
    for an expression the compiled form can never evaluate, because the
    exception is then paid at every point.

    Both were right about one case and wrong about the other: a persistent
    failure wants the route remembered, a transient one wants it retried.  A
    route that fails is therefore skipped for the next ``_RETRY_AFTER`` calls
    and then tried again, which costs one exception per that many points and
    recovers within that many if the failure was local.  Two counts are kept,
    because they mean different things.  A *rescue*
    is a point the compiled form could not evaluate and a slower route could:
    the optimum is still over the whole domain, but the expression is fragile
    and the reader should know.  A *failure* is a point no route could
    evaluate: those are skipped as "not better", so the optimum is over a
    subset and the count is the only evidence of it.
    """

    ROUTES = ("direct", "cancelled", "exact")

    def __init__(self, expr, variables, cancellation_source=None, params=None):
        self.expr = exact_numeric(expr)
        # Cancel before numerical parameter substitution. Binary rationals can
        # introduce large polynomial coefficients and pathological integer
        # GCD work in otherwise ordinary Logistic payoffs. Both forms still
        # retain every supplied Float before their arithmetic.
        self._cancellation_source = cancellation_source
        self._params = params
        self.variables = tuple(variables)
        self.calls = 0
        self.failures = 0
        self.rescues = 0
        self.routes_used = set()
        self.retries = 0
        self._fns = {}
        self._skip = [0] * len(self.ROUTES)

    @property
    def route_name(self) -> str:
        """The slowest route any point has needed."""
        if not self.routes_used:
            return self.ROUTES[0]
        return self.ROUTES[max(self.routes_used)]

    def _fn(self, index):
        if index not in self._fns:
            name = self.ROUTES[index]
            if name == "exact":
                expr, variables = self.expr, self.variables

                def exact(*args):
                    point = {v: a for v, a in zip(variables, args)}
                    return float(sp.N(exact_numeric(expr, point), 80))

                self._fns[index] = exact
            else:
                try:
                    if name == "direct":
                        form = self.expr
                    elif self._cancellation_source is None:
                        form = sp.cancel(self.expr)
                    else:
                        form = exact_numeric(sp.cancel(exact_numeric(self._cancellation_source)), self._params)
                    self._fns[index] = sp.lambdify(self.variables, form, "math")
                except Exception:
                    self._fns[index] = None
        return self._fns[index]

    def __call__(self, *args):
        self.calls += 1
        for index in range(len(self.ROUTES)):
            if index < 2 and self._skip[index] > 0:
                self._skip[index] -= 1
                continue
            fn = self._fn(index)
            if fn is None:
                self._skip[index] = _RETRY_AFTER
                continue
            try:
                value = fn(*args)
            except Exception:
                value = None
            if _finite(value):
                self.routes_used.add(index)
                if index > 0:
                    self.rescues += 1
                return float(value)
            if self._skip[index] == 0:
                self.retries += 1
            self._skip[index] = _RETRY_AFTER
        self.failures += 1
        return None

    @property
    def failure_rate(self) -> float:
        return self.failures / self.calls if self.calls else 0.0

    @property
    def rescue_rate(self) -> float:
        return self.rescues / self.calls if self.calls else 0.0


def _finite(v):
    import math
    try:
        return v is not None and math.isfinite(v)
    except (TypeError, ValueError, OverflowError):
        return False



def _safe(fn, x, star=False):
    try:
        v = fn(*x) if star else fn(x)
    except Exception:
        return None
    return v if _finite(v) else None


def _golden(fn, a, b, iters=70):
    """Maximise a unimodal fn on [a, b]; fn returns None where undefined."""
    gr = (5 ** 0.5 - 1) / 2
    for _ in range(iters):
        c, d = b - gr * (b - a), a + gr * (b - a)
        fc, fd = _safe(fn, c), _safe(fn, d)
        if fc is None or fd is None:
            break
        if fc < fd:
            a = c
        else:
            b = d
    return (a + b) / 2


def _max_1d(fn, lo, hi, grid=81):
    """Maximise on [lo, hi] by grid scan plus refinement, corners included."""
    if hi == lo:
        return lo, _safe(fn, lo)
    best_x, best_v = lo, _safe(fn, lo)
    for i in range(grid + 1):
        x = lo + (hi - lo) * i / grid
        v = _safe(fn, x)
        if v is None:
            continue
        if best_v is None or v > best_v:
            best_x, best_v = x, v
    step = (hi - lo) / grid if grid else 0.0
    a, b = max(lo, best_x - step), min(hi, best_x + step)
    if b > a:
        x = _golden(fn, a, b)
        v = _safe(fn, x)
        if v is not None and (best_v is None or v > best_v):
            best_x, best_v = x, v
    return best_x, best_v


def _grid_points(lo, hi, n):
    """Candidate values on [lo, hi]; geometric once the range is wide.

    A variable the model leaves unbounded can have a search range spanning six
    orders of magnitude, where a linear grid wastes every point at the top end.
    """
    if hi <= lo:
        return [lo]
    if hi - lo > 100:
        span = hi - lo
        out = [lo]
        for i in range(1, n):
            out.append(lo + span * (i / (n - 1)) ** 4)
        return out
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def _max_nd(objective, variables, boxes, n=21, passes=3):
    """Maximise over several variables: coarse product grid, then refinement.

    Coordinate ascent alone is not enough here.  When a signal only pays off if
    the player also waits, and waiting only pays off if it has signalled, every
    single-coordinate step from the origin looks flat and the search stops at a
    point that is not the optimum.  The product grid steps over that trap.
    """
    fixed = {v: boxes[v][0] for v in variables if boxes[v][0] == boxes[v][1]}
    if fixed:
        active = [v for v in variables if v not in fixed]
        if not active:
            return fixed, objective(fixed)
        chosen, value = _max_nd(lambda vals: objective({**fixed, **vals}),
                                active, boxes, n, passes)
        return {**fixed, **chosen}, value
    cand = {v: _grid_points(*boxes[v], n) for v in variables}
    best, best_v = {v: cand[v][0] for v in variables}, None
    if len(variables) == 1:
        v = variables[0]
        x, val = _max_1d(lambda t: objective({v: t}), *boxes[v])
        return {v: x}, val
    import itertools
    for combo in itertools.product(*(cand[v] for v in variables)):
        vals = dict(zip(variables, combo))
        out = objective(vals)
        if out is None:
            continue
        if best_v is None or out > best_v:
            best, best_v = vals, out
    for _ in range(passes):
        for v in variables:
            lo, hi = boxes[v]
            x, val = _max_1d(lambda t: objective({**best, v: t}), lo, hi)
            if val is not None and (best_v is None or val >= best_v):
                best, best_v = {**best, v: x}, val
    return best, best_v


def _find_cap(fn, lo, cap=_SIGNAL_CAP, start=1.0):
    """Upper search bound for a variable the model leaves unbounded.

    Doubling supplies a finite heuristic search box. Exhaustion means only
    that a computational budget was reached while the sampled payoff improved.
    It proves neither an infinite payoff nor absence of a finite maximizer;
    a finite asymptote can produce the same observations.

    Returns (bound, exhausted). This probe can also miss separated maxima,
    so a non-exhausted box is not a global search certificate.
    """
    x, best = start, _safe(fn, lo)
    while x < cap:
        v = _safe(fn, lo + x)
        if v is None:
            return lo + x, False
        if best is not None and v <= best + 1e-14:
            return lo + x, False
        best = v
        x *= 2
    return lo + cap, True


# ------------------------------------------------------------------ solvers
def solve_symbolic(game, strategy):
    """Closed-form stationary points, stage by stage. Returns None if unavailable."""
    contract = getattr(game, "validate_contract", None)
    if contract is not None:
        contract()
    payoffs = game.payoffs(strategy)
    order = game.decision_order(strategy)
    found = {}
    for player, variables in reversed(order):
        expr = exact_numeric(payoffs[player], found)
        for var in variables:
            try:
                roots = sp.solve(sp.Eq(sp.diff(expr, var), 0), var, dict=False)
            except Exception:
                return None
            real = [r for r in roots if not r.has(sp.I)]
            if not real:
                return None
            found[var] = sp.simplify(real[-1])
            expr = expr.subs(var, found[var])
    return found


def solve(game, strategy, params: dict, method: str = "numeric",
          signal_cap: float = _SIGNAL_CAP) -> Solution:
    """Numerical candidate for one admitted strategy and parameter point."""
    import math
    if method not in ("numeric", "auto", "symbolic"):
        raise ValueError("method must be numeric, auto or symbolic")
    if not math.isfinite(signal_cap) or signal_cap <= 0:
        raise ValueError("signal_cap must be positive and finite")
    if not game.admits(strategy):
        raise ValueError(f"strategy {strategy!r} is not admitted by the model")
    contract = getattr(game, "validate_contract", None)
    if contract is not None:
        contract()
    game.validate(params)
    # Both come from the game, which memoises them, so asking twice is free.
    # Assembling the net payoff here instead would be faster still and would
    # silently ignore a subclass that overrides payoffs(), which is an
    # extension point.
    payoffs = game.payoffs(strategy)
    gross = game.gross_payoffs(strategy)
    bounds = game.bounds(strategy)
    order = game.decision_order(strategy)          # outermost mover first
    decision_vars = [v for _, vs in order for v in vs]
    fns = {p: _Evaluator(exact_numeric(e, params), decision_vars,
                         cancellation_source=e, params=params)
           for p, e in payoffs.items()}

    def bound_of(var):
        lo, hi = bounds.get(var, (sp.Integer(0), sp.oo))
        try:
            lower, upper, relation = retained_interval(lo, hi, params)
            lo_n = float(sp.N(lower))
            hi_n = None if upper == sp.oo else float(sp.N(upper))
        except (TypeError, ValueError):
            raise ValueError(f"bounds for {var} must be independent numeric expressions") from None
        if relation == "reversed":
            raise ValueError(f"invalid independent bounds for {var}: lower bound exceeds upper bound")
        if (not math.isfinite(lo_n) or (hi_n is not None and
                (not math.isfinite(hi_n) or hi_n < lo_n))):
            raise ValueError(f"invalid independent bounds for {var}")
        require_distinguishable(lower, upper, lo_n, hi_n, relation)
        return lo_n, hi_n


    def resolve(stage: int, assigned: dict) -> dict:
        """Optimal values for this stage and every stage below it."""
        if stage >= len(order):
            return {}, set()
        player, variables = order[stage]
        fn = fns[player]

        def objective(vals: dict):
            cur = dict(assigned)
            cur.update(vals)
            deeper, _ = resolve(stage + 1, cur)
            full = dict(cur)
            full.update(deeper)
            args = [full.get(v, 0.0) for v in decision_vars]
            try:
                out = fn(*args)
            except Exception:
                return None
            return None if out != out else out

        boxes, limited = {}, set()
        for var in variables:
            lo, hi = bound_of(var)
            if hi is None:
                # probe with the other variables at a few values, so the cap is
                # not set from a slice where this variable happens to do nothing
                probes, spent = [], False
                for other in ({}, {v: (bound_of(v)[1] if bound_of(v)[1] is not None
                                       else max(1.0, bound_of(v)[0])) for v in variables
                                  if v is not var}):
                    b, ex = _find_cap(
                        lambda t: objective({**other, var: t}), lo, cap=signal_cap)
                    probes.append(b)
                    spent = spent or ex
                hi = max(probes)
                if spent:
                    limited.add(var)
            boxes[var] = (lo, hi)
        chosen, _ = _max_nd(objective, variables, boxes)
        deeper, deeper_limited = resolve(stage + 1, {**assigned, **chosen})
        # Only the selected continuation contributes its state, not every
        # off-path trial inspected during the leader search.
        return {**chosen, **deeper}, limited | deeper_limited

    values, limited = resolve(0, {})
    # Polish only the final stage's interior variables at the chosen branch.
    # A float search can drift by ~1e-8 along a flat maximum; differencing the
    # reported decisions magnifies that drift into a spurious nonzero slope.
    # This is a local precision repair, not a new global-search certificate.
    if order:
        player, last_vars = order[-1]
        interior = [v for v in last_vars if v not in limited and
                    values[v] > bound_of(v)[0] + _bound_tolerance(*bound_of(v)) and
                    (bound_of(v)[1] is None or values[v] < bound_of(v)[1] -
                     _bound_tolerance(*bound_of(v)))]
        if interior:
            fixed = dict(params)
            fixed.update({v: x for v, x in values.items() if v not in interior})
            expression = exact_numeric(payoffs[player], fixed)
            try:
                roots = sp.nsolve([sp.diff(expression, v) for v in interior],
                                  interior, [values[v] for v in interior],
                                  prec=35, tol=1e-25, maxsteps=30)
                polished = {v: float(x) for v, x in zip(interior, roots)}
                close = all(_finite(x) and abs(x - values[v]) <=
                            1e-5 * max(1.0, abs(values[v])) and
                            bound_of(v)[0] <= x and
                            (bound_of(v)[1] is None or x <= bound_of(v)[1])
                            for v, x in polished.items())
                if close:
                    old_args = [values[v] for v in decision_vars]
                    new_values = {**values, **polished}
                    old_v = fns[player](*old_args)
                    new_v = fns[player](*(new_values[v] for v in decision_vars))
                    if new_v is not None and old_v is not None and new_v >= old_v - 1e-12:
                        values = new_values
            except Exception:
                pass  # Diagnostics below still assess the unpolished candidate.
    point = {v: sp.Float(values[v]) for v in decision_vars if v in values}

    kind = {}
    for var, val in point.items():
        lo, hi = bound_of(var)
        v = float(val)
        if hi is not None and hi == lo:
            kind[var] = FIXED
        elif var in limited:
            kind[var] = SEARCH_LIMIT
        elif abs(v - lo) < _bound_tolerance(lo, hi):
            kind[var] = LOWER
        elif hi is not None and abs(v - hi) < _bound_tolerance(lo, hi):
            kind[var] = UPPER
        else:
            kind[var] = INTERIOR

    args = [float(point[v]) for v in decision_vars]
    realised, unevaluable = {}, []
    for p, fn in fns.items():
        v = fn(*args)
        if v is None:
            realised[p] = float("nan")
            unevaluable.append(p)
        else:
            realised[p] = float(v)

    stationary = {}
    if method in ("auto", "symbolic"):
        # Closed forms are informative but can be very expensive on a repaired
        # model; they are never needed for the numeric answer, so they are only
        # attempted when asked for.
        st = solve_symbolic(game, strategy)
        if st:
            stationary = st

    at = dict(params)
    at.update(point)
    owner = {v: player for player, vs in order for v in vs}
    rep = check_point(payoffs[game.focal], point, bounds, params,
                      upper_bound=game.demand_ceiling(strategy, at),
                      kinds=dict(kind),
                      payoff_for={v: payoffs[p] for v, p in owner.items()},
                      gross=gross[game.focal], realised=realised,
                      skip_optimality={v for _, vs in order[:-1] for v in vs})
    rep.findings.append(Finding(
        "search assurance", WARN,
        "product grid and local refinement give a numerical candidate, not a "
        "global optimality certificate; refine or validate independently"))
    for var in limited:
        rep.findings.append(Finding(
            "search limit", FAIL,
            f"{var}: the open-domain probe exhausted signal_cap={signal_cap:g}; "
            "this is unresolved, not proof of an infinite payoff or no maximum"))
    # --- do the two evaluation routes agree, for every player? ---
    # The checks read the payoff symbolically and the caller reports it as a
    # float.  When those disagree the report is about a different number from
    # the one on screen.  0.1.5 compared them for the focal player only, and
    # said nothing at all when the symbolic side failed, which is the state the
    # check exists to detect.
    retained_payoffs = {}
    for player in sorted(payoffs):
        reported = realised.get(player)
        try:
            retained_payoffs[player] = exact_numeric(payoffs[player], at)
            symbolic = float(sp.N(retained_payoffs[player], 80))
        except Exception:
            retained_payoffs.setdefault(player, sp.nan)
            symbolic = None
        if symbolic is None or not _finite(symbolic):
            rep.findings.append(Finding(
                "evaluation", WARN,
                f"pi_{player} could not be evaluated symbolically, so the two "
                f"routes were not compared here", required=True))
            continue
        if reported is None or reported != reported:
            continue
        scale = max(1.0, abs(symbolic), abs(reported))
        if abs(symbolic - reported) > 1e-6 * scale:
            rep.findings.append(Finding(
                "evaluation", FAIL,
                f"the reported pi_{player} {reported:.8g} and the symbolic "
                f"{symbolic:.8g} disagree, so the checks and the number on "
                f"screen are not about the same quantity"))

    # --- was the search able to evaluate its own domain? ---
    # Two different facts, reported separately because 0.1.6 conflated them.
    # A failure is a point no route could evaluate; the search skips it as "not
    # better", so the optimum is over a subset.  A rescue is a point the
    # compiled form could not evaluate and a slower one could; the optimum is
    # intact, but an expression that needs rescuing at all is worth saying so
    # about -- and it was the case that motivated this check, which 0.1.6 then
    # stopped counting by making the rescue succeed.
    for player in sorted(fns):
        ev = fns[player]
        if not ev.calls:
            continue
        if ev.calls < _EVAL_MIN_SAMPLE:
            # Suppress the percentage, not the facts.  A first attempt at this
            # dropped the route as well, which hid the one player whose payoff
            # had needed rescuing -- the case the whole mechanism exists for.
            counted = (f"pi_{player}: evaluated {ev.calls} time"
                       f"{'' if ev.calls == 1 else 's'}, too few for a rate; "
                       f"{ev.failures} could not be evaluated, {ev.rescues} "
                       f"needed a slower route (up to {ev.route_name})")
            # A failure here is already a violation under "payoff finite",
            # which names the same player; reporting it twice pads the report
            # without adding a fact.
            rep.findings.append(Finding(
                "evaluation coverage",
                WARN if (ev.failures or ev.rescues) else OK, counted))
            continue
        # the route is given with the share of points that needed it, so that
        # "exact" read on its own cannot stand in for one point in a thousand
        detail = (f"pi_{player}: {ev.failures} of {ev.calls} points could not "
                  f"be evaluated at all ({100 * ev.failure_rate:.1f}%), "
                  f"{ev.rescues} ({100 * ev.rescue_rate:.1f}%) needed a slower "
                  f"route, up to {ev.route_name}")
        if ev.failure_rate > _EVAL_FAILURE_LIMIT:
            rep.findings.append(Finding(
                "evaluation coverage", FAIL,
                detail + "; the optimum is the best of the part of the domain "
                         "that could be evaluated, not of the domain"))
        elif ev.failures or ev.rescues:
            rep.findings.append(Finding("evaluation coverage", WARN, detail))
        else:
            rep.findings.append(Finding("evaluation coverage", OK, detail))

    # --- is the competitive channel alive at this optimum? ---
    # A corner can put a player where the share rule never bites: a follower
    # that waits until the growth phase is over captures no arriving users, so
    # its payoff is its carried stock and nothing else.  The model still looks
    # like a duopoly and reads like one in a proposition, but the rival has
    # stopped entering the focal player's payoff.  Nothing about that is
    # illegal, and it is invisible in the number, so it is reported.
    share_params = list(game.share_rule.all_params())
    if share_params:
        dead, active, unknown = [], [], []
        for p in share_params:
            try:
                d = exact_numeric(game.share_sensitivity(strategy, p), at)
                value = float(sp.N(d, 80))
                if not math.isfinite(value):
                    raise ValueError("non-finite sensitivity")
                if abs(value) <= 1e-12:
                    dead.append(str(p))
                else:
                    active.append(str(p))
            except Exception as exc:
                unknown.append(f"{p}: {type(exc).__name__}: {exc}")
        if active:
            detail = f"finite nonzero local share-channel sensitivity in {', '.join(active)}"
            if unknown:
                detail += f"; other sensitivities unavailable: {'; '.join(unknown)}"
            rep.findings.append(Finding("competition", OK, detail, verdict=True))
        elif unknown:
            rep.findings.append(Finding("competition", WARN,
                f"no finite nonzero sensitivity established; unavailable: {'; '.join(unknown)}",
                verdict=None))
        else:
            rep.findings.append(Finding(
                "competition", WARN,
                f"the payoff share channel does not respond to {', '.join(dead)} at this "
                f"optimum: the share rule is inactive here, so the result is "
                f"not about competition between the players", verdict=False))

    if game.demand_ceiling(strategy, at) is None:
        rep.findings.append(Finding(
            "payoff magnitude", WARN,
            "this lifecycle declares no capacity, so the ceiling check did not "
            "run"))
    elif game.ceiling_is_endogenous(strategy):
        rep.findings.append(Finding(
            "payoff magnitude", WARN,
            "the ceiling contains a decision variable, so it rises with the "
            "payoff it bounds and this check cannot fail; read it as "
            "uninformative here"))

    return Solution(strategy=strategy, point=point, payoffs=realised, kind=kind,
                    method=method, feasibility=rep, stationary=stationary,
                    retained_payoffs=retained_payoffs)
