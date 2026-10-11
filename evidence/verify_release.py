"""Portable standard-library verification of the extracted software release."""
from pathlib import Path
import argparse, hashlib, json, tarfile, zipfile
ap=argparse.ArgumentParser();ap.add_argument('--release-root',type=Path)
a=ap.parse_args();root=(a.release_root or Path(__file__).resolve().parent.parent).resolve()
def digest(b): return hashlib.sha256(b).hexdigest()
manifest={}
for line in (root/'SHA256SUMS.txt').read_text().splitlines():
    h,n=line.split('  ',1);assert n not in manifest;manifest[n]=h
eligible=lambda p:p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and not p.name.startswith('.codex-library')
files={p.relative_to(root).as_posix():digest(p.read_bytes()) for p in root.rglob('*')
       if eligible(p) and p!=root/'SHA256SUMS.txt'}
assert files==manifest, 'Software payload missing, extra or modified'
source={p.relative_to(root/'pacegame').as_posix():digest(p.read_bytes())
        for p in (root/'pacegame').rglob('*') if eligible(p)}
with zipfile.ZipFile(root/'dist/pacegame-0.2.11-py3-none-any.whl') as z:
    assert z.testzip() is None
    wheel={n[len('pacegame/'):]:digest(z.read(n)) for n in z.namelist()
           if n.startswith('pacegame/') and not n.endswith('/')}
with tarfile.open(root/'dist/pacegame-0.2.11.tar.gz') as t:
    sdist={m.name.split('/pacegame/',1)[1]:digest(t.extractfile(m).read())
           for m in t.getmembers() if m.isfile() and '/pacegame/' in m.name}
assert source==wheel==sdist and len(source)==61
for p in (root/'pacegame/examples').iterdir():
    if eligible(p): assert p.read_bytes()==(root/'examples'/p.name).read_bytes()
for e,skip in [('source',0),('wheel',0),('core',1)]:
    s=json.loads((root/f'evidence/validation_{e}/test_suite/summary.json').read_text())
    assert s['tests_run']==493 and s['passed']==493-skip and s['skipped']==skip
    assert s['successful'] and not s['failures'] and not s['errors']
print(json.dumps({'version':'0.2.11','payload_files_checked':len(manifest),
                 'package_members_checked':61,'manifest_complete_and_matched':True,
                 'source_wheel_sdist_equal':True,'examples_mirrored':True},indent=2))
