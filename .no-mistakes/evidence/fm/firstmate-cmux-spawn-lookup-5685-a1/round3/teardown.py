from pathlib import Path
import os,subprocess,json,time,shutil
root=Path.cwd();lab=root/'.cmux-validation-r3';ev=Path('/Users/alex/.no-mistakes/evidence/01M3D2JD5ZBG8VV8D72A3EZKJQ/round3');case=lab/'teardown';home=case/'home';project=home/'projects/probe';task=f'test-cmux-teardown-{os.getpid()}'
e=os.environ.copy()
for k in list(e):
 if (k.startswith('FM_') and k.endswith('_OVERRIDE')) or k in ['FM_GATE_REFUSE_BYPASS','TASKS_AXI_FILE','TASKS_AXI_BACKEND']:e.pop(k)
e.update(PATH=str(lab/'bin')+':/Applications/cmux.app/Contents/Resources/bin:'+e['PATH'],TMPDIR=str(lab/'tmp'),FM_HOME=str(home),LIVE_CASE=str(case),LIVE_MODE='teardown',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
def run(*a,check=True):return subprocess.run(a,env=e,check=check,text=True,capture_output=True)
run(str(root/'bin/fm-lab-home.sh'),'create',str(home));project.mkdir();(home/'data'/task).mkdir()
(home/'config/backend').write_text('cmux\n');(home/'config/backlog-backend').write_text('manual\n');(home/'state/.last-watcher-beat').touch()
run('git','-C',str(project),'init','-q','-b','main');run('git','-C',str(project),'config','user.name','Live fixture');run('git','-C',str(project),'config','user.email','live@example.invalid');(project/'README.md').write_text('Fixture\n');run('git','-C',str(project),'add','README.md');run('git','-C',str(project),'commit','-qm','fixture')
run(str(root/'bin/fm-brief.sh'),task,'probe','--scout');brief=home/'data'/task/'brief.md';report=home/'data'/task/'report.md'
brief.write_text(brief.read_text().replace('{TASK}',f'Write exactly "Live teardown probe ready" to {report}. Do not change any project files. Then wait for the supervisor to close this disposable endpoint.').replace('{FIRSTMATE_SPEC}','This is an isolated live cleanup test.'))
r=run(str(root/'bin/fm-spawn.sh'),task,str(project),'--scout','--harness','pi','--backend','cmux',check=False);(ev/'teardown-spawn.log').write_text(r.stdout+r.stderr);assert r.returncode==0
meta=home/'state'/f'{task}.meta';m=dict(x.split('=',1) for x in meta.read_text().splitlines() if '=' in x);ws=m['cmux_workspace_id'];sf=m['cmux_surface_id'];wt=Path(m['worktree'])
(ev/'teardown-endpoint.json').write_text(json.dumps(m,indent=2))
for _ in range(90):
 if report.exists():break
 time.sleep(1)
assert report.exists(), 'Pi did not produce report'
print('Pi report:',report.read_text(),flush=True)
run(str(root/'bin/fm-captain-hold.sh'),'complete',task,'--none')
new=json.loads(run('cmux','new-surface','--workspace',ws,'--working-directory',str(lab),'--command','/bin/bash --noprofile --norc','--focus','false','--json','--id-format','uuids').stdout)['surface_id']
run('cmux','close-surface','--workspace',ws,'--surface',sf);time.sleep(.5)
refused=run(str(root/'bin/fm-teardown.sh'),task,check=False);(ev/'teardown-refusal.log').write_text(refused.stdout+refused.stderr)
assert refused.returncode!=0 and meta.exists() and (wt/'README.md').is_file(), 'teardown must refuse and retain metadata/copy'
print('Stale-surface teardown refused; task metadata and isolated copy remain',flush=True)
cmd='. "$1/bin/fm-backend.sh"; fm_backend_source cmux; . "$1/tests/cmux-test-safety.sh"; cmux_safe_close_workspace "$2" "$3"; rc=$?; [ "$rc" -eq 0 ] && fm_backend_cmux_workspace_confirmed_gone "$4"'
closed=run('bash','-c',cmd,'_',str(root),ws+':'+new,'fm-'+task,ws,check=False);(ev/'teardown-close.log').write_text(closed.stdout+closed.stderr);assert closed.returncode==0,'guarded cleanup refused'
finished=run(str(root/'bin/fm-teardown.sh'),task,check=False);(ev/'teardown-finished.log').write_text(finished.stdout+finished.stderr);assert finished.returncode==0 and not meta.exists(),'confirmed-gone teardown failed'
print('After exact closure was confirmed, teardown succeeded and retired task metadata',flush=True)
