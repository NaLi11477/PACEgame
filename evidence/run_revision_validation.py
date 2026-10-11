"""Run unchanged suite and all current exporters with byte and import receipts."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument('--source-root', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--installed', action='store_true')
a = ap.parse_args()
root, out = a.source_root.resolve(), a.out.resolve()
out.mkdir(parents=True, exist_ok=True)
cwd = out / 'execution'
cwd.mkdir(exist_ok=True)
env = os.environ.copy()
env.pop('PYTHONPATH', None)
env['PYTHONDONTWRITEBYTECODE'] = '1'
if not a.installed:
    env['PYTHONPATH'] = str(root)
    sys.path.insert(0, str(root))
package = Path(importlib.util.find_spec('pacegame').origin).parent
if a.installed:
    assert root not in package.parents, 'Installed verification imported checkout'
wheel = root / 'dist/pacegame-0.2.11-py3-none-any.whl'
wheel_sha = hashlib.sha256(wheel.read_bytes()).hexdigest()

def inventory():
    return {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in package.rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix != '.pyc'}

before = inventory()
commands = [('tests', [sys.executable, str(Path(__file__).with_name('run_test_suite.py')),
                       '--out', str(out/'test_suite')])]
if not a.installed:
    commands[0][1].extend(['--source-root', str(root)])
names = ['validate_release'] + [f'validate_audit_0{n}' for n in range(21, 30)] + ['validate_audit_0210', 'validate_audit_0211']
for name in names:
    cmd = [sys.executable, '-m', 'pacegame.examples.'+name, str(out)]
    if name == 'validate_audit_024':
        cmd += [str(root/'evidence/metadata_tables.json'), str(root/'.github/workflows/tests.yml')]
    if name == 'validate_audit_025':
        cmd += [str(root/'requirements-reproduce.txt')]
    commands.append((name, cmd))
records = []
for name, cmd in commands:
    start = time.monotonic()
    with (out/(name+'.log')).open('w') as log:
        result = subprocess.run(cmd, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    record = {'name': name, 'command': cmd, 'returncode': result.returncode,
              'seconds': time.monotonic()-start, 'outside_checkout': True,
              'cwd': str(cwd), 'package_path': str(package),
              'package_members': len(before), 'package_unchanged': inventory() == before,
              'wheel_unchanged': hashlib.sha256(wheel.read_bytes()).hexdigest() == wheel_sha,
              'wheel_sha256': wheel_sha}
    if name == 'tests' and (out/'test_suite/summary.json').exists():
        record['test_summary'] = json.loads((out/'test_suite/summary.json').read_text())
    records.append(record)
    (out/'execution.json').write_text(json.dumps(records, indent=2)+'\n')
    print(name, result.returncode, flush=True)
    assert record['package_unchanged'] and record['wheel_unchanged'], record
    if result.returncode:
        raise SystemExit(result.returncode)
print('All 13 commands completed, including 12 exporters.', flush=True)
