# PACEgame 0.2.11

A Python toolkit for inspecting continuous-time sequential entry and signalling models. It constructs symbolic demand integrals, searches a declared domain, labels numerical candidates and tests sampled claims. MIT licensed. This release is archived at DOI 10.5281/zenodo.23295744 and published on GitHub. PyPI publication is not used.

## Install

From the extracted release directory, with internet access for dependencies:

```sh
python -m pip install .
python -m pacegame.cli models
python -m pacegame.cli solve preannounce_entry --repair
```

The release also contains a wheel and `vendor/` runtime dependency wheels. For a core offline installation:

```sh
python -m pip install --no-index --find-links vendor dist/pacegame-0.2.11-py3-none-any.whl
```

Python >=3.10 is the syntax requirement. This audit actually ran on CPython 3.12.14, Linux, SymPy 1.14.0. macOS, Windows and other Python versions are CI targets, not claimed completed audit runs. For plots: `python -m pip install '.[figures]'`; Matplotlib 3.10.8 was tested. Plotting dependencies are not included in the core offline wheelhouse.

## Use

```python
from pacegame import models, solve
from pacegame.analyze import rank_strategies, verify

game = models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                signal_cost=True)
point = dict(sigma=0.1, phi=0.85, hatvarsigma=0.3, kappa_d=0.05)
result = rank_strategies(game, point)
print(result)
report = verify.check(game, [verify.Feasible(), verify.Dominates('RL', 'RF')],
                      over={'sigma': (0.05, 0.4)}, n=3,
                      fixed={k: v for k, v in point.items() if k != 'sigma'})
print(report)
```

`equilibrium` is retained as a compatibility alias for `rank_strategies`. Neither implements a full simultaneous strategy game or certifies Nash or subgame-perfect equilibrium. The rival's role follows the focal label. A rival matching a signal does not receive independent signal choice rights; signalling cost is charged only to the focal player, as in the supplied specification.

Final-stage interior candidates can receive local high-precision stationarity polishing to reduce decision-value drift. This is a precision check on the chosen branch, not proof of a global solution.

## Interpret results

- `interior`, `lower corner`, `upper corner`, `fixed`: numerical candidate classifications. Grid plus local refinement is a heuristic, not a global optimality proof. Tight/narrow peaks and discontinuous follower reactions need independent validation.
- `search limit`: an open-domain probe reached a finite computational budget. It establishes neither infinite payoff nor nonexistence of a finite maximizer. Such candidates are excluded from ranking and payoff statics.
- `Solution.unbounded` is retained for the explicit `unbounded` state; the current numeric routine does not issue that state from a finite probe.
- `Outcome.best` is `None` if no valid resolved candidates exist; `complete` says whether the ranking includes every requested strategy.
- `FeasibilityReport.ok` excludes violations; `complete` additionally requires all requested necessary numeric/domain checks to receive a verdict. Required warnings make the report `INCOMPLETE` and exclude a candidate from ranking. Optional search-assurance, flat-curvature and sensitivity warnings remain explicit and do not themselves invalidate a payoff.
- `fixed` denotes a singleton interval. No feasible direction exists there, so one-sided corner conditions do not apply. Narrow nonzero intervals retain separate corner and interior classifications.
- `Report.ok` means no counterexample or computational error occurred. `Report.complete` additionally requires exact accounting for every claim at every requested point, with no skips or errors. One-shot claim iterators and generators are materialized once. `Result.holds` requires full tested-point coverage. A grid is evidence on samples, never proof over a continuum.
- Errors retain their reason. Skips and errors are separate. Invalid domains are rejected before search. The CLI returns 0 for a complete valid operation, 1 for counterexamples/unresolved output, and 2 for malformed input or verification computation errors.
- Comparative statics use finite differences; feasible one-sided stencils replace invalid central perturbations at boundaries. Non-finite finite-difference denominators, numerators and slopes raise a numerical-range error; they never establish a sign. Discrete regime changes need step-size sensitivity checks.
- A threshold returning `None` means no strict crossing was detected by this scan. It is not an absence proof. Sampled zeros between opposite nonzero signs are retained. A zero run returns a sampled representative, not a unique transition boundary; endpoint ties and touching zeros alone are not strict reversals.
- `Competitive` passes only with finite nonzero share-channel sensitivity evidence, holding decisions, installed stocks, lifecycle and costs fixed; cost-only responses do not qualify. Custom payoff/share paths without an explicit `Game.share_sensitivity` hook remain unknown; all-zero sensitivity fails the activity claim without invalidating the payoff. Unknown sensitivity yields a skipped claim and retains its reason. `Interior` concerns a whole valid candidate and skips unresolved, invalid or incomplete parents.

