# Eleventh audit revision 0.2.10

## R11-01 Mixed endpoint geometry

The solver and public `check_point` validator retain each endpoint and its
parameter substitutions before subtracting or classifying the interval. For
`lo=Float(1.0)` and `hi=1+10^-20`, the interval is nonzero but its binary64
coordinates collapse; solving and ranking raise `BoundsPrecisionError`, while
the low-level result is required and incomplete. Replacing the upper endpoint
with `1-10^-20` produces an invalid reversed domain and raises `ValueError`.
`Float(0.1)` is its actual supplied binary value, not the exact decimal 1/10;
the corresponding reversed mixed-endpoint example also rejects.

Verification keeps existing computation-error accounting: rejected solves
produce zero passes and explicit errors. A true mixed singleton, a normal
mixed interval and a representable narrow interval remain valid. Retention
cannot recover information already lost before constructing an expression.

## R11-02 Tolerance admission and range

`check_point(tol=...)` first checks the retained value is numeric, finite, real
and nonnegative. Thus exact `-10^-400` cannot become an accepted negative zero.
Positive `10^-400` and nonfinite binary64 conversions receive an explicit
supported-range `ValueError`. This range policy does not claim arbitrary
precision search support. Zero, normal values and representable subnormal
tolerances remain admitted.

The original admitted tolerance is retained for endpoint precision,
membership, gross-sign and ceiling comparisons; conversion cannot widen a
Rational threshold. The derivative and curvature heuristics still use the
admitted binary64 approximation and their documented fixed numerical scales.
The default `check_point` tolerance remains 1e-9; `Bounded` remains 1e-12.

## R11-03 Payoff finite-real admission

Net payoffs, supplied gross payoffs and supplied realised payoffs require
retained finite-real admission before conversion. Exact `1+I*10^-400` and
`1+I*10^-10` are violations regardless of whether a ceiling is supplied.
Unresolved admission is a required warning, making the result incomplete.
An omitted gross payoff still skips the optional sign test, and legal negative
net payoffs remain accepted. The main solver's additional symbolic guard also
continues to exclude complex-payoff candidates. Derivative approximation
policy is separate from this public payoff-input admission.

## Reproduce

Run `python -m pacegame.tests` and
`python -m pacegame.examples.validate_audit_0210 /external/results`.
The suite retains 424 parent methods and adds 26 methods (450 total).
Eleven exporters, including `validate_release`, exercise 39 numbered audit
groups; three new groups correspond to three findings, not three individual
tests. The external `evidence/verify_round11_fixes.py` constructs independent
public Game fixtures and Rational oracles. It can also confirm the frozen
parent defects with `--expect-parent-defects --source-root /parent/source`.

Fresh source, full-wheel, core-wheel, old probes and sdist-rebuild receipts
accompany this revision. These are local Linux observations; hosted CI and
other platform/version combinations remain configured rather than executed.
Revision acceptance applies to the covered cases; a new independent audit,
verified submission metadata and current official-template verification are
still needed for final approval. No global optimum or full Nash certificate
is asserted.
