"""Shared finite-scan sign reversal handling; not a continuous-domain proof."""
from __future__ import annotations
import math
from ..core.numeric import finite_real, retained_exceeds, retained_sign


def scan_crossing(fn, lo, hi, scan, iters, tol):
    if not math.isfinite(tol) or tol < 0:
        raise ValueError("tol must be nonnegative and finite")

    def value(x):
        y = fn(x)
        return finite_real(y)

    xs = [lo + (hi - lo) * i / scan for i in range(scan + 1)]
    ys = [value(x) for x in xs]
    previous = None
    for i, y in enumerate(ys):
        if not retained_exceeds(abs(y), 0, tol):
            continue
        if previous is not None:
            j = previous
            if retained_sign(ys[j]) != retained_sign(y):
                if i > j + 1:
                    # A sampled zero (or zero run) lies between opposite signs.
                    # Return a sampled representative, without claiming uniqueness
                    # or an unsampled plateau boundary.
                    return xs[(j + i) // 2]
                x0, x1, sign_lo = xs[j], xs[i], ys[j]
                for _ in range(iters):
                    mid = (x0 + x1) / 2
                    g = value(mid)
                    if not retained_exceeds(abs(g), 0, tol):
                        return mid
                    if retained_sign(g) == retained_sign(sign_lo):
                        x0 = mid
                    else:
                        x1 = mid
                return (x0 + x1) / 2
        previous = i
    return None