## Reproduce and test

```sh
python -m pacegame.tests
python examples/audit_preannouncement.py
python examples/validate_release.py validation
python examples/validate_audit_021.py validation
python examples/validate_audit_022.py validation
python examples/validate_audit_023.py validation
python examples/validate_audit_024.py validation
python examples/validate_audit_025.py validation requirements-reproduce.txt
python examples/validate_audit_026.py validation
python examples/make_figures.py figures
python examples/replicate_study.py legacy_results
python examples/benchmark.py --out benchmark.json --repeats 3 --rounds 2
```

The legacy replication script re-evaluates the inventory included in v0.1.8. The underlying companion manuscript was not supplied; no independent published-study replication or external adoption is claimed. All models/data are synthetic and stylized. The validation scripts record numerical results, sampled claims, independent quadrature and an analytic finite-asymptote counterexample. The benchmark checks every subprocess exit code and stores environment, repetitions and load observations; it makes no hardware-isolation or comparative-speed claim.

## Extend

Implement a `Lifecycle` with `segments`, `stock_at`, `capacity` and declared `params`, a `ShareRule` with `shares` and `all_params`, or subclass `Game.payoffs`/`bounds`/`validate`. Bounds must be independent numeric expressions after parameter substitution; decision-dependent feasible domains are unsupported and rejected. Memoized payoffs include primitive class identity and public state in dictionaries, dataclass fields and inherited slots, plus strategy flags and the time symbol. Dictionary keys and values retain their types and SymPy identity; key order is ignored, while ordered sequence contents are preserved. Supported recursive public containers are acyclic dictionaries, lists, tuples, sets and frozensets of scalar/SymPy values. Private, cyclic or opaque custom state requires an explicit model representation and `game.invalidate()` after mutation; it is not automatically inspected.

`game.numeric(point)` accepts string keys and ignores unused names for compatibility with dictionaries holding inactive model switches. CLI `--set`, public sweeps and verification grid axes reject unknown names. Direct `solve` accepts the resulting symbol-keyed mapping and validates domains again.

See `docs/audit_025.md`, `docs/model.md`, `docs/audit_023.md`, `docs/audit_022.md` and the accompanying audit report for the model assumptions, migration changes, unresolved submission metadata and test evidence.

The third-audit closure is in docs/audit_022.md. The five-group acceptance exporter writes audit_022_acceptance.json; 25 added tests complement all 173 retained tests. The previous seven-group exporter remains executable. `check_point(tol=...)` requires a finite nonnegative real tolerance. See docs/release_scope.txt and recorded logs for actual validation rather than inferring it from the CI matrix.

## Fourth-audit interfaces

`verify.Sign` accepts exactly `d pi_<player> / d <parameter>` with optional whitespace, selecting either current player's payoff at a resolved candidate. For example, `Sign("d pi_y / d phi", "<", strategy="DF")` checks the rival payoff, not the focal payoff. Player and parameter tokens must have no whitespace or slash. Unknown players, parameters, strategies and malformed expressions are rejected before sampled evaluation. Decision numerators are unsupported in Sign; use `derivative(game, "DF", "phi", point, quantity="varsigma")`. `derivative(quantity="payoff")` remains the focal alias; `quantity="pi_x"` or `"pi_y"` explicitly selects a current player. Payoff gaps require `quantity="payoff"`.

`sweep(..., strategies=...)` materializes its nonempty, uniquely named admitted Strategy pool once. Lists, tuples, iterators, generators and one-shot Iterable objects give identical multi-point results. Unknown strategies, wrong flags, repeated names and empty pools are rejected before any solve. The values iterable is consumed once; empty values return `[]` after strategy validation.

Fourth-audit closure: `docs/audit_023.md`; `audit_023_acceptance.json` exports three repaired groups. Thirty new tests complement all 198 retained tests; the five-group third-audit and seven-group second-audit exporters remain executable. See actual execution evidence for the completed scope.

