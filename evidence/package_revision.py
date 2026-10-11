"""Freeze reviewed deliverables, then check complete payload manifests and ZIPs."""
from pathlib import Path
import hashlib, io, json, shutil, subprocess, zipfile
A=Path(__file__).resolve().parent.parent;B=A/'evidence';S=A/'work/PACEgame_v0_2_11';P=A/'manuscript';O=A/'outputs'
assert json.loads((B/'manuscript_visual_review.json').read_text())['accepted']
assert json.loads((B/'report_visual_review.json').read_text())['accepted']
assert json.loads((B/'revision_summary.json').read_text())['independent_reaudit']=='pending'
def sha(data):return hashlib.sha256(data).hexdigest()
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
# Current evidence is kept apart from the parent audit archive and the earlier
# metadata-reference pass. Runtime environments and upload helpers never enter.
skip={'manuscript_render','tex_build','report_render','pre_metadata_reference_correction','pre_history_label_correction','__pycache__'}
for src in B.rglob('*'):
    rel=src.relative_to(B)
    if not src.is_file() or any(part in skip for part in rel.parts) or src.suffix in {'.png','.pyc'} or src.name in {'targeted_initial.log','compare_initial_validation.py','portable_release_verification.log'}:continue
    copy(src,S/'evidence'/rel)
copy(B/'manuscript_content.json',P/'manuscript_content.json')
for src in (B/'validation_source').glob('*.json'):
    if src.name!='execution.json':copy(src,P/'data'/src.name)
copy(B/'benchmark_v0210.json',P/'data/benchmark_v0210.json')
copy(B/'manuscript_render/PACEgame_SoftwareX_Manuscript_v0_2_11.pdf',P/'word_proof.pdf')
copy(B/'tex_build/manuscript.pdf',P/'manuscript_proof.pdf')
def payload(root):
    return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and p!=root/'SHA256SUMS.txt' and '__pycache__' not in p.parts
            and p.suffix!='.pyc' and not p.name.startswith('.codex-library')}
def write_manifest(root):
    m=payload(root)
    (root/'SHA256SUMS.txt').write_text(''.join(f'{h}  {n}\n' for n,h in m.items()))
    return m
def makezip(root,name,outname):
    m=write_manifest(root);zpath=O/outname
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n in sorted(m):z.write(root/n,name+'/'+n)
        z.write(root/'SHA256SUMS.txt',name+'/SHA256SUMS.txt')
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        got={n.removeprefix(name+'/'):sha(z.read(n)) for n in z.namelist()
             if n!=name+'/SHA256SUMS.txt'}
        assert got==m
        assert z.read(name+'/SHA256SUMS.txt')==(root/'SHA256SUMS.txt').read_bytes()
    return {'filename':outname,'bytes':zpath.stat().st_size,'sha256':sha(zpath.read_bytes()),
            'members':len(m)+1,'manifest_payload_files':len(m),'crc_passed':True,
            'manifest_complete_and_matched':True}
write_manifest(S)
r=subprocess.run(['python',str(S/'evidence/verify_release.py'),'--release-root',str(S)],text=True,capture_output=True)
(B/'portable_release_verification.log').write_text(r.stdout+r.stderr);r.check_returncode()
records=[]
records.append(makezip(S,'PACEgame_v0_2_11','PACEgame_v0_2_11_software.zip'))
records.append(makezip(P,'PACEgame_Manuscript_v0_2_11_XeLaTeX','PACEgame_Manuscript_v0_2_11_XeLaTeX.zip'))
stage=A/'package/PACEgame_v0_2_11_Complete_Release'
if stage.exists():shutil.rmtree(stage)
stage.mkdir(parents=True)
for name in ['PACEgame_v0_2_11_software.zip','PACEgame_Manuscript_v0_2_11_XeLaTeX.zip',
             'PACEgame_SoftwareX_Manuscript_v0_2_11.docx','PACEgame_v0_2_11_Revision_and_Validation.docx']:
    copy(O/name,stage/name)
copy(P/'word_proof.pdf',stage/'proofs/word_manuscript.pdf')
copy(P/'manuscript_proof.pdf',stage/'proofs/tex_manuscript.pdf')
copy(B/'report_render/PACEgame_v0_2_11_Revision_and_Validation.pdf',stage/'proofs/revision_report.pdf')
for name in ['PACEgame_v0_2_10_Audit_Round12.docx','PACEgame_v0_2_10_Audit_Round12_Evidence.zip']:
    copy(A/'inputs'/name,stage/'prior_audit'/name)
copy(B/'probe_parent_defects.json',stage/'prior_audit/parent_defects_reproduced.json')
(stage/'README.txt').write_text('PACEgame v0.2.11 review release, 8 October 2026.\nSoftware, editable Word manuscript, synchronized XeLaTeX sources/data/proofs and Chinese revision report are included.\nThe two Round12 findings pass this implementation acceptance. The next independent audit, publication identities/archives and official-template certification remain pending.\nThe frozen Round12 report and evidence are in prior_audit; exact parent software/manuscript input hashes are identified by INPUT_PROVENANCE.json.\nUnzip the software archive, then see README.md and evidence/README_evidence.txt. Run python evidence/verify_release.py to check software payload bytes.\n')
records.append(makezip(stage,stage.name,'PACEgame_v0_2_11_Complete_Release.zip'))
with zipfile.ZipFile(O/'PACEgame_v0_2_11_Complete_Release.zip') as z:
    pref=stage.name+'/'
    for name in ['PACEgame_v0_2_11_software.zip','PACEgame_Manuscript_v0_2_11_XeLaTeX.zip',
                 'PACEgame_SoftwareX_Manuscript_v0_2_11.docx','PACEgame_v0_2_11_Revision_and_Validation.docx']:
        assert z.read(pref+name)==(O/name).read_bytes()
    with zipfile.ZipFile(io.BytesIO(z.read(pref+'PACEgame_Manuscript_v0_2_11_XeLaTeX.zip'))) as t:
        assert t.read('PACEgame_Manuscript_v0_2_11_XeLaTeX/PACEgame_SoftwareX_Manuscript_v0_2_11.docx')==(O/'PACEgame_SoftwareX_Manuscript_v0_2_11.docx').read_bytes()
receipt={'version':'0.2.11','archives':records,'nested_deliverables_byte_equal':True,
         'portable_release_verifier_exit':0,'all_checks_passed':True}
(O/'packaging_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
