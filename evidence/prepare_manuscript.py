"""Synchronize v0.2.11 prose from the frozen v0.2.10 shared content."""
from pathlib import Path
import json,re
A=Path(__file__).resolve().parent.parent;B=A/'evidence';P=A/'manuscript'
c=json.loads((P/'manuscript_content.json').read_text().replace('0.2.10','0.2.11'))
c['abstract']=c['abstract'].replace('450 tests','493 tests').replace('Final payoff comparisons guard tested cancellation.','Retained payoff differences guard tested cancellation.')
x=c['sections'][1][1][1][1]
x[2]=x[2].replace('Net and supplied gross payoffs require finite-real evidence before conversion; known invalid values fail and unknown values prevent completion.','Net, supplied gross and every declared payoff_for owner objective require finite-real evidence before conversion or derivative skipping; known invalid values fail and unknown values prevent completion, including fixed and earlier-stage decisions.')
x=c['sections'][1][1][2][1]
x[2]=x[2].replace('Difference denominators, numerators and final slopes must be finite. Overflow raises a numerical-range error,','Each solution retains payoffs with its own parameters and candidate. Ranking, ties, dominance, crossings and payoff differences subtract retained operands before conversion; float payoffs remain display values. Unknown comparisons prevent completion or produce explicit errors/skips. Absolute dominance and tie thresholds remain 1e-12 and 1e-9. Difference denominators, numerators and final slopes must be finite. Nonzero result underflow or overflow raises a numerical-range error,')
c['sections'][2][1][1][1]+='\npython examples/validate_audit_0211.py validation'
c['sections'][2][1][7]=(
 'Source, full-wheel and core-only environments each run 493 tests: 450 parent cases and 43 new regressions. '
 'Owner-payoff admission covers fixed, interior, lower-corner and skipped-stage paths: known complex, NaN and infinite values fail; unknown values remain incomplete. Different finite objectives and negative nets remain valid. '
 'Fixed-candidate payoffs A and A+1 retain gap 1 at A=2^53, 2^60 and 10^20 in either strategy order. RL wins, strict dominance passes and reversed weak dominance fails. '
 'A+phi-1/2 crosses A at phi=0.5; the constrained derivative of A+sigma is 1. Controls cover representable offsets, absolute tolerances, player targets and separately bound candidates and perturbations. '
 'Prior interval, coefficient, retained-ceiling and Hessian controls remain valid; unstable search candidates remain excluded. Twelve exporters exercise 41 groups in all three environments, with 17 metadata labels matching the depth report. Independent public-interface probes reproduce the parent defects and accept the revision. Hosted CI remains unexecuted.')
c['sections'][2][1][8]=c['sections'][2][1][8].replace('The benchmark records','Historical v0.2.10 benchmark records').replace('Shared-host measurements do not certify isolation or comparative speed.','This revision does not add timing; shared-host measurements do not certify isolation or comparative speed.')
c['sections'][4][1][0]=c['sections'][4][1][0].replace('finite-real payoff admission and ceiling differences','owner-payoff admission and retained inter-candidate differences')
# Keep historical conservative body limit while retaining scope and limitations.
c['sections'][0][1][3]='Version 0.2.11 retains counterexamples to finite-limit mislabelling, unevaluable claims and unsuccessful benchmarks. Checks establish covered behavior; unchecked properties remain unresolved.'
c['sections'][4][1][1]='Future work includes search refinement, follower ties, decision-dependent domains and independent global comparisons. Empirical applications need calibration. Confirmed authors, declarations and permanent public identifiers remain necessary before submission.'
c['sections'][0][1][1]='PACEgame connects reusable lifecycles, demand-share rules and decision ownership to payoffs, domains, candidate searches and reports. Users can change demand assumptions within one inspection procedure. Its contribution is an auditable computational workflow rather than a new entry-timing theorem.'
c['sections'][0][1][4]='Researchers, instructors and reviewers are the intended users. Inputs specify stylized models; empirical adoption or policy applications require separate calibration. External uptake and published companion-study replication are unverified. The unavailable companion study remains a clearly identified legacy claim inventory.'
def flat(xs):
 for x in xs:
  if isinstance(x,str):yield x
  elif x[0]=='code':yield x[1]
  else:yield from flat(x[1])
wc=lambda s:len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b",s))
c['body_word_count']=wc(' '.join(s for _,xs in c['sections'] for s in flat(xs)));c['abstract_word_count']=wc(c['abstract'])
assert c['body_word_count']<=3000 and c['abstract_word_count']<=250,(c['body_word_count'],c['abstract_word_count'])
for p in (B/'manuscript_content.json',P/'manuscript_content.json'):p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
s=B/'build_documents.py';t=s.read_text().replace('450 tests discovered; 39 audit groups configured','493 tests discovered; 41 audit groups configured')
t=t.replace('the ten numbered audit acceptance files 021 through 029 and 0210. The last three rows summarize the R11 fixes and controls.','the eleven numbered audit acceptance files 021 through 029, 0210 and 0211. The last two rows summarize the R12 fixes and controls.')
t=t.replace('\ndef font(run,',"\nedge_rows += [\n ('Owner payoff admission','payoff_for; fixed / interior / lower / skipped','known invalid fails; unknown incomplete; finite negative controls pass'),\n ('Retained payoff differences','A=2^53 / 2^60 / 10^20; exact gap 1','RL ranks first; weak reverse fails; crossing .5; slope 1')\n]\n\ndef font(run,")
s.write_text(t)
(P/'README.txt').write_text(f"Synchronized PACEgame v0.2.11 editable Word and XeLaTeX review manuscript. Body words: {c['body_word_count']}; abstract: {c['abstract_word_count']}.\nCompile manuscript.tex with xelatex twice. TeX Gyre Termes or Latin Modern Roman, DejaVu Sans Mono and standard TeX Live packages are required.\nHistorical depth-report structure and conservative 3000/250 word limits are used; current official-template certification remains pending.\nAuthor identity, support contact, public source/archive identifiers and author declarations remain to be confirmed.\nCurrent validation JSON is in data; benchmark_v0210.json is historical, with no new timing claim.\n")
print(c['body_word_count'],c['abstract_word_count'])
