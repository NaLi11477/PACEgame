# Tenth audit revision 0.2.9

The parent audit identified two P2 defects. This revision fixes their specific numerical guards; independent re-audit remains pending.

## Retained ceiling comparisons

At A=2^53, 2^60 or 10^20, excesses of 1, 128 or 4096 can disappear when payoff and ceiling are separately rounded to binary64. `check_point` now retains both operands and its absolute tolerance before computing the difference. The three deliberately injected over-ceiling outputs fail the required magnitude diagnostic, are excluded from rankings, fail Feasible and are skipped by Bounded. Fixed decision domains isolate this guard from search accuracy. They are invalid model outputs, not counterexamples to a lawful model's capacity.

`Bounded` uses the same retained difference function on the symbolic focal payoff at the selected point. Its existing absolute tolerance remains 1e-12; low-level magnitude retains 1e-9. A diagnostic-tolerance control A=10^6, excess=10^-11 therefore passes low-level magnitude but fails Bounded. This difference is intentional. Unknown/nonreal/nonfinite required comparisons produce an unavailable result rather than a pass. An explicitly infinite ceiling remains uninformative.

## Strict finite-real and sign validation

`Game.numeric` preserves supplied SymPy numeric values. Ordinary Python floats retain their supplied binary values; no intended decimal is inferred. Validation checks finite real values and exact/adaptively resolved signs before float conversion. Bare parameter assumptions and evaluated horizon, entry, cost, signal, quality and share coefficients use this policy. Entry-domain ordering compares retained differences.

Signal and timing parameters equal to -10^-400 are rejected as nonnegative-domain violations before search. The same applies to mutated constant costs and the Proportional phi coefficient, at numeric and direct-solve boundaries. A negative evaluated cost such as q-1 with q=1-10^-400 is also rejected rather than rounded to zero. The ordinary negative, zero and positive controls remain covered.

The numerical search still uses binary64. Nonzero finite input or evaluated coefficients whose conversion becomes zero, or whose conversion is nonfinite, raise ValueError with a supported-binary64-range message. Positive underflow is therefore explicitly unsupported; it is not silently accepted as zero. Actual zero costs remain lawful. NaN, infinity and nonreal inputs reject as invalid finite-real values. The deliberate unlimited signal bound is the existing special case.

## Reproduction and scope

Run `python -m pacegame.tests` and `python -m pacegame.examples.validate_audit_029 validation`. The suite retains all 399 parent tests and adds 25 regressions, for 424 tests. Three new groups bring the numbered acceptance total to 36 across ten exporters including validate_release. The new groups cover two defects and the range policy; group count is not defect count.

The independent `evidence/verify_round10_fixes.py` repeats public-interface cases with analytic arithmetic and records its oracles without calling the new numeric helpers. Source, full installed wheel and core-only evidence distinguish dependencies and skips. Parent R7/R8/R9 probes are retained. Local sign and ceiling verdicts do not certify global optima, arbitrary-precision search, continuous-domain propositions or Nash equilibrium.
