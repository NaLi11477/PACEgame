# Model specification and limits

This release evaluates the supplied v0.1.8 specification. The external companion study was not provided, so exact attribution to a published article is unverified.

## Decisions

RF: focal player signals and leads; rival chooses entry time.
RL: focal player signals and follows; focal signal and entry are jointly selected.
DF: focal player is silent and leads; rival chooses entry time.
DL: focal player is silent and follows; focal chooses entry time.

The pioneer enters at zero. The follower enters at e in [entry_floor, growth_end] for TwoPhase, or [entry_floor, horizon] for Logistic. A singleton interval is fixed and has no feasible timing deviation. Signalling, when enabled, has d >=0, optionally bounded by signal_ceiling. For RF, the signal is selected before the rival's entry response. Other labels are conditional scenarios. Ranking their focal payoffs is not a Nash strategy-profile calculation.

TwoPhase demand grows at rate sigma until g, then stays flat to T. Proportional shares are theta_j(1+phi*q_j)/sum(theta_i(1+phi*q_i)). Payoff is one quarter of integrated demand, less timing_cost*(1-own_entry/T) and, for the focal signalling player, signal_cost*d^2/2. The general-horizon timing cost is nonnegative on 0<=own_entry<=T and preserves the former formula at T=1. The factor 1/4 and timing-cost normalization are assumptions, not calibrated empirical quantities.

Lifecycle.capacity() bounds cumulative endogenous demand, with demand-times-time units. TwoPhase uses sigma*(g*T-g^2/2); Logistic uses the loose bound ceiling*T. A player's gross payoff is bounded by (max carried stock*T+capacity)/4; nonnegative costs also put net payoff below this bound. The stock term is included only for keep_stock=True. Custom lifecycles must establish their own envelope and restrictions. This does not impose customer conservation, and a ceiling depending on an open signal remains an uninformative diagnostic.

The pioneer demand level carries sigma*e. A signal enters its duopoly share but does not directly add to its demand level. The follower's signal stock enters its demand level only with keep_stock=True. Matching rival signals change the share input; they are mechanically tied to the focal signal and do not add a rival decision or rival signal cost. Do not describe this as fully symmetric signalling.

## Baseline versus variants

The baseline has keep_stock=False, signal_accrues=False and no costs. At sigma=.1, phi=.85, g=.3 and e=0, the two signalling labels' focal payoff has the finite limit .006375 as d tends to infinity; silent payoff is .0031875. The finite-cap numerical result is therefore not proof of an infinite payoff. The validation script derives and stores the limit.

The stock-cost variant sets keep_stock=True, signal_accrues=True, signal_cost=True. At the illustrative point kappa_d=.05, RL has d approximately 1.05, e=.3, payoff .0275625. These are stylized signal-created demand stocks; total realized customers are not constrained by a closed-population conservation rule. This is not an empirically calibrated adoption model.

The bounded-signal variant adds d<=sigma (T=1 in the factory). At the same point d=.1, e=.3, RL payoff=.005. This is a chosen exogenous bound; it does not establish real-world credibility. With cost alone the signal is interior, while adding the bound makes it an upper corner. The same claim list is checked for both variants.

A readiness lag constrains e>=lambda. It creates a pioneer window for silent strategies but cannot force RL away from its upper corner, and it does not restore every strategy's local share-parameter sensitivity.

## Other models

Logistic demand uses adopted(t)-adopted(0) with a logit share. It has silent labels only. `asymmetric_quality` changes baseline qualities; the stock-cost RL corner may make those qualities locally irrelevant. The competition diagnostic measures the explicit share-channel partial with decisions, installed stocks, lifecycle and costs held fixed, not the total derivative of an equilibrium response and not the absence of economic competition globally.

## Supported parameter domain

All parameters must be finite real numbers and satisfy declared SymPy positivity assumptions. Require 0<=entry_floor<=growth_end<=horizon, horizon>0, nonnegative costs and signal bounds, positive qualities. Alternative custom restrictions belong in Game.validate. Bounds that depend on decisions rather than substituted parameters are not supported.

For lifecycles without growth_end, horizon is used consistently in validation and bounds. Unknown requested bounds, supplied gross payoff or magnitude ceilings make low-level required checks incomplete; absent gross is explicitly skipped rather than replaced by net profit. Custom payoff/share implementations must explicitly implement Game.share_sensitivity to declare this channel; otherwise its diagnostic is unknown. A share parameter used in a cost or lifecycle cannot establish activity through that other path. Optional sensitivity uncertainty does not remove a finite payoff from comparison, but cannot establish Competitive. Interior uses whole-candidate scope.

