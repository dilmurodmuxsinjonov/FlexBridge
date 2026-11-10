"""Explicit, exclusive Q016 takeover. No inferred Codex quota or idle trigger."""
import argparse,datetime,hashlib,json,msvcrt,os,re,subprocess,time,uuid
from pathlib import Path

BASE=Path('D:/Codex/FlexBridge-agents');ROOT=Path('D:/FlexBridge')
AGY='C:/Users/dilmu/AppData/Local/agy/bin/agy.exe'
STATE=BASE/'coordinator_state.json';LOCK=BASE/'master_runner.lock';STOP=BASE/'STOP_MASTER'
FREEZE='764fb98496fa40857acb07844fd09fcafa99b7d6'

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write_json(path,value):
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8');os.replace(temp,path)
def git(*args):
    env={**os.environ,'GIT_TERMINAL_PROMPT':'0'}
    return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,
        encoding='utf8',timeout=30,check=True,env=env).stdout.strip()

def classify_result(returncode,data,stderr):
    """Use structured CLI outcome, never echoed prompt/stderr words as quota."""
    status=str(data.get('status','')).upper()
    finish=str(data.get('finished_reason','')).lower()
    error=data.get('error','')
    error_text=error if isinstance(error,str) else str(error.get('message','')) if isinstance(error,dict) else ''
    if status in {'TIMEOUT','TIMED_OUT','RUNNING'} or finish in {'print_timeout','timeout','timed_out'}:
        return 'continuing_timeout'
    if re.match(r'^print timeout\b',error_text,re.I):return 'continuing_timeout'
    if returncode==0 and status=='SUCCESS':return 'success'
    if returncode==0:return 'needs_inspection'  # contradictory/stale ERROR envelope
    if status!='ERROR':return 'needs_inspection'
    code=str(error.get('code','')) if isinstance(error,dict) else ''
    if code in {'429','RESOURCE_EXHAUSTED','QUOTA_EXCEEDED'}:return 'quota'
    if re.match(r'^(?:Individual quota (?:reached|exceeded|exhausted)\b|Quota (?:exceeded|exhausted)\b|RESOURCE_EXHAUSTED\b|QUOTA_EXCEEDED\b|(?:HTTP )?429\b)',error_text,re.I):
        return 'quota'
    return 'needs_inspection'

def handback_record(previous,expected_generation,confirmed):
    if not confirmed:raise RuntimeError('ACTIVE_TURN_DRAIN_CONFIRMATION_REQUIRED')
    if previous.get('owner')!='ANTIGRAVITY' or previous.get('generation')!=expected_generation:
        raise RuntimeError('STALE_HANDBACK_GENERATION_OR_OWNER')
    return {'owner':'CODEX','generation':expected_generation+1,'status':'HANDED_BACK',
        'handed_back_at':utc(),'previous_run_token':previous.get('run_token'),
        'inflight_turns_stopped_confirmed_by_operator':True,'automatic_quota_detection':False,
        'policy':'Q016 explicit handback, main frozen; integration only'}

class ExclusiveMaster:
    def __init__(self,path=LOCK):self.path=path;self.handle=None
    def __enter__(self):
        self.handle=self.path.open('a+b')
        if self.path.stat().st_size==0:self.handle.write(b'0');self.handle.flush()
        self.handle.seek(0)
        try:msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            self.handle.close();self.handle=None;raise RuntimeError('ANOTHER_MASTER_RUNNER_HOLDS_LOCK') from None
        return self
    def __exit__(self,*args):
        if self.handle:
            self.handle.seek(0);msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1);self.handle.close()

