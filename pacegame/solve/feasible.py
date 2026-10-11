"""Is a candidate optimum actually an optimum, and is it inside the model?

Closed-form solutions obtained by setting a first-order condition to zero carry
three standing risks: the root can fall outside the declared feasible set, it
can be a minimum rather than a maximum, and the payoff it implies can exceed
what the model's own demand makes possible.  Each is cheap to test and easy to
miss by hand, so the tests run automatically on every solve.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp
from ._domains import BoundsPrecisionError, retained_interval, require_distinguishable, exact_numeric, exceeds
from ..core.numeric import finite_real, retained_sign, retained_exceeds

__all__ = ["Finding", "FeasibilityReport", "check_point"]

OK, WARN, FAIL = "ok", "warning", "violation"


@dataclass
class Finding:
    check: str
    status: str
    detail: str
    required: bool = False
    #: An optional diagnostic verdict; None means unavailable, not false.
    verdict: bool | None = None

    def __str__(self):
        mark = {OK: "ok  ", WARN: "warn", FAIL: "FAIL"}[self.status]
        return f"  [{mark}] {self.check}: {self.detail}"


@dataclass
class FeasibilityReport:
    findings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(f.status != FAIL for f in self.findings)

    @property
    def complete(self) -> bool:
        """All required checks received a numeric verdict (pass or violation).

        Optional algorithm/sensitivity warnings do not imply incomplete bounds.
        This does not certify global optimality or continuous-domain coverage.
        """
        return bool(self.findings) and not any(
            f.required and f.status == WARN for f in self.findings)

    def violations(self) -> list:
        return [f for f in self.findings if f.status == FAIL]

    def __str__(self):
        head = "INFEASIBLE" if not self.ok else ("feasible" if self.complete else "INCOMPLETE")
        return "\n".join([f"feasibility: {head}"] + [str(f) for f in self.findings])


def _num(expr, subs):
    try:
        v = complex(sp.N(exact_numeric(expr, subs), 80))
    except (TypeError, ValueError, AttributeError):
        return None
    import math
    if not math.isfinite(v.real) or not math.isfinite(v.imag):
        # NaN compares false against everything, so a NaN that reaches the
        # tests below passes all of them and the report says "feasible" about
        # something that is not a number.
        return None
    if abs(v.imag) > 1e-9:
        return None
    return v.real


def _admit_payoff(rep, value, check):
    """Require retained finite-real payoff values before numerical conversion.

    A known non-real/non-finite value is a violation; unresolved admission is
    required and unavailable. Derivative approximation policies stay separate.
    """
    if (value in (sp.nan, sp.zoo, sp.oo, -sp.oo)
            or value.is_real is False or value.is_finite is False):
        rep.findings.append(Finding(check, FAIL,
            "the supplied payoff is not a finite real number", required=True))
        return False
    if (value.is_number is not True or value.is_real is not True
            or value.is_finite is not True):
        rep.findings.append(Finding(check, WARN,
            "retained payoff finite-real admission unavailable", required=True))
        return False
    return True


def _bound_tolerance(lo, hi):
    """Shared solver/validator corner scale; keep narrow nonzero domains."""
    import math
    scale = max([1.0] + [abs(v) for v in (lo, hi) if v is not None])
    tol = max(1e-7, 8 * math.ulp(scale))
    return min(tol, (hi - lo) * 1e-4) if lo is not None and hi is not None and hi > lo else tol


def _retained_sign(expr):
    """Decide a finite real sign without converting retained values to float.

    Exact signs take precedence. Strict, bounded adaptive evaluation may decide
    a nonzero sign; rounded numerical zero never proves exact zero. Failure to
    decide is propagated as a required unavailable diagnostic.
    """
    value = exact_numeric(expr)
    if value.is_real is not True or value.is_finite is not True:
        raise ValueError("non-finite/non-real curvature expression")
    if value.is_zero is True:
        return 0
    if value.is_positive is True:
        return 1
    if value.is_negative is True:
        return -1
    for precision in (80, 160, 320):
        try:
            numeric = sp.N(value, precision, maxn=4*precision, strict=True)
            if numeric.is_real is True and numeric.is_finite is True:
                if numeric.is_positive is True:
                    return 1
                if numeric.is_negative is True:
                    return -1
        except (ValueError, TypeError, ArithmeticError):
            continue
    raise ValueError("curvature sign could not be resolved")


def _joint_curvature(rep, payoff, owned, at, positions, skipped, excluded, tol):
    """Necessary joint curvature of each equal declared objective.

    All-interior groups use their retained Hessian spectrum. Boundary groups
    cover one/two-dimensional critical feasible cones, after excluding earlier
    stages, fixed coordinates, and strict boundary-gradient directions. Neither
    this condition nor a flat-direction warning certifies a maximum.
    """
    groups = {}
    for var, kind in positions.items():
        if var in skipped or var in excluded or kind not in {"interior", "lower corner", "upper corner"}:
            continue
        target = exact_numeric(owned.get(var, payoff))
        groups.setdefault(target, []).append((var, kind))
    threshold = exact_numeric(max(tol, 1e-7))
    for target, variables in groups.items():
        boundary = any(k != "interior" for _, k in variables)
        if not boundary and len(variables) == 1:
            # The ordinary scalar interior second-order check already covers it.
            continue
        active = []
        try:
            for var, kind in variables:
                gradient = exact_numeric(sp.diff(target, var), at)
                strict = _retained_sign(sp.Abs(gradient)-threshold) > 0
                if kind != "interior" and strict:
                    # Its first-order verdict is recorded separately.
                    continue
                active.append((var, kind))
        except Exception:
            rep.findings.append(Finding("joint curvature", WARN,
                "critical gradients could not be evaluated", required=True))
            continue
        if boundary and len(active) > 2:
            rep.findings.append(Finding("joint curvature", WARN,
                f"boundary critical cone has dimension {len(active)}; only one/two-dimensional cones are covered",
                required=True))
            continue
        if not active:
            rep.findings.append(Finding("joint curvature", OK,
                "boundary critical cone has no nonzero direction; necessary check only", required=True, verdict=True))
            continue
        try:
            symbols = [v for v, _ in active]
            raw = exact_numeric(sp.hessian(target, symbols), at)
            for value in raw:
                # Verify real finiteness even when another entry proves failure.
                _retained_sign(value)
            if len(active) == 1:
                largest = raw[0, 0]
                violation = _retained_sign(largest-threshold) > 0
                flat = _retained_sign(sp.Abs(largest)-threshold) <= 0
                detail = f"one-dimensional critical curvature: {sp.N(largest, 12)}"
            elif all(kind != "interior" for _, kind in active):
                signs = [1 if kind == "lower corner" else -1 for _, kind in active]
                a, b = raw[0, 0], raw[1, 1]
                cross = signs[0]*signs[1]*raw[0, 1]
                negative_a = -a if _retained_sign(a) < 0 else sp.Integer(0)
                negative_b = -b if _retained_sign(b) < 0 else sp.Integer(0)
                product = negative_a*negative_b
                # q(s,t)<=0 on s,t>=0 requires a,b<=0 and
                # cross<=sqrt((-a)*(-b)). Compare retained squared values
                # only after establishing the correct nonnegative cross sign.
                shifted = cross-threshold
                cross_violation = (_retained_sign(shifted) > 0 and
                                   _retained_sign(shifted**2-product) > 0)
                violation = (_retained_sign(a-threshold) > 0 or
                             _retained_sign(b-threshold) > 0 or cross_violation)
                envelope = sp.sqrt(product)
                flat = (_retained_sign(sp.Abs(a)-threshold) <= 0 or
                        _retained_sign(sp.Abs(b)-threshold) <= 0 or
                        _retained_sign(sp.Abs(cross-envelope)-threshold) <= 0)
                detail = (f"two-boundary critical cone: diagonal=({sp.N(a,12)}, {sp.N(b,12)}), "
                          f"inward cross={sp.N(cross,12)}, nonpositive envelope={sp.N(envelope,12)}; "
                          f"retained cross excess={sp.N(cross-envelope,12)}")
            else:
                # With one unrestricted coordinate, each quadratic direction
                # can be oriented into the boundary half-space. All-interior
                # groups use the same spectrum computation, including >2D.
                eigenvalues = list(raw.eigenvals())
                if not eigenvalues:
                    raise ValueError("empty Hessian spectrum")
                signs = [_retained_sign(value-threshold) for value in eigenvalues]
                violation = any(sign > 0 for sign in signs)
                flat = any(_retained_sign(sp.Abs(value)-threshold) <= 0 for value in eigenvalues)
                scope = "mixed boundary/interior" if boundary else "interior"
                detail = f"{scope} critical Hessian eigenvalues: {[str(sp.N(v,12)) for v in eigenvalues]}"
            rep.findings.append(Finding("joint curvature", FAIL if violation else OK,
                detail + "; necessary local condition, not a maximum certificate", required=True, verdict=not violation))
            if flat and not violation:
                rep.findings.append(Finding("joint curvature scope", WARN,
                    "flat feasible curvature does not resolve higher-order behavior"))
        except Exception:
            rep.findings.append(Finding("joint curvature", WARN,
                "critical Hessian or its sign could not be evaluated", required=True))


def check_point(payoff, point: dict, bounds: dict, params: dict,
                upper_bound=None, tol: float = 1e-9,
                kinds: dict | None = None,
                payoff_for: dict | None = None,
                gross=None, realised: dict | None = None,
                skip_optimality: set | None = None) -> FeasibilityReport:
    """Run every check on one candidate ``point`` of one player's payoff.

    ``point`` maps each decision symbol to its candidate value, ``bounds`` maps
    the same symbols to (lo, hi) expressions, and ``params`` fixes the model
    parameters numerically.  ``kinds`` says whether each optimum is interior or
    on a bound, which decides *which* optimality test applies: a second-order
    condition is only meaningful in the interior, while on a bound the test is
    that the payoff is not still climbing out of the feasible set.
    ``payoff_for`` names, per variable, the payoff of the player that actually
    chooses it: a leader's own payoff says nothing about whether its rival's
    reaction is optimal.  ``gross`` is the payoff before costs; the sign test
    applies to it rather than to the net payoff, because a net payoff may be
    negative once a signalling or timing cost is subtracted, while a demand
    integral may not.  When it is omitted the sign test is skipped rather than
    guessed at.

    ``tol`` must be finite, real and nonnegative before binary64 conversion.
    Nonzero underflow/overflow is rejected explicitly. Retained absolute
    tolerances govern membership, gross sign and payoff-ceiling comparisons;
    derivative heuristics use the admitted binary64 tolerance.
    """
    import math
    try:
        tolerance = finite_real(tol)
        if retained_sign(tolerance) < 0:
            raise ValueError
    except (TypeError, ValueError, ArithmeticError):
        raise ValueError("tol must be a finite nonnegative real number") from None
    try:
        tol = float(tolerance)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("tol is outside the supported binary64 range") from None
    if not math.isfinite(tol) or (tol == 0 and tolerance.is_zero is not True):
        raise ValueError("tol is outside the supported binary64 range")
    rep = FeasibilityReport()
    sub = dict(params)
    fixed = set()
    kinds = {} if kinds is None else kinds
    owned = {} if payoff_for is None else payoff_for
    skipped = set() if skip_optimality is None else set(skip_optimality)
    allowed = {"interior", "lower corner", "upper corner", "fixed",
               "unbounded", "search limit"}
    invalid = set()
    outside = set()
    numeric_bounds = {}
    positions = {}
    expected = set(point) | set(bounds) | set(kinds) | set(owned) | skipped
    for var in sorted(expected, key=str):
        if var not in point or var not in bounds:
            missing = "coordinate" if var not in point else "declared bounds"
            rep.findings.append(Finding("candidate metadata", FAIL,
                f"{var}: missing {missing}", required=True))
            invalid.add(var)
        if var in kinds and (not isinstance(kinds[var], str) or kinds[var] not in allowed):
            rep.findings.append(Finding("candidate metadata", FAIL,
                f"{var}: unknown candidate kind {kinds[var]!r}", required=True))
            invalid.add(var)

    # --- 1. inside the declared feasible set
    # Inspect every declared interval, including those with a missing point.
    for var, interval in bounds.items():
        lo, hi = interval
        lo, hi, relation = retained_interval(lo, hi, sub)
        if relation == "reversed":
            rep.findings.append(Finding("bounds", FAIL,
                f"{var}: lower bound exceeds upper bound", required=True))
            invalid.add(var)
            continue
        lo_n, hi_n = _num(lo, {}), _num(hi, {})
        if lo == sp.oo or hi == -sp.oo:
            rep.findings.append(Finding("bounds", FAIL,
                f"{var}: invalid signed infinite interval", required=True))
            continue
        if (lo_n is None and lo != -sp.oo) or (hi_n is None and hi != sp.oo):
            rep.findings.append(Finding("bounds", WARN,
                f"{var}: requested bounds not finite real/evaluable: ({lo}, {hi})",
                required=True))
            continue
        if lo_n is not None and hi_n is not None and lo_n > hi_n:
            rep.findings.append(Finding("bounds", FAIL,
                f"{var}: lower bound exceeds upper bound", required=True))
            continue
        # Membership uses the original numbers and the candidate's actual
        # binary value, never two identically rounded endpoint approximations.
        if var in point:
            candidate = exact_numeric(point[var], sub)
            if candidate.is_real is True and candidate.is_finite is True:
                below = False if lo == -sp.oo else exceeds(lo - candidate, tolerance)
                above = False if hi == sp.oo else exceeds(candidate - hi, tolerance)
                if below is True or above is True:
                    direction = (f"below its lower bound {lo}" if below is True
                                 else f"exceeds its upper bound {hi}")
                    rep.findings.append(Finding("bounds", FAIL,
                        f"{var} = {candidate} {direction} in retained interval ({lo}, {hi}) "
                        f"at absolute tolerance {tol}", required=True))
                    outside.add(var)
                elif below is None or above is None:
                    rep.findings.append(Finding("bounds", WARN,
                        f"{var}: retained numeric membership comparison unavailable", required=True))
                    invalid.add(var)
        try:
            require_distinguishable(lo, hi, lo_n, hi_n, relation, tolerance)
        except BoundsPrecisionError as error:
            rep.findings.append(Finding("bounds precision", WARN,
                f"{var}: {error}", required=True))
            invalid.add(var)
            continue
        if relation == "fixed":
            fixed.add(var)
        numeric_bounds[var] = (lo_n, hi_n)
        if var not in point:
            continue
        v = _num(point[var], sub)
        if v is None:
            rep.findings.append(Finding("bounds", WARN, f"{var} not numeric", required=True))
            continue
        if var not in outside and var not in invalid:
            if candidate.is_real is not True or candidate.is_finite is not True:
                rep.findings.append(Finding("bounds", WARN,
                    f"{var}: candidate has no finite real membership verdict", required=True))
                invalid.add(var)
                continue
            rep.findings.append(Finding("bounds", OK, f"{var} = {v:.6g} is in range", required=True))

    # --- 2. optimality: second order inside, first order on a bound
    at = dict(sub)
    at.update({k: exact_numeric(v, sub) for k, v in point.items()})
    # Admission is independent of whether this coordinate needs a derivative.
    # A constant invalid/unknown owner payoff must not disappear on diff(), or
    # escape through the fixed/earlier-stage branches below.
    for var, target in sorted(owned.items(), key=lambda item: str(item[0])):
        _admit_payoff(rep, exact_numeric(target, at), f"owner payoff ({var})")
    for var in point:
        if var in invalid:
            continue
        kind = kinds.get(var)
        if var in numeric_bounds and var not in outside:
            lo_n, hi_n = numeric_bounds[var]
            v = _num(point[var], sub)
            if v is None:
                continue
            corner_tolerance = _bound_tolerance(lo_n, hi_n)
            lower = lo_n is not None and abs(v - lo_n) < corner_tolerance
            upper = hi_n is not None and abs(v - hi_n) < corner_tolerance
            actual = ("fixed" if var in fixed else "lower corner" if lower
                      else "upper corner" if upper else "interior")
            # A singleton is both corners. Preserve the legacy explicit corner
            # inputs while interpreting them as fixed, without a KKT direction.
            compatible = (kind is None or kind == actual
                          or (var in fixed and kind in {"fixed", "lower corner", "upper corner"})
                          or (hi_n is None and kind in {"search limit", "unbounded"}))
            if not compatible:
                rep.findings.append(Finding("candidate metadata", FAIL,
                    f"{var}: kind {kind!r} does not match {actual} at the declared interval",
                    required=True))
                continue
            if kind is None:
                kind = actual
        elif var in kinds and var not in outside:
            rep.findings.append(Finding("candidate metadata", WARN,
                f"{var}: kind cannot be checked without an evaluable interval", required=True))
            continue
        elif kind is None:
            kind = "interior"
        positions[var] = "fixed" if var in fixed else kind
        if var in fixed:
            rep.findings.append(Finding("fixed variable", OK,
                f"{var}: singleton interval; no feasible direction, no one-sided KKT test"))
            continue
        if kind == "search limit":
            rep.findings.append(Finding("optimality", WARN,
                f"{var}: search limit is unresolved, not an optimality verdict", required=True))
            continue
        if kind == "unbounded":
            rep.findings.append(Finding(
                "optimality", FAIL,
                f"the payoff has no maximum in {var}: it rises without bound, "
                f"so the model needs a cost or a cap on it"))
            continue
        if var in skipped:
            rep.findings.append(Finding("reduced objective", WARN,
                f"{var}: leader objective includes a follower reaction; raw "
                "partial derivatives are not an optimality certificate"))
            continue
        target = exact_numeric(owned.get(var, payoff))
        if kind == "interior":
            try:
                first = _num(sp.diff(target, var), at)
            except Exception:
                first = None
            rep.findings.append(Finding("stationarity",
                WARN if first is None else (FAIL if abs(first) > 1e-6 else OK),
                f"d/d{var} = {first}; tested against 1e-6", required=True))
            try:
                second = _num(sp.diff(target, var, 2), at)
            except Exception:
                second = None
            if second is None:
                rep.findings.append(Finding("second order", WARN,
                                            f"d2/d{var}2 not evaluable", required=True))
            elif second > tol:
                rep.findings.append(Finding(
                    "second order", FAIL,
                    f"d2/d{var}2 = {second:+.6g} > 0: the stationary point is "
                    f"a MINIMUM"))
            elif abs(second) <= tol:
                rep.findings.append(Finding("second order", WARN,
                                            f"d2/d{var}2 = {second:+.3g} is flat"))
            else:
                rep.findings.append(Finding("second order", OK,
                                            f"d2/d{var}2 = {second:+.6g} < 0"))
            continue
        try:
            first = _num(sp.diff(target, var), at)
        except Exception:
            first = None
        if first is None:
            rep.findings.append(Finding("first order", WARN,
                                        f"d/d{var} not evaluable", required=True))
        elif kind == "lower corner" and first > 1e-7:
            rep.findings.append(Finding(
                "first order", FAIL,
                f"d/d{var} = {first:+.6g} > 0 at the lower bound: the search "
                f"stopped short of the optimum"))
        elif kind == "upper corner" and first < -1e-7:
            rep.findings.append(Finding(
                "first order", FAIL,
                f"d/d{var} = {first:+.6g} < 0 at the upper bound"))
        else:
            rep.findings.append(Finding(
                "first order", OK,
                f"d/d{var} = {first:+.6g} is consistent with the {kind}"))

    _joint_curvature(rep, payoff, owned, at, positions, skipped,
                        invalid | outside | fixed, tol)

    # --- 3. payoff sign and magnitude
    # --- 0. the number the caller will report must be a number
    for player, value in (realised or {}).items():
        retained_value = exact_numeric(value)
        if not _admit_payoff(rep, retained_value, "payoff finite"):
            continue
        realised_value = _num(retained_value, {})
        if realised_value is None:
            rep.findings.append(Finding(
                "payoff finite", FAIL,
                f"the payoff of {player} did not evaluate to a finite number "
                f"at this optimum, so nothing below is a statement about it"))
        else:
            rep.findings.append(Finding(
                "payoff finite", OK, f"pi_{player} = {realised_value:.6g}"))

    retained_payoff = exact_numeric(payoff, at)
    if not _admit_payoff(rep, retained_payoff, "payoff"):
        return rep
    pv = _num(retained_payoff, {})
    if pv is None:
        rep.findings.append(Finding("payoff", FAIL,
                                    "the payoff is not a finite real number"))
        return rep
    if gross is None:
        rep.findings.append(Finding("payoff sign", WARN,
                                    "gross payoff not supplied; sign test skipped"))
    else:
        retained_gross = exact_numeric(gross, at)
        if _admit_payoff(rep, retained_gross, "payoff sign"):
            gv = _num(retained_gross, {})
            try:
                if gv is None:
                    raise ValueError("gross payoff numerical route unavailable")
                negative = retained_exceeds(0, retained_gross, tolerance)
            except (ValueError, TypeError, ArithmeticError):
                rep.findings.append(Finding("payoff sign", WARN,
                    "gross payoff sign not evaluable", required=True))
            else:
                rep.findings.append(Finding("payoff sign", FAIL if negative else OK,
                    (f"gross payoff = {gv:.6g} < 0, but the demand integral cannot be negative"
                     if negative else f"gross payoff = {gv:.6g}")))
    if upper_bound is not None:
        bound = exact_numeric(upper_bound, at)
        if bound == sp.oo:
            rep.findings.append(Finding("payoff magnitude", WARN,
                "explicit infinite ceiling is uninformative"))
        else:
            try:
                above = retained_exceeds(retained_payoff, bound, tolerance)
            except (ValueError, TypeError, ArithmeticError):
                rep.findings.append(Finding("payoff magnitude", WARN,
                    f"requested ceiling comparison unavailable: {bound}", required=True))
            else:
                rep.findings.append(Finding("payoff magnitude", FAIL if above else OK,
                    (f"payoff exceeds the model's own ceiling {sp.N(bound, 6)}; "
                     f"retained excess {sp.N(retained_payoff - bound, 6)} > {tol}"
                     if above else f"payoff <= ceiling {sp.N(bound, 6)} within {tol}"),
                    required=True))
    return rep
