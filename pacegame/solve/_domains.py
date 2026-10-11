"""Exact interval geometry must precede floating coordinate classification."""
from __future__ import annotations
import sympy as sp
from ..core.numeric import exact_numeric


class BoundsPrecisionError(ValueError):
    """A domain cannot safely use the current binary64 search coordinates."""


def exceeds(a, b):
    """Compare retained real numbers, using high precision only if needed."""
    difference = a - b
    verdict = difference.is_positive
    if verdict is None and difference.is_number and difference.is_real:
        verdict = sp.N(difference, 80).is_positive
    return verdict


def interval_relation(lo, hi, width=None):
    """Relation of substituted SymPy endpoints before conversion to float."""
    width = hi - lo if width is None else width
    if width.is_zero is True:
        return "fixed"
    if width.is_negative is True:
        return "reversed"
    if width.is_positive is True:
        return "nonzero"
    return "unknown"


def retained_interval(lo, hi, subs=None):
    """Retain each endpoint before substitution and interval arithmetic.

    Subtracting mixed Float/exact inputs first can erase a nonzero width.
    Both solver and validator use this path to classify the same geometry.
    """
    lower, upper = exact_numeric(lo, subs), exact_numeric(hi, subs)
    return lower, upper, interval_relation(lower, upper)


def require_distinguishable(lo, hi, lo_n, hi_n, relation, tol=1e-9):
    if lo_n is not None and hi_n is not None and lo_n == hi_n and relation != "fixed":
        raise BoundsPrecisionError(
            f"bounds precision unavailable: non-singleton or unresolved interval "
            f"({lo}, {hi}) collapses after numerical substitution/conversion; rescale the "
            "model or use independently validated higher-precision coordinates")
    threshold = exact_numeric(tol)
    for bound, converted in ((lo, lo_n), (hi, hi_n)):
        if converted is None:
            continue
        error = abs(exact_numeric(converted) - bound)
        if exceeds(error, threshold) is not False:
            raise BoundsPrecisionError(
                f"bounds precision unavailable: endpoint {bound} has binary64 "
                f"coordinate error {error}, exceeding absolute tolerance {tol}; "
                "translate/rescale the model or use independently validated "
                "higher-precision coordinates")
