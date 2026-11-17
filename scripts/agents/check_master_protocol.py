"""Windows-only controller boundary checks; never launches an actual master."""
import importlib.util,json,subprocess,sys,uuid
from pathlib import Path

def main():
    if sys.platform!='win32':raise RuntimeError('WINDOWS_PROTOCOL_CHECK_REQUIRES_MSVCRT')
    here=Path(__file__).resolve().parent;runner=here/'antigravity_master_runner.py'
    spec=importlib.util.spec_from_file_location('checked_master',runner)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    state=Path('D:/Codex/FlexBridge-agents/coordinator_state.json')
    before=state.read_bytes() if state.exists() else None
    samples={s['name']:s for s in json.loads((here/'outcome_samples.json').read_text(encoding='utf8'))['samples']}
    cases=[('actual_print_timeout','continuing_timeout'),('actual_quota','quota'),
           ('actual_stale_zero_exit_error','needs_inspection')]
    checks={}
    for name,expected in cases:
        case=samples[name]
        checks[name]=module.classify_result(case['returncode'],case['data'],'echoed quota limits')==expected
    checks['stderr_only_not_quota']=module.classify_result(3,{'status':'ERROR','error':'Permission denied'},
        'Individual quota reached')=='needs_inspection'
    checks['structured_provider_quota']=module.classify_result(3,{'status':'ERROR',
        'error':{'code':'RESOURCE_EXHAUSTED','message':'provider quota'}},'')=='quota'
    previous={'owner':'ANTIGRAVITY','generation':8,'run_token':'isolated-test'}
    for name,generation,confirmed in [('unconfirmed_handback_denied',8,False),('stale_handback_denied',7,True)]:
        try:module.handback_record(previous,generation,confirmed)
        except RuntimeError:checks[name]=True
        else:checks[name]=False
    handed=module.handback_record(previous,8,True)
    checks['confirmed_handback_generation']=handed['owner']=='CODEX' and handed['generation']==9
    directory=Path('D:/Codex/FlexBridge-agents/protocol-tests');directory.mkdir(exist_ok=True,parents=True)
    lock=directory/(uuid.uuid4().hex+'.lock')
    def attempt():return subprocess.run([sys.executable,str(runner),'--check-lock',str(lock)],capture_output=True,text=True)
    with module.ExclusiveMaster(lock):
        blocked=attempt();checks['second_process_lock_denied']=blocked.returncode==23 and blocked.stdout.strip()=='LOCK_BUSY'
    released=attempt();checks['lock_released']=released.returncode==0 and released.stdout.strip()=='LOCK_ACQUIRED'
    checks['real_owner_unchanged']=(state.read_bytes() if state.exists() else None)==before
    assert all(checks.values()),checks
    result={'checks':checks,'actual_master_started':False,'live_handback':False,'automatic_quota_detector':False}
    (directory/'latest_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result));return 0

if __name__=='__main__':raise SystemExit(main())
