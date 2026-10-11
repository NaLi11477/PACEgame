"""Run the unchanged shipped suite with a durable per-test result ledger."""
import argparse
import json
import sys
import time
import unittest
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--source-root', type=Path)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
root = a.source_root.resolve() if a.source_root else None
out = a.out.resolve()
out.mkdir(parents=True, exist_ok=True)
if root: sys.path.insert(0, str(root))
import pacegame
from pacegame.tests import load_suite

class Ledger(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entries = []
    def record(self, test, status, detail=None):
        self.entries.append({'id': test.id(), 'status': status, 'detail': detail})
        (out / 'test_ledger.json').write_text(json.dumps(self.entries, indent=2)+'\n')
    def addSuccess(self, test):
        super().addSuccess(test); self.record(test, 'passed')
    def addFailure(self, test, err):
        super().addFailure(test, err); self.record(test, 'failed', self._exc_info_to_string(err, test))
    def addError(self, test, err):
        super().addError(test, err); self.record(test, 'error', self._exc_info_to_string(err, test))
    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.record(test, 'skipped', reason)
    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self.record(test, 'expected_failure')
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.record(test, 'unexpected_success')

suite = load_suite()
count = suite.countTestCases()
start = time.monotonic()
with (out / 'tests.log').open('w') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=1, resultclass=Ledger).run(suite)
summary = {
    'package_path': str(Path(pacegame.__file__).resolve()),
    'discovered': count, 'tests_run': result.testsRun,
    'passed': sum(x['status'] == 'passed' for x in result.entries),
    'failures': len(result.failures), 'errors': len(result.errors),
    'skipped': len(result.skipped),
    'successful': result.wasSuccessful(), 'seconds': time.monotonic()-start,
    'production_files_modified': False,
    'runner_only_change': 'Explicit stream and durable result ledger; same shipped load_suite().',
}
(out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary), flush=True)
sys.exit(0 if result.wasSuccessful() and result.testsRun == count else 1)
