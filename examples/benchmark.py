"""Repeat successful commands and record environment and observed contention.

No isolated-hardware or platform certification is inferred from load averages.
Run: python examples/benchmark.py --out benchmark.json --repeats 3 --rounds 2
"""
from __future__ import annotations
import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
QUIET = .4

def load():
    try: return os.getloadavg()[0]
    except (OSError, AttributeError): return None

def busy(baseline=None, limit=QUIET):
    current = load()
    return (current > limit, f"load average {current:.2f}") if current is not None else (False, "load unavailable; contention unknown")

def wait_for_quiet(limit=QUIET, patience=0, baseline=None):
    # Retained as an advisory API; no blocking wait or certification.
    return not busy(limit=limit)[0]

def measure(command, repeats=3, rounds=2, gap=0, cwd=None):
    if repeats < 1 or rounds < 1 or gap < 0:
        raise ValueError("positive repeats/rounds and nonnegative gap required")
    runs=[]
    for round_index in range(rounds):
        if round_index and gap: time.sleep(gap)
        for _ in range(repeats):
            before=load()
            start=time.perf_counter()
            done=subprocess.run(command, cwd=cwd, capture_output=True, text=True)
            elapsed=time.perf_counter()-start
            after=load()
            if done.returncode:
                raise RuntimeError(f"command failed ({done.returncode}): {command}; "
                                   f"{done.stderr[-1000:] or done.stdout[-1000:]}")
            runs.append({'seconds':elapsed,'round':round_index+1,
                         'returncode':done.returncode,
                         'load_before':before,'load_after':after})
    times=[r['seconds'] for r in runs]
    return {'command':list(command),'median':statistics.median(times),
            'low':min(times),'high':max(times),'n':len(times),'rounds':rounds,
            'runs':runs,'timing_scope':'wall time including process startup',
            'contention':'unknown' if any(r['load_before'] is None for r in runs)
            else 'observed load; no isolation certification'}

def main(argv=None):
    a=argparse.ArgumentParser()
    a.add_argument('--out',default='benchmark.json')
    a.add_argument('--repeats',type=int,default=3)
    a.add_argument('--rounds',type=int,default=2)
    opts=a.parse_args(argv)
    import sympy
    import pacegame
    record={'version':pacegame.__version__,'python':sys.version,
            'sympy':sympy.__version__,'platform':platform.platform(),
            'processor':platform.processor(),'cpu_count':os.cpu_count(),
            'measurements':[],'scope':'same-host observations; no speed-up comparator'}
    here=os.path.dirname(os.path.abspath(__file__))
    commands=[('repaired CLI',[sys.executable,'-m','pacegame.cli','solve',
                              'preannounce_entry','--repair']),
              ('worked audit',[sys.executable,os.path.join(here,'audit_preannouncement.py')])]
    for label,cmd in commands:
        result=measure(cmd,opts.repeats,opts.rounds)
        result['label']=label
        record['measurements'].append(result)
    with open(opts.out,'w',encoding='utf-8') as f:
        json.dump(record,f,indent=2,allow_nan=False)
    print(opts.out)
    return 0
if __name__=='__main__':
    raise SystemExit(main())
