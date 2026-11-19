"""Rebuild pinned Git blob inventory and collect existing validation evidence; no DB writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
SOURCE='1368ee528236bce8e9e7b52fd0fe799e2ecbac30'

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
    commit=SOURCE,note='Registration inventory, not acceptance coverage. No canonical handler added in this security fix.',contracts=contracts))
def result(name):
    suites=list(ET.parse(OUT/name).getroot().iter('testsuite'))
    return dict(tests=sum(int(s.get('tests',0)) for s in suites),failures=sum(int(s.get('failures',0)) for s in suites),
        errors=sum(int(s.get('errors',0)) for s in suites),skipped=sum(int(s.get('skipped',0)) for s in suites),
        elapsed_seconds=sum(float(s.get('time',0)) for s in suites))
write('summary.json',dict(commit=SOURCE,
    native_baseline=dict(commit='d88ebafb902aec7cfb1caf1afbc096d3fdd96b45',new_cases=result('new_junit.xml'),old_affected=result('affected_junit.xml')),
    native_replay_delta=dict(commit='895fb8c180bd35b8e8699ff023aea1342bae7a3d',**result('post_review_junit.xml')),
    native_final=dict(commit=SOURCE,**result('final_new_junit.xml')),
    initial_regressions=dict(runtime_commit='5856dc6b6f73ac2f42f5e98e5993d4604a17c336',
        refund=result('initial_junit.xml'),checkout_org_wait=result('checkout_initial_junit.xml'),
        target_wait_repeat=result('target_initial_junit.xml')),
    ci_runs=[42564327339,42564331479],ci_tests=582,ci_conclusion='success',ci_elapsed_seconds=[437.43,441.90],
    prior_ci=dict(commit='d88ebafb902aec7cfb1caf1afbc096d3fdd96b45',runs=[42563376429,42563380627],
        tests=579,conclusion='success',elapsed_seconds=[429.74,381.18]),
    excluded_scope=['Quota publish/transition assurance','Trusted provider callback/worker policy changes',
        'Live merchant/provider integration and secret rotation','Browser/hardware/DR/pilot acceptance'],
    pilot_ready=False,
    note='Final runtime matches d88ebaf. Native final78 reruns prior75 plus added3; old137 and intermediate3 are separate overlapping evidence, not added as distinct coverage or a native full-suite claim. Repeated initial target subset is not distinct vulnerabilities.'))
print('Wrote pinned manifest, canonical registration inventory and separated validation summary.')
