# PACEgame 0.2.1 — closure of the second independent audit

The parent v0.2.0 broad approval was narrowed by seven independent audit groups. This release implements their fixes; exact measured acceptance results are exported to evidence/validation/audit_021_acceptance.json, alongside source and installed-wheel logs. Historic audit_020.md is not a current approval.

| Finding | Implementation | Acceptance coverage |
| --- | --- | --- |
| R2-01 | Sweep aggregates invalid/unresolved state into exit 1 | Complete 0, incomplete 1, malformed 2 |
| R2-02 | Shared scan retains zero samples between opposite signs | Node root, off-node root, touching zero, endpoint tie, zero plateau, tolerance errors |
| R2-03 | Fixed decisions excluded from free-coordinate search and one-sided KKT | Fixed entry, signal, both; narrow nonzero intervals |
| R2-04 | Finite nonzero, all-zero and unknown sensitivity verdicts | Activity, inactivity, all unknown, partial unknown+active/zero, absent parameters |
| R2-05 | Horizon-aligned domains; cumulative capacity; stock times horizon; normalized nonnegative timing cost | Both lifecycles below/at/above unit horizon, analytic integral, independent quadrature |
| R2-06 | Required completeness; unknown bounds/ceilings retained; absent gross skipped | Missing/nonnumeric/infinite bounds, requested ceiling, legitimate negative net, zero ceiling |
| R2-07 | Interior uses whole valid candidate scope | Unresolved parent, invalid parent, valid interior |

Compatibility: T=1 illustrative payoff values and the chosen signal bound sigma*horizon are retained. Custom Lifecycle.capacity implementations must now explicitly provide cumulative-demand units. Finding adds required/verdict fields; FeasibilityReport.complete governs necessary-check completion. Optional sensitivity warnings do not invalidate finite payoff comparison, but unknown activity cannot pass Competitive. Interior skips change the baseline six-claim grid from two skipped/four failed claims to four skipped/two failed claims. Updated JSON, figures and manuscript reflect this change.

These acceptance cases establish their stated behavior, not complete software correctness, a regional proposition theorem or a global/Nash certificate. Public submission identifiers and author information still require true source material.
