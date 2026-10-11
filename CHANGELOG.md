# PACEgame 0.2.11 2026-10-08

- R12-01: admit every declared payoff_for objective at the retained candidate before fixed, skipped-stage or derivative branches. Known non-real/non-finite values are required violations; unknown admission is required unavailable. Different finite owner objectives and negative net payoffs remain legal.
- R12-02: Solution.retained_payoffs binds each final payoff to its own parameters and candidate. Outcome.payoff_value and Solution.payoff_value expose finite-real retained values; binary64 payoffs remain display/compatibility values. Ranking, ties, dominance, crossings and constrained payoff finite differences subtract retained operands first. Unavailable comparison cannot become a zero, tie or weak pass; complete=False or explicit ValueError/skip propagates. Existing absolute thresholds stay unchanged.
- 43 regression methods join 450 parent cases: 493 total. Twelve exporters cover 41 numbered acceptance groups. Source, installed full wheel and offline core installation are validated separately; hosted cross-platform CI remains unexecuted.
- Word, XeLaTeX, metadata, evidence and release manifests are synchronized. Independent re-audit, confirmed authors/declarations, permanent public identifiers and current official-template certification remain pending.

# Changelog

## 0.2.10 2026-10-08

- R11-01: share endpoint retention before interval subtraction between solver and low-level validation.
- R11-02: validate retained tolerance signs before conversion, reject nonzero binary64 underflow/overflow and retain admitted absolute comparison thresholds.
- R11-03: admit only retained finite-real net, supplied gross and realised payoffs; mark unknown admission required and unavailable.
- Preserve genuine singleton, representable narrow-domain, omitted-gross and negative-net controls.
- Add 26 regression methods and three acceptance groups; synchronize Word, XeLaTeX and installation/rebuild evidence.

## 0.2.9

- Compare retained payoff-ceiling differences before rounding, in feasibility and Bounded.
- Reject negative underflow inputs and coefficients using retained signs, including public mutations and direct solves.
- Preserve supplied numeric parameter values; reject unsupported binary64 underflow/overflow explicitly.
- Add 25 regressions and three tenth-audit acceptance groups; synchronize manuscript and release metadata.

## 0.2.8 2026-10-07

- R9-01: keep finite real Hessian values and cone comparisons retained through the sign verdict; use exact signs before bounded strict adaptive evaluation.
- R9-02: shared equal-objective curvature check covers interior and supported boundary candidates; remove the duplicate solver-only interior check.
- Preserve owner, stage and fixed-domain scope; unresolved curvature is required and incomplete.
- Reject unstable expanded-expression candidates rather than report false feasibility or rank them. The finite binary64 search itself remains heuristic.
- Retain 365 parent tests and add 34 analytic/scope regressions (399); nine exporters exercise 33 acceptance groups.
- Synchronize complete Word and XeLaTeX manuscripts, figures, metadata and independently executed release evidence. Independent re-audit and publisher acceptance remain pending.

## 0.2.7 2026-10-07

- Address R8-01 by retaining actual parameter, expression and candidate Float values before substitution or differentiation.
- Use consistent objectives, polishing, corner classification, critical gradients/Hessians, ceilings and final-payoff checks.
- Mark unavailable necessary curvature or independent payoff comparisons required and incomplete.
- Retain all 327 parent regressions; add 38 controls and three acceptance groups through an eighth exporter.
- Synchronize complete Word and XeLaTeX articles and preserve existing search and numerical-scope limits.

## 0.2.6 2026-10-07

- R7-01: retain Float binary values before bound/parameter arithmetic; check candidate membership against original endpoints; reject binary64 endpoint errors beyond absolute tolerance, including true singletons.
- Keep typed precision failures out of ranking and dependent claims; support consistent shifted coordinates and representable large-domain controls.
- R7-02: check necessary scalar boundary curvature after fixed coordinates are excluded, retaining strict-gradient and higher-order scope behavior.
- Retain 300 tests, add 27 controls, add the seventh exporter and two groups (327 tests, 27 audit groups); synchronize complete Word and XeLaTeX manuscripts.


## 0.2.5 2026-10-07

- Sixth audit: inspect exact pre-substitution interval width; reject collapsed non-singleton numerical domains with BoundsPrecisionError; low-level required warnings prevent ranking.
- Require independent scalar structural Symbols and external primitive parameter symbols at construction and public mutable-state boundaries.
- Check necessary curvature in one/two-dimensional critical box-boundary cones; retain larger-cone, flat-curvature and finite-search scope warnings.
- Reject duplicate focal/rival identities before stocks, shares, integration or ranking.
- Align principal reproduction pins and actual environment records; add core-only and optional full lock files.
- Retain all 262 prior tests, add 38 regressions, add a sixth exporter and five acceptance groups; synchronize complete Word and XeLaTeX manuscripts.


