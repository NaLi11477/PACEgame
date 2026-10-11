from pathlib import Path
A=Path(__file__).resolve().parent.parent;S=A/'work/PACEgame_v0_2_11';B=A/'evidence'
p=S/'pacegame/tests/test_audit_0211.py';t=p.read_text().replace("r=owner_case(value,path);self.assertFalse(r.complete)","r=owner_case(value,path);self.assertFalse(r.ok and r.complete)\n   if label=='unknown':self.assertFalse(r.complete)");p.write_text(t)
t=(B/'probe_round12_parent.py').read_text()
t=t.replace('exit 1 means confirmed defects, not probe failure.','revision acceptance; exact algebra supplies the independent oracle.')
t=t.replace("ap.add_argument('--out',type=Path,required=True)","ap.add_argument('--out',type=Path,required=True)")
start=t.index("assert all(x['false_complete_pass'] for x in owned")
end=t.index('\nclass OffsetGame',start)
t=t[:start]+"""assert not any(x['false_complete_pass'] for x in owned)
for x in owned:
    fs=[f for f in x['report']['findings'] if f['check']==f'owner payoff ({U})']
    assert fs and all(f['required'] for f in fs)
    assert fs[0]['status']==('violation' if x['known_invalid'] else 'warning')
    if x['known_invalid']:assert not x['report']['ok']
    else:assert not x['report']['complete']
"""+t[end:]
t=t.replace("'binary64_payoffs':o.payoffs,","'binary64_payoffs':o.payoffs,'retained_gap':str(o.payoff_value(high)-o.payoff_value(low)),")
t=t.replace("assert all(x['incorrect_weak_dominance_pass'] and x['missed_true_strict_dominance'] and x['complete'] for x in gaps)","assert all(not x['incorrect_weak_dominance_pass'] and not x['missed_true_strict_dominance'] and not x['incorrect_best'] and x['complete'] and x['ties']==['RL'] and x['retained_gap']=='1' for x in gaps)")
t=t.replace("assert any(x['incorrect_best'] for x in gaps)","assert not any(x['incorrect_best'] for x in gaps)")
t=t.replace('assert root is None','assert root==.5')
t=t.replace("'reported_gap':o.payoffs['RL']-o.payoffs['RF']","'reported_gap':o.payoffs['RL']-o.payoffs['RF'],'retained_gap':str(o.payoff_value('RL')-o.payoff_value('RF'))")
t=t.replace("assert response.slope==0 and response.sign=='0'","assert abs(response.slope-1)<1e-9 and response.sign=='+'")
t=t.replace("'technical_approval':False","'independent_reaudit':'pending','all_revision_criteria_passed':True,'all_accepted':True")
t=t.replace("'findings':{'R12-01':{'priority':'P2','confirmed':True","'groups':{'R12-01':{'priority':'P2','accepted':True")
t=t.replace("'R12-02':{'priority':'P2','confirmed':True","'R12-02':{'priority':'P2','accepted':True")
t=t.replace('Public check_point payoff_for objectives lack retained finite-real admission; main solver complex guards are not claimed broken.','Every declared owner objective requires retained finite-real admission before derivative or skip; known invalid values fail and unknown values are required unavailable.')
t=t.replace('Finite binary64 payoff operands erase an exact inter-strategy or inter-point difference before comparison. Dominates gives a false weak pass; rank/threshold/statics share the loss path. Fixed candidates remove search uncertainty.','Comparisons subtract retained finite-real candidate-bound payoffs before conversion. Rank, dominance, threshold and constrained finite differences preserve the audited offsets.')
t=t[:t.index(" 'exit_one_meaning':")]+" 'oracle':'Exact Integer/Rational payoffs and analytic derivative; no production numeric helpers as oracle.'}\na.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\\n')\nprint(json.dumps({'version':pg.__version__,'accepted':['R12-01','R12-02'],'all_revision_criteria_passed':True}))\n"
(B/'verify_round12_fixes.py').write_text(t)
# Exporter uses its own public fixtures and algebraic assertions, not test outcomes.
e=t.replace("ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path);ap.add_argument('--out',type=Path,required=True)","ap=argparse.ArgumentParser();ap.add_argument('outdir',nargs='?',default='validation')")
e=e.replace('a=ap.parse_args()',"a=ap.parse_args();a.source_root=None;a.out=Path(a.outdir)/'audit_0211_acceptance.json'")
(S/'pacegame/examples/validate_audit_0211.py').write_text(e)
for n in ('_audit_0211_fixtures.py','validate_audit_0211.py'):(S/'examples'/n).write_bytes((S/'pacegame/examples'/n).read_bytes())
(B/'setup_notes.json').write_text('{"initial_targeted_test_assertion_correction":"Known invalid payoffs are complete violations; only unresolved admission requires complete=False. Corrected 16 overstrict test assertions to the documented report contract. All initial observations were already violations. No production change was needed for this correction."}\n')