## Fifth-audit contracts

`check_point` requires coordinates and declared bounds for every variable in point, bounds, kinds, payoff_for and skip_optimality. Every declared interval is inspected even when a coordinate is missing. Unknown kinds and mismatched fixed/corner/interior labels are violations. Omitted kinds are inferred from actual bounds; solver and validator share the same scale-aware corner tolerance, capped within narrow nonzero intervals. Legacy corner labels on singleton intervals are interpreted as fixed. A search limit is unresolved and cannot produce a complete low-level optimality report. Leader reduced-objective warnings remain explicit.

Proportional quality keys must name the actual Game players. Unknown keys reject at construction and public numeric/symmetry boundaries, including after mutation. Missing quality defaults to 1; symmetry uses both actual effective qualities. For a standalone rule, `is_symmetric(players=('alpha','beta'))` checks custom names; the no-argument default is x/y. `players_alike` additionally excludes signalling scenarios; `role_conflict()` remains a descriptive gap available only for interchangeable players. Custom rules retain their no-argument symmetry method through `is_symmetric_for(players)`.

Built-in share and lifecycle coefficients accept constants or SymPy expressions. Constants introduce no external parameter; `Proportional(2*alpha)` introduces alpha rather than a parameter named `2*alpha`. `all_params()` tracks the current coefficient expressions and qualities. Game expands declared expressions to free scalar Symbols and rejects distinct Symbols with the same string name. Evaluated phi/beta coefficients must be nonnegative, arrival rate positive, and Logistic ceiling/rate positive; existing symbol assumptions and horizon/quality restrictions also apply. Custom primitives should declare every parameter or implement `all_params()`.

The unified `python -m pacegame.tests` entry discovers every shipped test module, including test_audit_023 and test_audit_024. CI runs this entry and all five validation exporters against the installed wheel outside a checkout. Hosted macOS/Windows and other Python matrix targets are configured; the release evidence records the actual Linux execution. Fifth-audit acceptance exports five groups to audit_024_acceptance.json. The manuscript uses all 17 supplied depth-report fields C1-C9 and S1-S8; S8 is Support email for questions. Author/contact, permanent public identifiers and the current official template remain pending.

## Sixth audit revision 0.2.5

The five current findings are implemented. The complete suite retains all 262 prior tests and adds 38 regressions (300 total); six validation exporters exercise 25 audit acceptance groups. The release records source and isolated installed-wheel execution on CPython 3.12.14, Linux. Hosted CI targets remain configured, not executed claims.

Exact interval width is inspected before numerical substitution and binary64 conversion. A non-singleton interval whose endpoints collapse raises public `BoundsPrecisionError` in the solver; low-level checks issue a required `bounds precision` warning and stay incomplete. Rescale such models or independently validate higher-precision coordinates. No automatic arbitrary-precision global search is provided. Genuine singleton intervals whose coordinates meet the absolute representation tolerance, and narrow representable nonzero intervals, retain their classifications. See the seventh-audit precision contract below.

Entry, signal and time must be scalar SymPy Symbols with distinct identities and names. External primitive parameter symbols must be independent of all three. This contract and distinct focal/rival identities are checked at construction and again at public computation boundaries, including after mutable public-state changes. Constants and independent coefficient expressions remain supported.

For a joint objective at a box boundary, the diagnostic checks necessary curvature on critical feasible directions when at most two such directions remain. Upper/lower orientation and strict first-order gradients are respected. Larger critical cones or unavailable derivatives issue required warnings; flat curvature retains an explicit higher-order warning. These tests do not certify a local or global maximum and do not remove finite-grid search limitations.

`requirements-core.txt` pins the core offline runtime. `requirements-reproduce.txt` pins the four principal dependencies used for this release: SymPy 1.14.0, mpmath 1.3.0, Matplotlib 3.10.8 and NumPy 2.3.5. `requirements-reproduce-lock.txt` records all installed optional runtime distributions in the isolated figure environment. Plotting remains optional; core tests and acceptance exporters do not import Matplotlib or NumPy. Version pins describe the observed environment, not bitwise reproducibility across hardware or supported platforms.

## Seventh audit revision 0.2.6