## 0.2.4 2026-10-07

- Validate low-level candidate types, actual interval positions and coordinate coverage; keep narrow and singleton domains distinct.
- Reject quality keys outside the actual Game players; use effective quality defaults for symmetry.
- Discover all packaged tests and execute every retained/current acceptance exporter against installed wheels in CI.
- Collect free Symbols from constant/compound primitive coefficients, validate evaluated domains and reject ambiguous symbol names.
- Restore all 17 depth-report metadata labels, including S8 Support email for questions.
- Retain 228 regressions and add 34 controls. Full execution results accompany the release.

# 0.2.3 — 2026-10-06

- Encode dictionary keys and values recursively with types and SymPy identity; dictionary/set order is irrelevant, ordered sequences remain ordered.
- Strictly parse Sign payoff expressions and bind focal/rival targets before evaluation; unsupported numerator or parameter cannot silently pass.
- Expose explicit player payoffs through derivative(quantity="pi_<player>") while retaining focal and decision responses.
- Consume sweep strategy iterables once and validate the complete pool before solving.
- Add 30 fourth-audit controls and a three-group acceptance export; retain all 198 earlier tests and twelve prior groups.

# 0.2.2 — 2026-10-06

- Include public inherited slot/dataclass state and class identity in payoff caching.
- Isolate local share-channel sensitivity from stock, lifecycle and cost paths; custom paths require an explicit hook or remain unknown.
- Consume claim iterables once and require complete point accounting.
- Reject invalid low-level feasibility tolerances and non-finite difference results before sign verdicts.
- Add 25 third-audit regression tests and a five-group executable acceptance export; retain all 173 earlier tests and the seven-group exporter.

# 0.2.1 — second-audit corrections

- Sweep returns 1 when any requested candidate is unresolved or invalid.
- Threshold and derivative-crossing scans retain sampled zeros bracketed by opposite signs; zero runs return a sampled representative, not a unique boundary.
- Singleton decision intervals are classified as fixed and removed from free-coordinate searches and one-sided KKT checks; narrow nonzero intervals keep distinct corners.
- Sensitivity diagnostics distinguish finite nonzero, all-zero and unknown results. Competitive cannot pass without finite nonzero evidence.
- Logistic entry bounds use its horizon. Lifecycle capacity has cumulative-demand units; carried-stock ceilings include horizon. Timing costs use 1-entry/horizon and remain nonnegative on the declared domain.
- Required low-level checks expose incomplete status. Omitted gross payoffs are not replaced by net payoffs. Invalid/incomplete candidates are excluded from ranking.
- Interior uses whole valid candidate scope; unresolved or invalid parent solutions are skipped.
- Retain the chosen signal bound sigma*horizon independently of the capacity diagnostic, preserving the T=1 bounded-signal example.
- Add 38 acceptance tests and a machine-readable executable acceptance exporter.

# 0.2.0 — audited review release

Based on the supplied 0.1.8 archive. Behavioral changes justify a minor version.

- Finite open-domain search exhaustion is `search limit`, never an unbounded-payoff proof. Unresolved and invalid candidates cannot rank or enter comparative statics.
- `rank_strategies` names the actual operation; `equilibrium` remains an alias. No full Nash equilibrium is claimed; empty rank sets yield `best=None`.
- Verification records computation errors and skips separately. Exceptions cannot become a vacuous Feasible pass. Full sampled-point coverage is required for a claim to hold.
- Reject nonfinite/invalid model domains, invalid methods/search caps, unknown sweeps/grid/CLI names and empty/nonfinite grids.
- Interior stationarity and joint interior curvature are checked; leader raw partial derivatives are withheld because recourse changes the objective. Numerical global optimality remains uncertified.
- Selected continuation states replace off-path accumulated search-limit flags. The exact evaluation route remains available after a local failure.
- Memo keys include time and full strategy flags. Single explicit quality and mechanically matched signal choices no longer imply player interchangeability.
- Benchmark rejects failed commands and records environment, repetitions, raw times and load observations without certifying isolation.
- Legacy example ranges respect readiness lag. Unverified publication/impact and no-crossing-existence claims are removed.
- Author/repository/DOI placeholders are removed from package metadata. No public publishing action is performed. Manuscript identifies outstanding submission fields.

The bundled regression expectations changed only where 0.1.8 asserted the incorrect semantics above; tests were retained. See docs/audit_020.md for exact evidence.
- Final-stage interior choices receive local high-precision first-order polishing when it stays near the searched candidate and preserves its objective. This prevents optimizer drift from appearing as a derivative of a mathematically constant decision. It is not a global certificate.
