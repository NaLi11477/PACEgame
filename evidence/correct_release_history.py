from pathlib import Path
import json,shutil,subprocess,time,hashlib
A=Path(__file__).resolve().parent.parent;B=A/'evidence';S=A/'work/PACEgame_v0_2_11';old=A.parent/'audit_v0210/work/PACEgame_v0_2_10'
p=S/'README.md';new=p.read_text().split('## Revision 0.2.11\n',1)[1]
t=(old/'README.md').read_text().replace('# PACEgame 0.2.10','# PACEgame 0.2.11',1).replace('dist/pacegame-0.2.10','dist/pacegame-0.2.11');p.write_text(t+'\n## Revision 0.2.11\n\n'+new)
(S/'docs/release_scope.txt').write_text('''PACEgame 0.2.11 implements the Round12 audit revision. R12-01 and R12-02 meet the listed implementation acceptance; a new independent re-audit remains pending.
493 test methods retain all 450 parent methods and add 43 new methods. Twelve exporters cover 41 numbered acceptance groups. Source, full installed wheel and offline core-only results are separately recorded.
Every declared owner objective requires finite-real admission before fixed/skipped/derivative branches. Final comparisons and constrained payoff finite differences retain each candidate's parameters and payoffs before subtraction. Float payoffs remain display values; unavailable precision must propagate explicitly.
Prior retained endpoint, tolerance-sign, ceiling, coefficient and Hessian guards remain. Heuristic binary64 search, necessary local conditions and sampled claims do not certify global optima, continuous-domain propositions or Nash equilibrium.
Author identities, contacts, declarations, permanent public identifiers and current official-template certification remain pending. No new timing, external adoption or empirical application is asserted.
''')
prior=B/'pre_history_label_correction';prior.mkdir()
for e in ('source','wheel','core'):shutil.move(B/f'validation_{e}',prior/f'validation_{e}')
shutil.copyfile(B/'distribution_integrity.json',prior/'distribution_integrity.json')
shutil.copyfile(B/'distribution_build.json',prior/'distribution_build.json')
cmd=[str(A.parent/'revision_v0210/build_env/bin/python'),'-m','build','--sdist','--wheel','--no-isolation','--outdir',str(S/'dist'),str(S)]
start=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True);(B/'distribution_build.log').write_text(r.stdout+r.stderr);r.check_returncode();(B/'distribution_build.json').write_text(json.dumps({'command':cmd,'returncode':r.returncode,'seconds':time.monotonic()-start,'build_environment_reused':True,'description_history_corrected_before_final_validation':True},indent=2)+'\n')
rs=[]
for e in ('wheel','core'):
 cmd=[str(A/f'{e}_env/bin/python'),'-m','pip','install','--force-reinstall','--no-deps','--no-index',str(S/'dist/pacegame-0.2.11-py3-none-any.whl')]
 r=subprocess.run(cmd,capture_output=True,text=True);(B/f'{e}_env_final_install.log').write_text(r.stdout+r.stderr);r.check_returncode();rs.append({'environment':e,'command':cmd,'returncode':r.returncode,'wheel_sha256':hashlib.sha256((S/'dist/pacegame-0.2.11-py3-none-any.whl').read_bytes()).hexdigest()})
(B/'final_install_receipts.json').write_text(json.dumps(rs,indent=2)+'\n')
j=json.loads((B/'setup_notes.json').read_text());j['history_label_correction']='First full validation passed. Corrected the inherited R11 README title to its original v0.2.10 and rewrote current release_scope for R12. Rebuilt metadata and distributions, reinstalled wheels, and reran all three suites and exporters against final wheel. Earlier pass excluded from delivery evidence.';(B/'setup_notes.json').write_text(json.dumps(j,indent=2)+'\n')
print('History corrected and final wheels installed')
