from pathlib import Path
import shutil,json
A=Path(__file__).resolve().parent.parent;S=A/'work/PACEgame_v0_2_11';B=A/'evidence'
# Preserve parent implementation evidence separately, not as fresh validation.
shutil.move(S/'evidence',A/'parent_evidence_snapshot');(S/'evidence').mkdir()
for p in S.rglob('*'):
 if p.is_file() and p.suffix in {'.py','.toml','.yml','.md','.txt','.json'} and 'vendor' not in p.parts and 'dist' not in p.parts and 'evidence' not in p.parts:
  t=p.read_text();t=t.replace('0.2.10','0.2.11').replace('v0_2_10','v0_2_11');p.write_text(t)
# metadata references must point at the new current audit implementation
m=json.loads((A/'manuscript/metadata_tables.json').read_text());m=json.loads(json.dumps(m).replace('0.2.10','0.2.11').replace('v0_2_10','v0_2_11').replace('audit_0210.md','audit_0211.md'))
for p in (A/'manuscript/metadata_tables.json',S/'evidence/metadata_tables.json'):p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
for n in ['run_test_suite.py','run_revision_validation.py','run_public_probes.py','verify_round7_fixes.py','verify_round8_fixes.py','probe_round9.py','verify_round10_fixes.py','verify_round11_fixes.py','rebuild_and_compare.py','check_artifacts.py','build_tex_proof.py','build_documents.py','report_style.py','verify_release.py','package_revision.py']:
 t=(Path('revision_v0210/evidence')/n).read_text().replace('v0_2_10','v0_2_11').replace('0.2.10','0.2.11')
 if n=='run_revision_validation.py':t=t.replace("['validate_audit_0210']","['validate_audit_0210', 'validate_audit_0211']").replace('All 12 commands completed, including 11 exporters.','All 13 commands completed, including 12 exporters.')
 if n=='rebuild_and_compare.py':t=t.replace("str(A/'build_env/bin/python')","str(A.parent/'revision_v0210/build_env/bin/python')")
 (B/n).write_text(t)
shutil.copyfile('audit_v0210/evidence/depth_report_fields.json',B/'depth_report_fields.json')
for p in (S/'dist').iterdir():p.unlink()
ci=S/'.github/workflows/tests.yml';ci.write_text(ci.read_text().replace("'validate_audit_0210']","'validate_audit_0210','validate_audit_0211']"))
shutil.copyfile('audit_v0210/evidence/probe_round12.py',B/'probe_round12_parent.py')