The local activity diagnostic treats absolute partial sensitivities <=1e-12 as numerically inactive. This is a declared numerical tolerance, not proof of an exactly zero real-valued derivative.

Public primitive fields in __dict__, dataclasses and inherited __slots__ participate in the payoff fingerprint together with actual class identity. Hidden/private state requires explicit invalidate(). Claim iterables are consumed once and every result must account for all requested points before Report.complete is true. Low-level feasibility tolerance must be finite, real and nonnegative; finite differences reject numerical overflow instead of returning an infinite slope or sign.

## Structural and numerical contracts in 0.2.5

Game.entry, Game.signal and Game.time are independent scalar Symbols with unique names. External primitive parameters cannot alias them. Game.focal and Game.rival are distinct identities. Public mutation is validated again before integration and search. Custom overrides must preserve these public contracts.

Bounds are inspected using pre-substitution symbolic width before float conversion. BoundsPrecisionError indicates an interval cannot be represented distinctly by the numerical search coordinates. A true singleton has no feasible direction, but its endpoint must still meet the representation tolerance. Necessary boundary curvature is checked for joint groups with one/two critical feasible directions; a flat result or a finite-grid candidate never certifies optimality.

## Candidate precision and remaining boundary directions in 0.2.6

Before numeric parameter substitution, Float atoms in domain expressions and parameter values retain their actual binary values as Rational numbers. This prevents a large Float plus a small exact offset from silently erasing the offset during substitution. The symbolic interval width is still inspected before substitution.

The binary64 solver requires finite endpoint conversion error <=1e-9 in absolute coordinate units and distinguishable nonzero endpoints. This includes fixed domains. The low-level validator uses its supplied finite nonnegative absolute tol for endpoint representation and compares candidate membership against the retained original domain, rather than rounded endpoint values. Exact/high-precision numeric comparison precedes floating corner classification. Unsupported representation receives a required precision warning; outside candidates receive violations. Both ok and complete are required for ranking. Translate/rescale all model expressions together when original coordinate units cannot meet this contract. Payoff agreement at a returned coordinate cannot repair original-domain violations.

Boundary objectives are grouped by equal declared expressions after skipped, invalid, outside and fixed coordinates are excluded. A group with one remaining boundary coordinate is checked, as are groups with one/two critical directions. Strict first-order boundary derivatives remove critical directions; their first-order verdict is recorded separately. Flat curvature is an optional higher-order scope warning, not maximum certification. More than two active directions and unavailable gradients/Hessians remain required incomplete warnings.

## Consistent retained values in 0.2.7

Parameters and candidate expressions are retained before search and local necessary derivatives, not only before interval membership and final payoff comparison. Actual binary values are preserved without inferring decimal intent. Derivatives are taken from expressions whose Float atoms have been retained; corner classification and gradient/Hessian evaluation use the same retained candidate. An unavailable necessary condition remains incomplete. Compiled evaluation is still binary64 and final-point agreement alone does not validate an entire search objective. See audit_027.md for the analytic scope and tests.

## Shared retained joint curvature in 0.2.8

Equal declared objectives receive retained Hessian diagnostics for interior groups and supported critical boundary cones. Cross signs and squared products decide two-boundary cone curvature without converting Hessian entries to binary64. Owner groups, earlier stages and fixed coordinates retain their scope. If a necessary sign cannot be decided, completion and ranking are blocked. This does not guarantee stable evaluation of the finite search objective, higher-order maxima or global optimality. See audit_028.md.

## Numeric domains and range

Supplied numeric parameter values are retained before substitution. Domain validation checks finite-real values and declared signs before binary64 conversion; direct solves and public coefficient mutations repeat these checks. Costs and nonnegative coefficients cannot pass by underflowing a negative value to -0.0. Nonzero input/coefficients converting to zero, or converting to a nonfinite binary64 value, raise an explicit supported-range ValueError. Legal zero costs and normally represented positive inputs remain supported. Requested finite ceiling comparisons use retained payoff-minus-ceiling differences, with existing absolute tolerances 1e-9 in check_point and 1e-12 in Bounded. Unavailable required comparisons prevent ranking. The solver still performs finite binary64 searches.
