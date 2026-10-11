# Fourth-audit revision: PACEgame 0.2.3

Parent: frozen 0.2.2. Input: PACEgame_v0_2_2_Audit_Round4.docx. INPUT_PROVENANCE.json binds both to SHA-256.

| Finding | Corrected contract | Acceptance |
| --- | --- | --- |
| R4-01 | Type-aware recursive keys and values; unordered mappings/sets | int/string, same-named Symbol assumptions and nested key mutation match fresh/invalidate/51/16000; insertion order ignored; typed values and ordered sequences tested |
| R4-02 | Sign grammar d pi_<player> / d <parameter>; bind current focal/rival and validate before samples | x derivative +160/16136289, y derivative negative; rival positive fails and negative passes; unknown/malformed targets reject; custom names and flat/overflow controls |
| R4-03 | Materialize sweep strategy pool once; early validation | five iterable forms yield identical three-point scans; one-shot strategy/value iterables consumed once; invalid pools reject even with empty values |

Run `python -m unittest discover -s pacegame/tests -v` and `python examples/validate_audit_023.py validation`. Exact completed source/wheel test counts and environment are recorded in evidence/. Historical audit_020/021/022 documents retain their original scope.

Sign supports current-player payoffs only. Decision responses stay in analyze.statics.derivative(quantity=<decision name>); payoff gaps require quantity="payoff". Unknown target, parameter or strategy is a malformed request, not a skipped or passing proposition. Player/parameter tokens contain no whitespace or slash.

Cache state support is limited to scalar/SymPy values and their acyclic public builtin containers, dictionary/dataclass fields and inherited slots. Private, cyclic or opaque extensions need an explicit supported representation and invalidate after mutation. A fingerprint is not proof of a custom model's correctness.

Empty sweep values return [] after strategy-pool validation. Nonempty unique admitted Strategy objects are required, including matching flags; values and a one-shot strategy pool are each consumed once.

Tests and sampled claims do not certify global optima, continuous-domain propositions, Nash, empirical adoption or unexecuted platform/version combinations. Author/contact, permanent public archives and official final-template verification remain pending.
