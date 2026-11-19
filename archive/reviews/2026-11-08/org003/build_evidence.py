"""Rebuild pinned Git blob inventory and collect existing validation evidence; no DB writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
SOURCE='f118e23e2a0d2d48d08a6ad8fd500f5a43bca9d2'

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def write(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

paths=git('ls-tree','-r','--name-only',SOURCE).decode().splitlines()
selected=[p for p in paths if p.startswith(('backend/app/','backend/alembic/','backend/tests/',
    '.github/','infra/','scripts/')) or p in ('FlexBridge_1_4_schema.sql',
    'specs/v1_4/FlexBridge_model_1_4.json','backend/Dockerfile','backend/alembic.ini',
    'backend/pyproject.toml','backend/requirements.txt')]
files=[]
for path in selected:
    blob=git('show',SOURCE+':'+path)
    files.append(dict(path=path,sha256=hashlib.sha256(blob).hexdigest(),bytes=len(blob)))
write('source_manifest.json',dict(commit=SOURCE,note='SHA256 of pinned Git blob bytes, including tests and configuration.',files=files))

sys.path.insert(0,str(ROOT/'backend'))
from app.main import app
def flatten(routes):
    for route in routes:
        if hasattr(route,'original_router'):
            yield from flatten(route.original_router.routes)
        else:
            yield route

def normalize(path):
    import re
    return re.sub(r'\{[^}]+\}','{}',path)

routes=list(flatten(app.routes))
model=json.loads((ROOT/'specs/v1_4/FlexBridge_model_1_4.json').read_text(encoding='utf-8'))
contracts=[]
for api in model['apis']+model['helper_apis']:
    matches=[r for r in routes if getattr(r,'path',None) and normalize(r.path)==normalize(api['path'])
        and api['method'] in getattr(r,'methods',())]
    status='MISSING'
    if matches:
        status='PLACEHOLDER_501' if all(getattr(getattr(r.endpoint,'__code__',None),'co_name',None)
            =='_canonical_contract_endpoint' for r in matches) else 'EXPLICIT_HANDLER'
    contracts.append(dict(id=api['id'],method=api['method'],path=api['path'],status=status))
write('contracts.json',dict(total=len(contracts),explicit=sum(c['status']=='EXPLICIT_HANDLER' for c in contracts),
    placeholder_501=sum(c['status']=='PLACEHOLDER_501' for c in contracts),missing=sum(c['status']=='MISSING' for c in contracts),
    commit=SOURCE,note='Registration inventory, not acceptance coverage. Ownership helper routes are outside this canonical132 list.',contracts=contracts))
suites=list(ET.parse(OUT/'final_affected_junit.xml').getroot().iter('testsuite'))
write('summary.json',dict(commit=SOURCE,scope='Six affected native PostgreSQL modules; full suite separately in GitHub CI.',
    tests=sum(int(s.get('tests',0)) for s in suites),failures=sum(int(s.get('failures',0)) for s in suites),
    errors=sum(int(s.get('errors',0)) for s in suites),skipped=sum(int(s.get('skipped',0)) for s in suites),
    elapsed_seconds=sum(float(s.get('time',0)) for s in suites),ci_runs=[42503498638],ci_tests=297,
    ci_conclusion='success',pilot_ready=False))
print('Wrote source manifest, canonical registration inventory and validation summary.')
