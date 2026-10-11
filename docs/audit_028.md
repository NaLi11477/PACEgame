# Ninth audit revision 0.2.8

| Finding | Analytic trigger | Revision acceptance |
|---|---|---|
| R9-01 (P1) | f=-A(u-v)^2+2uv, [0,1]^2; Hessian eigenvalues 2 and -4A-2 | Wrong origin rejected for 2^40, 2^53, 2^60, 10^20 and reordered symbols. Solver outputs maximum 2 or excludes the candidate. Feasible cannot pass the wrong point. |
| R9-02 (P2) | -a^2-b^2+3ab at interior a=b=0; eigenvalues 1,-5 | Automatic and explicit low-level metadata reject the saddle. Concave interior and main-solver positive-corner controls remain valid. |

Hessian entries remain SymPy values through the verdict. For a two-boundary cone, inward cross terms are oriented by lower/upper signs. A nonnegative cross excess is squared before comparison with retained diagonal product; no floating square-root subtraction decides the verdict. Exact signs take precedence over strict bounded adaptive evaluation at 80,160,320 digits. Unresolved, non-real or non-finite quantities produce a required warning and exclude ranking. Tolerances retain their stated absolute meaning; this is a necessary condition, not a maximum certificate.

Equal declared target expressions define an objective group, not an arbitrary union of players. Interior groups use retained Hessian eigenvalues. Boundary groups support one/two critical directions, excluding earlier stages, fixed/invalid coordinates and strict boundary-gradient directions. Higher-dimensional boundary cones stay incomplete. Flat feasible curvature does not resolve higher orders. Solver and low-level API now use one checker.

Binary64 finite search is not rewritten in this revision. The expanded expressions at 2^53 and 2^60 may still select the origin; curvature excludes it and ranking has no best label. The factored forms return 2. At 10^20, the previous independent final-payoff guard still excludes the expanded candidate reporting 16384. Do not confuse diagnostic rejection with recovery of the global optimum. The original 2^40 control returns 2 in both forms.

365 parent behavior cases remain, plus 34 new tests (399 total). Nine exporters cover 33 groups; three new groups address two findings. Prior R7/R8 independent controls remain. Fresh source, wheel and core-only execution evidence records actual results; hosted CI is configuration only. Technical revision acceptance remains subject to independent re-audit and author/contact/public-archive/current-template conditions.