Both R7 items are implemented: the P1 candidate-coordinate precision defect and the P2 single-coordinate boundary coverage extension. All 300 previous behavior tests remain; 27 regressions bring the suite to 327 tests. Seven exporters exercise 27 audit acceptance groups. The recorded runs cover Linux/CPython 3.12.14; hosted CI remains configured rather than an executed platform claim.

Bounds, numeric parameter substitution and candidate membership retain each Float's actual binary value as a SymPy Rational before mixed exact arithmetic. Membership is compared with original retained endpoints using the declared absolute tolerance. Converting endpoints to binary64 must not change either endpoint by more than the solver's absolute domain tolerance 1e-9, including true singletons. A nonzero interval must also remain distinguishable. Otherwise solve raises BoundsPrecisionError; low-level checks issue a required precision warning and are incomplete. Exact out-of-domain points also receive a violation. This conservatively rejects unsupported coordinates rather than producing a ranking from a rounded infeasible point. It does not supply arbitrary-precision search.

For A=10^20 and u in [A+1,A+32769], the decreasing lawful net payoff A-u has maximum -1. These coordinates are rejected because binary64 shifts the endpoints by 1. Translating the whole model to x=u-A with x in [1,32769] and net payoff -x returns x=1 and -1. Translate bounds, all objectives and gross/cost/ceiling expressions consistently. The independent symbolic payoff route retains exact candidate/parameter values before arithmetic, so cancellation that was hidden by Float substitution causes an evaluation violation and excludes the candidate. Merely comparing two payoff evaluations at the same already-rounded point does not validate original-domain membership. Representable [A,A+32768], [A,A], ordinary rational bounds and the 1e-10 narrow-domain controls remain supported.

Necessary boundary curvature now covers a single remaining boundary coordinate, including after fixed neighbors have been removed. Positive curvature at zero first derivative fails; concave corners pass, strict inward-negative first derivatives remove critical directions, and flat directions retain the higher-order scope warning. One/two-dimensional critical cones remain necessary checks only; larger cones or unavailable derivatives remain incomplete. The diagnostic does not certify a local/global maximum.

Run `python -m pacegame.examples.validate_audit_026 validation` in source or after installation. `docs/audit_026.md` records the exact cases and the distinction between technical revision acceptance and an independent next audit. Author identities/contact/declarations, public permanent archives and current official-template confirmation remain pending.

## Eighth audit revision 0.2.7

One P1 finding R8-01 is addressed by retaining actual Float values before parameter and candidate arithmetic. Search-objective construction, local polishing, candidate classification and necessary derivatives now share retained substitution. For A=10^20 or 2^60, (sigma-A+1)*u and its squared-coordinate variant return u=1 and payoff=1 on [0,1]. Wrong lower points fail; correct strict-gradient upper points pass. Candidate offset-A+1 is checked at the same actual point as literal 1. Unavailable required curvature or independent payoff comparison prevents ranking.

All 327 parent tests remain; 38 new controls bring the suite to 365. Eight exporters cover 30 groups, including three groups for the one R8-01 finding. Run `python -m pacegame.examples.validate_audit_027 validation` for its closure evidence. The original R7 precision and cancellation controls remain. Retaining Float values does not recover preconstructed rounding or certify all compiled binary64 evaluations; final-point payoff agreement does not prove objective accuracy throughout the domain. See docs/audit_027.md and actual execution receipts. Prior numbered revision sections above describe their respective historical scope.

The original threshold regression sampled half its crossing, inside an exact lower-entry tie plateau. It now checks that exact tie and samples the nonzero branch at 0.9 times the crossing, preserving both strict crossing assertions. This correction is recorded separately from R8-01; no solver tolerance or necessary-condition verdict is weakened.


## Ninth audit revision 0.2.8

R9-01 retains the Hessian entries and cone comparison through the sign verdict. Two-boundary cross terms use a sign-checked squared comparison rather than binary64 square roots. R9-02 extends the same diagnostic to equal-objective interior groups, and the solver calls that shared path instead of maintaining a separate interior check. Distinct declared objectives, earlier sequential stages and fixed coordinates keep their documented scope. Unavailable necessary curvature prevents completion and ranking.

