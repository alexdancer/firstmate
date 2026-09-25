import os, subprocess, pathlib, json, time, hashlib, shutil
root=pathlib.Path.cwd(); scratch=root/'.local-test-tmp/live'; scratch.mkdir(parents=True,exist_ok=True)
ev=pathlib.Path('/Users/alex/.no-mistakes/evidence/01M3BH9GJAQT2Z7T9F8BAK50GD')
env=os.environ.copy()
for k in ['HERDR_ENV','HERDR_PANE_ID','HERDR_TAB_ID','HERDR_WORKSPACE_ID','HERDR_SOCKET_PATH','HERDR_SESSION']: env.pop(k,None)
env.update(TMPDIR=str(root/'.local-test-tmp'), FM_HERDR_LAB_STATE_DIR=str(scratch/'labs'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',FM_GATE_REFUSE_BYPASS='1')
helper=str(root/'bin/fm-herdr-lab.sh'); transcript=[]; ids=[]
def run(args, e=None, check=True):
    p=subprocess.run([str(x) for x in args],env=e or env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    if check and p.returncode: raise RuntimeError(f'{args}: {p.stdout}')
    return p
session=run([helper,'name','launch-gate']).stdout.strip()
def lab(*a): return run([helper,'run',session,*a]).stdout
def note(s):
    print(s,flush=True); transcript.append(s)
def waitfile(p,secs=12):
    deadline=time.time()+secs
    while time.time()<deadline:
        if p.exists(): return True
        time.sleep(.1)
    return False
baseline=root/'bin/.nm-baseline-spawn.sh'
baseline.write_text(run(['git','show','4be8a409597572ad2e29bb6186dc71d4ec3bb787:bin/fm-spawn.sh']).stdout); baseline.chmod(0o755)
def case(label,spawn,blocked=False,long=False):
    d=scratch/label; d.mkdir(); project=d/'project'; wt=d/'candidate'; home=d/'home'; marker=d/'started.json'
    project.mkdir(); (home/'state').mkdir(parents=True); (home/'config').mkdir()
    ident=f'nmgate-{label}-{os.getpid()}'; ids.append(ident)
    run(['git','init','-q',project]); run(['git','-C',project,'config','user.name','Live Test']);run(['git','-C',project,'config','user.email','test@example.invalid'])
    (project/'candidate.txt').write_text('preserved candidate\n');run(['git','-C',project,'add','.']);run(['git','-C',project,'commit','-qm','candidate'])
    run(['git','-C',project,'worktree','add','-qb',f'fm/{ident}',wt])
    (wt/'candidate.txt').write_text('preserved candidate with staged change\n'); run(['git','-C',wt,'add','candidate.txt']);(wt/'untracked.txt').write_text('uncommitted candidate must survive\n')
    before=run(['git','-C',wt,'diff','--cached','--binary']).stdout+(wt/'untracked.txt').read_text()
    for key,val in [('backlog-backend','manual'),('herdr-presentation-spaces','off')]: (home/'config'/key).write_text(val+'\n')
    (home/'data'/ident).mkdir(parents=True)
    (home/'data'/ident/'brief.md').write_text('# Task\n## Captain\'s intent\nVerify launch in this disposable lab.\n## Firstmate spec\nStart the test worker.\n')
    payload='LONG-END-'+('abcd0123'*900) if long else 'normal'
    worker=d/'worker.py';worker.write_text('import os,json,sys,time\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text(json.dumps({"task":os.getenv("FM_TASK_ID"),"gotmp":os.getenv("GOTMPDIR"),"compact":os.getenv("COMPACT_ADVISER_DISABLE"),"payload":sys.argv[1]}))\nprint("WORKER_STARTED: environment received; candidate preserved",flush=True)\ntime.sleep(300)\n')
    harness=f'{shutil.which("python3")} {worker} {payload}'
    ws=json.loads(lab('workspace','create','--cwd',str(wt),'--label',label,'--no-focus'))['result'];pane=ws['root_pane']['pane_id']
    (home/'state'/f'{ident}.meta').write_text(f'window={session}:{pane}\nendpoint_task_id={ident}\nworktree={wt}\nproject={project}\nharness={harness}\nkind=ship\nmode=local-only\nyolo=off\nbranch=fm/{ident}\nbackend=herdr\nherdr_session={session}\nherdr_workspace_id={ws["workspace"]["workspace_id"]}\nherdr_tab_id={ws["tab"]["tab_id"]}\nherdr_pane_id={pane}\n')
    if blocked:
        ready=d/'readonly-ready';lab('pane','run',pane,f'readonly FM_TASK_ID=blocked; : > {ready}');assert waitfile(ready)
    launch_env=env|{'FM_HOME':str(home),'HERDR_SESSION':session,'HERDR_PANE_ID':'','FM_SPAWN_NO_GUARD':'1'}
    p=run([spawn,ident,'--relaunch'],e=launch_env,check=False)
    started=waitfile(marker,3)
    screen=lab('pane','read',pane,'--source','recent','--lines','100')
    process=lab('pane','process-info','--pane',pane)
    (ev/f'{label}-pane.json').write_text(screen);(ev/f'{label}-process.json').write_text(process)
    after=run(['git','-C',wt,'diff','--cached','--binary']).stdout+(wt/'untracked.txt').read_text()
    note(f'{label}: fm-spawn exit={p.returncode}\n{p.stdout.strip()}\nworker_started={started}; candidate_identical={before==after}')
    assert before==after
    if spawn==baseline:
        note('baseline pane: '+screen)
        return
    if blocked:
        assert p.returncode!=0 and not started and 'setup did not complete' in p.stdout
        note('Blocked setup refused without launching; shell response: '+screen)
    else:
        assert p.returncode==0 and started
        data=json.loads(marker.read_text());assert data=={'task':ident,'gotmp':f'/tmp/fm-{ident}/gotmp','compact':'1','payload':payload}
        assert any(str(worker) in x.get('cmdline','') for x in json.loads(process)['result']['process_info']['foreground_processes'])
        note(f'Foreground worker confirmed; payload_bytes={len(payload)}; payload_sha256={hashlib.sha256(payload.encode()).hexdigest()}; environment={data["task"]}, {data["gotmp"]}, COMPACT_ADVISER_DISABLE={data["compact"]}')
        (ev/f'{label}-worker.json').write_text(marker.read_text())
try:
    run([helper,'provision',session]);note('Provisioned '+session)
    case('baseline',baseline)
    case('normal',root/'bin/fm-spawn.sh')
    case('long',root/'bin/fm-spawn.sh',long=True)
    case('blocked',root/'bin/fm-spawn.sh',blocked=True)
finally:
    p=run([helper,'teardown',session],check=False);note(f'Guarded teardown exit={p.returncode}; default-session tripwire '+('unchanged' if p.returncode==0 else p.stdout))
    (ev/'live-launch-transcript.txt').write_text('\n\n'.join(transcript)+'\n')
    baseline.unlink(missing_ok=True)