def preflight():
    for attempt in range(3):
        try:
            main_sha=git('ls-remote','origin','refs/heads/main').split()[0];break
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
            if attempt==2:raise
            time.sleep(attempt+1)
    assert main_sha==FREEZE,'MAIN_FREEZE_CHANGED'
    assert git('branch','--show-current') not in ('main','master'),'REFUSE_MAIN_WORKSPACE'
    protocol=ROOT/'ANTIGRAVITY_MASTER_PROTOCOL.md';assert protocol.is_file()
    assert (BASE/'CURRENT_HANDOFF.json').is_file(),'HANDOFF_SNAPSHOT_REQUIRED'
    result=subprocess.run([AGY,'models'],cwd=ROOT,capture_output=True,text=True,encoding='utf8',check=True)
    listed={line.split('\t',1)[0] for line in result.stdout.splitlines() if '\t' in line}
    candidates=[x for x in ['gemini-4-argon-high','gemini-3.8-flash-high','gpt-oss-120b-medium',
        'claude-opus-5-5-high','claude-sonnet-5-5-high'] if x in listed]
    assert candidates,'NO_LISTED_MASTER_MODEL'
    return {'time':utc(),'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),
        'main_frozen_sha':FREEZE,'protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),
        'listed_candidates':candidates,'automatic_quota_detection':False}

