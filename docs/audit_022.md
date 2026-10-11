# Third-audit revision: PACEgame 0.2.2

Parent: frozen v0.2.1; input: PACEgame_v0_2_1_Audit_Round3.docx. Five finding IDs and the input digest are retained in INPUT_PROVENANCE.json.

| Finding | Implemented contract | Behavioral acceptance |
| --- | --- | --- |
| R3-01 | Fingerprint includes public dataclass/slot state across MRO and actual class identity | gain 1→2→1 matches the exact integrated payoff; same-named classes, slotted shares, fresh game and invalidate controls |
| R3-02 | Game.share_sensitivity isolates the explicit share channel using independent stock/share placeholders and a chain rule | cost-only and lifecycle-only overlap cannot pass; genuine share response passes; custom undisclosed payoff channel skips |
| R3-03 | Materialize claims once; nonempty Claim instances; Report.complete requires exact point accounting | lists, tuples, iterators and generators execute identically; empty/partial reports cannot be complete |
| R3-04 | check_point validates tolerance before all checks | NaN, signed infinity, negative, complex and symbolic tolerances reject; normal/zero tolerance retain violations |
| R3-05 | Finite-difference denominator, numerator and quotient must be finite; Response.sign and Sign also guard | finite resolved extreme payoffs cannot produce a passing infinite derivative; ordinary response remains finite positive |

Reproduce: `python -m unittest pacegame.tests.test_pacegame pacegame.tests.test_audit_020 pacegame.tests.test_audit_021 pacegame.tests.test_audit_022 -v`; run `examples/validate_release.py`, `examples/validate_audit_021.py` and `examples/validate_audit_022.py` into a chosen evidence directory. The first 173 tests remain, with only the current-version assertion updated. The 25 new tests cover these third-audit contracts.

A custom Game overriding payoffs, _payoffs, gross_payoffs, _gross_payoffs, _gross_with_shares or shares must provide its own share_sensitivity(strategy, parameter) expression to receive a channel verdict. Otherwise Competitive skips. A custom hook is a model declaration, not a software proof that the declaration is correct. Built-in activity uses an absolute 1e-12 tolerance and holds decisions fixed. The check does not certify economic competition globally or a Nash equilibrium.

Exact completed runs, environment, package comparisons and manuscript checks are recorded in evidence/ and the accompanying revision report. docs/audit_020.md and docs/audit_021.md are historical revision records, not current execution claims. Public archive, verified author/contact fields and official final-template checks remain pending.
