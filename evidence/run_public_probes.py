"""Reexecute independently maintained probes against the requested import path."""
from pathlib import Path
import argparse, json, os, subprocess, sys, time
ap=argparse.ArgumentParser()
ap.add_argument('--source-root', type=Path)
ap.add_argument('--out', type=Path, required=True)
a=ap.parse_args()
B=Path(__file__).resolve().parent
out=a.out.resolve(); out.mkdir(parents=True, exist_ok=True)
env=os.environ.copy(); env.pop('PYTHONPATH', None); env['PYTHONDONTWRITEBYTECODE']='1'
records=[]
for n, name in [(7,'verify_round7_fixes.py'),(8,'verify_round8_fixes.py'),
                (9,'probe_round9.py'),(10,'verify_round10_fixes.py'),(11,'verify_round11_fixes.py'),(12,'verify_round12_fixes.py')]:
    cmd=[sys.executable,str(B/name),'--out',str(out/f'round{n}.json')]
    if a.source_root: cmd += ['--source-root',str(a.source_root.resolve())]
    start=time.monotonic()
    with (out/f'round{n}.log').open('w') as f:
        result=subprocess.run(cmd,cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT)
    records.append({'round':n,'command':cmd,'returncode':result.returncode,
                    'seconds':time.monotonic()-start,'outside_checkout':True})
    (out/'execution.json').write_text(json.dumps(records,indent=2)+'\n')
    print(n,result.returncode,flush=True)
    if result.returncode: raise SystemExit(result.returncode)
