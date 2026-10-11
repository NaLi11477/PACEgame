"""Retain supplied numeric values before substitution or differentiation."""
from __future__ import annotations

import sympy as sp


def exact_numeric(expr, subs=None):
    """Replace Float atoms with their actual rationals before arithmetic.

    This preserves the value supplied to SymPy. It neither recovers digits
    lost before expression construction nor guesses an intended decimal.
    All expression and replacement atoms are retained before ``subs`` so
    mixed Integer/Float operations cannot erase offsets during substitution.
    The result may still be symbolic; callers decide numerical evaluability.
    """
    def retain(value):
        value = sp.sympify(value)
        atoms = value.atoms(sp.Float)
        return value.xreplace({atom: sp.Rational(atom) for atom in atoms}) if atoms else value

    return retain(expr).subs({key: retain(value) for key, value in (subs or {}).items()})


def finite_real(expr, subs=None):
    """A retained numeric real, before any binary64 conversion."""
    value = exact_numeric(expr, subs)
    if (value.is_number is not True or value.is_real is not True
            or value.is_finite is not True):
        raise ValueError("value must be a finite real number")
    return value


def retained_sign(expr):
    """Decide a retained finite real sign; numerical zero is not proof of zero."""
    value = finite_real(expr)
    if value.is_zero is True:
        return 0
    if value.is_positive is True:
        return 1
    if value.is_negative is True:
        return -1
    for precision in (80, 160, 320):
        try:
            numeric = sp.N(value, precision, maxn=4 * precision, strict=True)
            if numeric.is_real is True and numeric.is_finite is True:
                if numeric.is_positive is True:
                    return 1
                if numeric.is_negative is True:
                    return -1
        except (ValueError, TypeError, ArithmeticError):
            continue
    raise ValueError("retained real sign could not be resolved")


def retained_exceeds(left, right, tol=0, subs=None):
    """Compare the retained difference with an absolute tolerance.

    Retain both operands and the tolerance before subtraction. A caller must
    propagate unavailable signs, rather than silently treating them as passes.
    """
    a, b, tolerance = (finite_real(x, subs) for x in (left, right, tol))
    if retained_sign(tolerance) < 0:
        raise ValueError("tolerance must be nonnegative")
    return retained_sign(a - b - tolerance) > 0


def retained_difference(left, right):
    """Subtract admitted operands before any display/range conversion."""
    return finite_real(finite_real(left) - finite_real(right))


def binary64_real(value, label="value"):
    """Convert a retained result; reject nonzero underflow and overflow."""
    import math
    retained = finite_real(value)
    try:
        result = float(retained)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label} exceeds numerical range") from None
    if not math.isfinite(result) or (result == 0 and retained_sign(retained) != 0):
        raise ValueError(f"{label} exceeds numerical range")
    return result
