"""Rebuild pinned Git blob inventory and collect existing validation evidence; no DB writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
SOURCE='ef4a94b61e5fbd67f0b370fe816a20bb858d630a'

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
def result(name):
    suites=list(ET.parse(OUT/name).getroot().iter('testsuite'))
    return dict(tests=sum(int(s.get('tests',0)) for s in suites),failures=sum(int(s.get('failures',0)) for s in suites),
        errors=sum(int(s.get('errors',0)) for s in suites),skipped=sum(int(s.get('skipped',0)) for s in suites),
        elapsed_seconds=sum(float(s.get('time',0)) for s in suites))
write('summary.json',dict(commit=SOURCE,
    native_baseline=dict(commit='fa40e54749dd6300e866f1ecc9a9833497bd4585',**result('affected_junit.xml')),
    native_post_review=dict(commit=SOURCE,scope='Matching replay, negative reviewer outcomes, reset isolation and existing parallel full flow',**result('peer_fix_junit.xml')),
    initial_new_replay_regression=dict(runtime_commit='fa40e54749dd6300e866f1ecc9a9833497bd4585',**result('initial_replay_junit.xml')),
    ci_runs=[42534534532,42534538671],ci_tests=401,ci_conclusion='success',
    ci_elapsed_seconds=[219.40,257.95],
    prior_ci=dict(commit='fa40e54749dd6300e866f1ecc9a9833497bd4585',runs=[42528552035,42528625943],tests=393,conclusion='success'),
    residual_security_issue=47,pilot_ready=False,
    note='Native263 predates the six-line replay fix; post-review native9 plus final complete CI are separate evidence, not a claim of rerunning all263 natively.'))
print('Wrote pinned manifest, canonical registration inventory and separated validation summary.')
