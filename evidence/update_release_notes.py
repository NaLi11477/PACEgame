from pathlib import Path
import json
A=Path(__file__).resolve().parent.parent;S=A/'work/PACEgame_v0_2_11';old=A.parent/'audit_v0210/work/PACEgame_v0_2_10'
for p in (old/'docs').glob('audit_*.md'):(S/'docs'/p.name).write_bytes(p.read_bytes())
new='''# PACEgame 0.2.11 2026-10-08

- R12-01: admit every declared payoff_for objective at the retained candidate before fixed, skipped-stage or derivative branches. Known non-real/non-finite values are required violations; unknown admission is required unavailable. Different finite owner objectives and negative net payoffs remain legal.
- R12-02: Solution.retained_payoffs binds each final payoff to its own parameters and candidate. Outcome.payoff_value and Solution.payoff_value expose finite-real retained values; binary64 payoffs remain display/compatibility values. Ranking, ties, dominance, crossings and constrained payoff finite differences subtract retained operands first. Unavailable comparison cannot become a zero, tie or weak pass; complete=False or explicit ValueError/skip propagates. Existing absolute thresholds stay unchanged.
- 45 regression methods join 450 parent cases: 495 total. Twelve exporters cover 41 numbered acceptance groups. Source, installed full wheel and offline core installation are validated separately; hosted cross-platform CI remains unexecuted.
- Word, XeLaTeX, metadata, evidence and release manifests are synchronized. Independent re-audit, confirmed authors/declarations, permanent public identifiers and current official-template certification remain pending.

'''
(S/'CHANGELOG.md').write_text(new+(old/'CHANGELOG.md').read_text())
(S/'docs/audit_0211.md').write_text(new+'''## Public behavior and controls

Owner admission covers fixed, interior, lower-corner and skip_optimality paths, including NaN, infinity, unresolved real symbols and imaginary terms down to 10^-400. A complete violation is a completed rejection; complete=False is reserved for unresolved required checks.

At fixed decisions, payoffs A and A+1 retain gap 1 for A=2^53, 2^60 and 10^20, in either strategy order. RL wins with a single tie label; true strict dominance passes and reversed weak dominance fails. A+phi-1/2 crosses at phi=.5 on [.25,.75]; the constrained derivative of A+sigma is 1. Representable offsets, negative owner payoffs, per-player targets, separate candidate coordinates and perturbed parameters are tested.

Legacy manually constructed Solution/Outcome objects without retained mappings fall back to the actual supplied payoff values; they cannot recover digits already lost before construction. Finite differences use separately solved constrained candidates. A result outside binary64 range, including nonzero underflow, raises ValueError without a sign verdict. An unavailable retained ranking raises ValueError and complete is False. Display values can still round two different payoffs identically; use payoff_value for comparisons.

The heuristic search still uses binary64 objective evaluations. Retained final comparisons do not certify search arithmetic, global optima, continuous-domain claims or full Nash interactions.

Run python -m pacegame.tests and python -m pacegame.examples.validate_audit_0211 validation outside the checkout after installation. Independent acceptance is evidence/verify_round12_fixes.py; frozen parent reproduction is evidence/probe_round12_parent.py, whose confirmed-defect exit 1 is expected only on v0.2.10.
''')
p=S/'README.md';p.write_text(p.read_text()+'\n## Revision 0.2.11\n\n'+new.split('\n\n',1)[1]+'See docs/audit_0211.md for retained payoff access, unavailable status and fixed-candidate analytic controls.\n')
p=S/'docs/release_scope.txt';p.write_text(p.read_text()+'\nCurrent v0.2.11: R12-01 and R12-02 implemented; 495 tests (45 new), 12 exporters and 41 numbered groups. Retained payoff comparisons and candidate-bound finite differences; float display and heuristic search remain approximate. Next independent audit pending.\n')
for p in (S/'examples/manuscript_metadata.json',S/'pacegame/examples/manuscript_metadata.json'):
 p.write_bytes((S/'evidence/metadata_tables.json').read_bytes())
inputs=json.loads((A/'evidence/frozen_inputs.json').read_text())
(S/'INPUT_PROVENANCE.json').write_text(json.dumps({'version':'0.2.11','parent_version':'0.2.10','authoritative_audit':'Round12','input_files':inputs,'previous_evidence':'Frozen Round12 evidence retained in complete release prior_audit; parent implementation evidence snapshot remains a separate local input, not new execution.'},indent=2)+'\n')
