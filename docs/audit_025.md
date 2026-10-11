# Sixth audit revision 0.2.5

This revision implements R6-01 through R6-05 of the v0.2.4 Round 6 audit. R6-01, R6-02 and R6-04 were confirmed defects; R6-03 extends declared boundary-check coverage, and R6-05 aligns reproduction metadata. This acceptance does not replace the next independent audit.

| Item | Change | Controls |
|---|---|---|
| R6-01 | Inspect symbolic width before substitution and float conversion; reject precision collapse | Exact A=10^20 domain [A,A+1], reversed domain, substituted offset, actual singleton, rescaled unit and 1e-10 interval |
| R6-02 | Scalar distinct structural Symbols and independent primitive parameters | time/rate and decision/parameter aliases, constructor and mutation rejection, independent alpha=1 versus constant rate |
| R6-03 | Necessary curvature on critical feasible box-boundary cones with at most two directions | Audited mixed corner, infeasible positive eigenvector, concave corner, upper/lower orientation, strict gradients, flat and dimension-three disclosure |
| R6-04 | Distinct actual player identities | Duplicate constructor and mutation rejection, custom alpha/beta and default x/y payoff dictionaries |
| R6-05 | Align exact reproduction pins and actual records; separate optional plotting | Core-only offline install and exporter execution; isolated optional plotting pins and complete dependency record |

The solver raises BoundsPrecisionError rather than returning a false fixed candidate. CLI precision-unavailable requests return unresolved exit 1; malformed model contracts return input-error exit 2. The low-level validator may have ok=True but complete=False for a required precision warning; callers must require both, as ranking does.

Boundary grouping uses the same declared objective for jointly evaluated coordinates. Earlier sequential coordinates excluded via skip_optimality remain excluded. Critical boundary directions with a strict first-order derivative are removed after their separate first-order verdict. Mixed boundary/interior directions use the Hessian; two boundary directions use oriented quadratic-form nonpositivity on the inward quadrant. Flat directions do not resolve higher orders. Coverage above two critical directions is incomplete. Numerical tolerances and finite search continue to limit assurance.

Run `python -m pacegame.tests` and `python -m pacegame.examples.validate_audit_025 validation requirements-reproduce.txt` from the extracted release. After installation, omit the optional requirements path if unavailable; the exporter then uses its packaged snapshot. Record actual environment versions and do not infer full supported-platform execution from the CI matrix.

All 300 tests include 262 retained cases and 38 new cases. Twenty prior acceptance groups and five current groups are exercised in source and installed-wheel environments. Evidence contains the original depth report and frozen Round 6 findings, current outputs, commands, receipts, integrity checks and manuscript alignment. Permanent public identifiers, author/contact declarations and current official-template certification remain pending.

## Seventh audit follow-up

R6-01 covered collapsed endpoints, but distinguishable endpoints were insufficient to establish original-domain membership. Version 0.2.6 adds retained candidate/endpoint comparisons and absolute endpoint conversion error checks, including singletons. R6-03 grouping also skipped a remaining scalar boundary coordinate after fixed neighbors were excluded; 0.2.6 covers that case. See audit_026.md and its executable exporter.
