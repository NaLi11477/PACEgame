"""Rebuild the newly created sdist and compare source, wheels and installations."""
from pathlib import Path
import hashlib, json, os, subprocess, tarfile, time, zipfile
A=Path(__file__).resolve().parent.parent; S=A/'work/PACEgame_v0_2_11'; B=A/'evidence'
env=os.environ.copy(); env.pop('PYTHONPATH',None); env['PYTHONDONTWRITEBYTECODE']='1'
sdist=S/'dist/pacegame-0.2.11.tar.gz'; wheel=S/'dist/pacegame-0.2.11-py3-none-any.whl'
build=A/'rebuild_sdist'; build.mkdir(exist_ok=True)
with tarfile.open(sdist) as t:
    t.extractall(build,filter='data')
cmd=[str(A.parent/'revision_v0210/build_env/bin/python'),'-m','build','--wheel','--no-isolation',
     '--outdir',str(A/'rebuilt_dist')]
start=time.monotonic()
r=subprocess.run(cmd,cwd=build/'pacegame-0.2.11',env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(B/'sdist_rebuild.log').write_text(r.stdout)
r.check_returncode()
rebuilt=A/'rebuilt_dist'/wheel.name
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():digest(p) for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
source=inventory(S/'pacegame')
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    w={n[len('pacegame/'):]:hashlib.sha256(z.read(n)).hexdigest()
       for n in z.namelist() if n.startswith('pacegame/') and not n.endswith('/')}
with zipfile.ZipFile(rebuilt) as z:
    rw={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
with zipfile.ZipFile(wheel) as z:
    ow={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
sd=inventory(build/'pacegame-0.2.11/pacegame')
installed={}
for name in ['wheel_env','core_env']:
    paths=list((A/name/'lib').glob('python*/site-packages/pacegame'))
    assert len(paths)==1
    installed[name]=inventory(paths[0])
receipt={'sdist_build_command':cmd,'sdist_build_returncode':r.returncode,
         'sdist_build_seconds':time.monotonic()-start,
         'fresh_distribution_names':[wheel.name,sdist.name],
         'wheel_sha256':digest(wheel),'sdist_sha256':digest(sdist),
         'rebuilt_wheel_sha256':digest(rebuilt),'wheel_bytes_identical':digest(wheel)==digest(rebuilt),
         'wheel_all_member_bytes_identical':ow==rw,'package_members':len(source),
         'source_wheel_sdist_identical':source==w==sd,
         'installed_package_identical':{name:data==source for name,data in installed.items()},
         'source_member_hashes':source}
(B/'distribution_integrity.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert receipt['source_wheel_sdist_identical'] and receipt['wheel_all_member_bytes_identical']
assert all(receipt['installed_package_identical'].values())
print(json.dumps({k:v for k,v in receipt.items() if k!='source_member_hashes'},indent=2))
