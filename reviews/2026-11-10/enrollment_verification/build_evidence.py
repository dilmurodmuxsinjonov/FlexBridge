"""Rebuild pinned Git blob inventory and collect existing validation evidence; no DB writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
SOURCE=sys.argv[1] if len(sys.argv)>1 else ''
if not SOURCE:raise SystemExit('Pass the source commit represented by this evidence snapshot')

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def write(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

if git('diff','--name-only',SOURCE,'--','backend/app','backend/alembic','backend/tests',
    'backend/requirements.txt','specs/v1_4/FlexBridge_model_1_4.json').strip():
    raise SystemExit('Current runtime/test source differs from pinned validation commit')

paths=git('ls-tree','-r','--name-only',SOURCE).decode().splitlines()
selected=[p for p in paths if p.startswith(('backend/app/','backend/alembic/','backend/tests/',
    '.github/','infra/','scripts/')) or p in ('FlexBridge_1_4_schema.sql',
    'specs/v1_4/FlexBridge_model_1_4.json','backend/Dockerfile','backend/alembic.ini',
    'backend/pyproject.toml','backend/requirements.txt','backend/INSTITUTION_ONBOARDING.md','backend/STORAGE_VERSIONS.md','backend/FILE_AUTHORITY.md','backend/CANDIDATE_AUTHORITY.md','backend/ENROLLMENTS.md')]
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
    commit=SOURCE,note='Registration inventory, not acceptance coverage. Enrollment adds API027/034 handlers; registration is not functional/security acceptance.',contracts=contracts))
def result(name):
    suites=list(ET.parse(OUT/name).getroot().iter('testsuite'))
    return dict(tests=sum(int(s.get('tests',0)) for s in suites),failures=sum(int(s.get('failures',0)) for s in suites),
        errors=sum(int(s.get('errors',0)) for s in suites),skipped=sum(int(s.get('skipped',0)) for s in suites),
        elapsed_seconds=sum(float(s.get('time',0)) for s in suites))
results={p.name:result(p.name) for p in sorted(OUT.glob('*junit.xml'))}
write('native_results.json',results)
print('Wrote pinned Git-blob manifest, canonical registration inventory and separated native results.')