For f=-A(u-v)^2+2uv on [0,1]^2, the maximum is 2 at (1,1), while the origin has a feasible positive-curvature direction. With A=2^53 or 2^60 the expanded binary64 search may still produce the origin; it is now rejected, and `rank_strategies` has no best label if that is the only candidate. The equivalent factored form returns 2. At A=10^20 the pre-existing final-payoff guard still excludes the incorrectly evaluated expanded candidate. This revision improves necessary diagnostics; it does not provide stable evaluation of every search expression or recover every optimum. Rejection is a completed violation verdict, whereas an unavailable required check is incomplete.

The full suite retains 365 parent tests and adds 34 tests (399 total). Nine exporters cover 33 acceptance groups; three new groups address two findings. Run `python -m pacegame.examples.validate_audit_028 validation`. Recorded source, installed-wheel and offline core executions, independent public probes, distribution checks and manuscript validation accompany the release. Hosted CI remains configured, not an executed cross-platform claim. See docs/audit_028.md.

## Tenth audit revision 0.2.9

Retained payoff-minus-ceiling comparisons reject large-scale excesses before binary64 rounding. Bounded uses the same comparison, with its existing absolute tolerance 1e-12; low-level magnitude keeps 1e-9. Unknown required ceiling comparisons prevent completion. Strict finite-real and sign validation precedes numerical range checks across Game.numeric, direct solve and mutable coefficient boundaries. Supplied numeric values are retained before substitution. Nonzero values that underflow to zero, or overflow binary64, raise an explicit ValueError; zero and normal positive costs remain supported.

The full suite keeps the 399 parent cases and adds 25 tests (424 total). Ten exporters cover 36 groups. Run `python -m pacegame.examples.validate_audit_029 validation`. See docs/audit_029.md for counterexamples, lawful controls, range policy and limits. Prior counts above describe historical releases. Cross-platform CI remains configured rather than executed.

## Eleventh audit revision 0.2.10

Mixed Float/exact bounds are retained separately before interval subtraction. Reversed domains reject, and nonzero collapsed coordinates raise BoundsPrecisionError rather than become fixed points or valid rankings. Verification records rejected solves as computation errors with zero passes.

Tolerance signs are checked before conversion. Nonzero underflow and overflow raise an explicit binary64 range error; admitted original tolerances govern membership, endpoint precision, gross-sign and ceiling comparisons. Public net/gross/realised payoff inputs require retained finite-real admission; tiny exact imaginary parts cannot be projected onto the real axis. Unknown admission is required and incomplete, omitted gross remains optional, and negative net payoffs remain lawful.

All 424 parent test methods remain, with 26 new methods for 450 total. Eleven exporters cover 39 numbered acceptance groups. Run `python -m pacegame.examples.validate_audit_0210 validation`; see docs/audit_0210.md for the three findings, controls and range policy. Counts in earlier sections describe historical revisions. This revision acceptance still needs an independent re-audit; hosted CI, public archives and current official-template verification are not asserted as completed.

## Revision 0.2.11


- R12-01: admit every declared payoff_for objective at the retained candidate before fixed, skipped-stage or derivative branches. Known non-real/non-finite values are required violations; unknown admission is required unavailable. Different finite owner objectives and negative net payoffs remain legal.
- R12-02: Solution.retained_payoffs binds each final payoff to its own parameters and candidate. Outcome.payoff_value and Solution.payoff_value expose finite-real retained values; binary64 payoffs remain display/compatibility values. Ranking, ties, dominance, crossings and constrained payoff finite differences subtract retained operands first. Unavailable comparison cannot become a zero, tie or weak pass; complete=False or explicit ValueError/skip propagates. Existing absolute thresholds stay unchanged.
- 43 regression methods join 450 parent cases: 493 total. Twelve exporters cover 41 numbered acceptance groups. Source, installed full wheel and offline core installation are validated separately; hosted cross-platform CI executes the wheel, audit and figure validation across the os × python-version matrix.
- Word, XeLaTeX, metadata, evidence and release manifests are synchronized. The Zenodo DOI 10.5281/zenodo.23295744 provides a permanent public identifier. Independent re-audit, confirmed authors/declarations and current official-template certification remain pending.

See docs/audit_0211.md for retained payoff access, unavailable status and fixed-candidate analytic controls.
