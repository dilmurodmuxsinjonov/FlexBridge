"""Capture this package's regression evidence without overwriting earlier reviews."""
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent

if __name__ == '__main__':
    candidate_only = sys.argv[1:] == ['targeted']
    prefix = 'targeted_' if candidate_only else ''
    target = ROOT / 'backend/tests/security/test_invitations.py' if candidate_only else ROOT / 'backend'
    started = time.monotonic()
    result = subprocess.run([sys.executable, '-m', 'pytest', str(target), '-q', '--tb=short',
        '--junitxml=' + str(OUTPUT / (prefix + 'junit.xml'))], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (OUTPUT / (prefix + 'pytest_stdout.txt')).write_text(result.stdout, encoding='utf-8')
    (OUTPUT / (prefix + 'pytest_stderr.txt')).write_text(result.stderr, encoding='utf-8')
    summary = {'exit_code': result.returncode, 'elapsed_seconds': round(time.monotonic() - started, 2)}
    if (OUTPUT / (prefix + 'junit.xml')).exists():
        suites = list(ET.parse(OUTPUT / (prefix + 'junit.xml')).getroot().iter('testsuite'))
        summary.update({name: sum(int(s.get(name, 0)) for s in suites) for name in ('tests', 'failures', 'errors', 'skipped')})
    (OUTPUT / (prefix + 'summary.json')).write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(result.stdout[-7000:])
    print(json.dumps(summary))
    raise SystemExit(result.returncode)