def run_master(reason,max_chunks):
    with ExclusiveMaster():
        if STOP.exists():raise RuntimeError('USER_STOP_MARKER_PRESENT')
        checked=preflight();old=json.loads(STATE.read_text(encoding='utf8')) if STATE.exists() else {}
        if old.get('owner')=='ANTIGRAVITY':
            raise RuntimeError('EXPLICIT_HANDBACK_REQUIRED_BEFORE_ANOTHER_MASTER_RUN')
        token=uuid.uuid4().hex
        state={'owner':'ANTIGRAVITY','generation':int(old.get('generation',0))+1,'run_token':token,
            'pid':os.getpid(),'status':'RUNNING','supplied_trigger':reason,
            'trigger_observed_by_script':False,'started_at':utc(),'preflight':checked}
        write_json(STATE,state);chunk=0
        try:
            while not STOP.exists() and (not max_chunks or chunk<max_chunks):
                current=json.loads(STATE.read_text(encoding='utf8'))
                if current.get('owner')!='ANTIGRAVITY' or current.get('run_token')!=token:
                    print('COORDINATOR_OWNERSHIP_CHANGED; no new chunk started');return
                chunk+=1;models=preflight()['listed_candidates'];accepted=False
                next_path=BASE/'MASTER_NEXT.md'
                prior_next_mtime=next_path.stat().st_mtime_ns if next_path.exists() else None
                for model in models:
                    if STOP.exists():break
                    target=BASE/'master_runs'/token/str(chunk)/model;target.mkdir(exist_ok=True,parents=True)
                    task='''You are Antigravity MASTER under user Q016. Explicit supplied trigger: %s.
Read D:/FlexBridge/AGENTS.md, ANTIGRAVITY_MASTER_PROTOCOL.md, four journals,
ANTIGRAVITY_HANDOFF.md and D:/Codex/FlexBridge-agents/CURRENT_HANDOFF.json.
Read MASTER_NEXT.md if present and refresh actual source/PR/CI/process state.
You own the exclusive coordinator lease generation%s token%s. Codex is fenced
from concurrent writes. Preserve user/agent WIP. Main/master FROZEN%s; all PRs
and verified merges ONLY integration/r1-agent-collaboration. You may coordinate
actual Copilot/OpenCode, assign precise isolated tasks, implement and verify each
bounded unit with real native evidence/source pins/full exact-head CI/current
feedback. No live deployment/money/credential/.env/.data/pg_live/admin/reboot work.
No fake tests, invented model/execution/pilot claims. Check STOP_MASTER before
new mutations/delegation; if present, stop and report active work. One bounded
chunk only, then write D:/Codex/FlexBridge-agents/MASTER_NEXT.md with completed
work, evidence, precise next task, ownership, processes/conversations and risks.
Update journals. Distinguish quota from transport; do not duplicate ongoing turns.
If a prior model partly edited before quota, inspect the preserved diff first.
Return a concise actual result; the controller starts the next chunk only after
terminal SUCCESS. FullR1 continues until user stop, not small green milestones.
'''%(reason,state['generation'],token,FREEZE)
                    command=[AGY,'--project','FlexBridge-R1-Agents','--add-dir',str(ROOT),'--add-dir',str(BASE),
                        '--model',model,'--mode','auto','--output-format','json',
                        '--print-timeout','540s','--log-file',str(target/'cli.log'),'-p',task]
                    started=time.monotonic();done=subprocess.run(command,cwd=BASE/'antigravity',capture_output=True,text=True,encoding='utf8')
                    (target/'stdout.raw.json').write_text(done.stdout,encoding='utf8');(target/'stderr.raw.txt').write_text(done.stderr,encoding='utf8')
                    try:data=json.loads(done.stdout)
                    except json.JSONDecodeError:data={}
                    classification=classify_result(done.returncode,data,done.stderr)
                    quota=classification=='quota'
                    receipt={'chunk':chunk,'requested_model':model,'reported_model':data.get('model'),
                        'exit_code':done.returncode,'status':data.get('status'),'conversation_id':data.get('conversation_id'),
                        'seconds':round(time.monotonic()-started,2),'actual_quota_error':quota,
                        'classification':classification,'recorded_at':utc()}
                    write_json(target/'receipt.json',receipt);state['latest_attempt']=receipt;write_json(STATE,state)
                    if classification=='success':
                        (target/'result.md').write_text(data.get('response',''),encoding='utf8');accepted=True;break
                    if not quota:
                        # A print timeout can leave the CLI conversation active. Do
                        # not create a competing turn or release coordinator owner.
                        state['status']='NEEDS_INSPECTION';write_json(STATE,state);return
                if STOP.exists():break
                if not accepted:
                    state['status']='MODELS_LIMITED';write_json(STATE,state);return
                if not next_path.is_file() or next_path.stat().st_mtime_ns==prior_next_mtime:
                    state['status']='MISSING_NEXT_HANDOFF';write_json(STATE,state);return
                time.sleep(2)
            state['status']='USER_STOPPED' if STOP.exists() else 'BOUNDED_RUN_FINISHED'
            write_json(STATE,state)
        except BaseException as error:
            current=json.loads(STATE.read_text(encoding='utf8'))
            if current.get('run_token')==token:
                state['status']='NEEDS_INSPECTION';state['error_type']=type(error).__name__;write_json(STATE,state)
            raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reason',choices=['CodexLimit','UserTakeover'],default='CodexLimit')
    parser.add_argument('--dry-run',action='store_true');parser.add_argument('--check-lock',type=Path)
    parser.add_argument('--handback',action='store_true');parser.add_argument('--confirmed-no-active-turn',action='store_true')
    parser.add_argument('--expected-generation',type=int)
    parser.add_argument('--max-chunks',type=int,default=0);args=parser.parse_args()
    if args.check_lock:
        try:
            with ExclusiveMaster(args.check_lock):print('LOCK_ACQUIRED')
        except RuntimeError:print('LOCK_BUSY');return 23
        return 0
    if args.dry_run:
        result=preflight();result['result']='DRY_RUN_NO_OWNER_CHANGE_NO_AGENT_STARTED'
        write_json(BASE/'master_dry_run_receipt.json',result);print(json.dumps(result));return 0
    if args.handback:
        with ExclusiveMaster():
            previous=json.loads(STATE.read_text(encoding='utf8'))
            result=handback_record(previous,args.expected_generation,args.confirmed_no_active_turn)
            write_json(STATE,result);write_json(BASE/('handback_generation_'+str(result['generation'])+'.json'),result)
            print(json.dumps(result))
        return 0
    run_master(args.reason,args.max_chunks);return 0
if __name__=='__main__':raise SystemExit(main())
