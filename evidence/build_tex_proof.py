"""Build the synchronized TeX source twice and preserve both command logs."""
from pathlib import Path
import json, subprocess, time
A=Path(__file__).resolve().parent.parent
P=A/'manuscript';T=A/'evidence/tex_build';T.mkdir(exist_ok=True)
records=[]
for n in [1,2]:
    cmd=['xelatex','-interaction=nonstopmode','-halt-on-error',f'-output-directory={T}','manuscript.tex']
    start=time.monotonic()
    r=subprocess.run(cmd,cwd=P,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (T/f'pass{n}.stdout.log').write_text(r.stdout)
    records.append({'command':cmd,'cwd':str(P),'returncode':r.returncode,'seconds':time.monotonic()-start})
    (T/'execution.json').write_text(json.dumps(records,indent=2)+'\n')
    r.check_returncode()
log=(T/'manuscript.log').read_text()
assert 'Overfull' not in log and 'Missing character' not in log
print('XeLaTeX twice completed; no overfull boxes or missing characters.')
