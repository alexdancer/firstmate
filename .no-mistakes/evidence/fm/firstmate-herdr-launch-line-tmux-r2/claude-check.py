import os,subprocess,pathlib,json,time
root=pathlib.Path.cwd();d=root/'.local-test-tmp/claude';d.mkdir(parents=True,exist_ok=True)
ev=pathlib.Path('/Users/alex/.no-mistakes/evidence/01M3BH9GJAQT2Z7T9F8BAK50GD');helper=root/'bin/fm-herdr-lab.sh'
env=os.environ.copy()
for k in ['HERDR_ENV','HERDR_PANE_ID','HERDR_TAB_ID','HERDR_WORKSPACE_ID','HERDR_SOCKET_PATH','HERDR_SESSION','CLAUDECODE']:env.pop(k,None)
env.update(TMPDIR=str(root/'.local-test-tmp'),FM_HERDR_LAB_STATE_DIR=str(d/'labs'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',FM_GATE_REFUSE_BYPASS='1',CLAUDE_CONFIG_DIR=str(d/'claude-store'))
def run(a,e=None,check=True):
 p=subprocess.run(list(map(str,a)),env=e or env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
 if check and p.returncode:raise RuntimeError(p.stdout)
 return p
session=run([helper,'name','claude-launch']).stdout.strip()
def lab(*a):return run([helper,'run',session,*a]).stdout
project=d/'project';wt=d/'candidate';home=d/'home';ident=f'nmclaude-{os.getpid()}'
project.mkdir();(home/'state').mkdir(parents=True);(home/'config').mkdir();(d/'claude-store').mkdir()
(d/'claude-store'/'.claude.json').write_text(json.dumps({'hasCompletedOnboarding':True,'theme':'dark'}))
run(['git','init','-q',project]);run(['git','-C',project,'config','user.name','Test']);run(['git','-C',project,'config','user.email','test@example.invalid'])
(project/'README.md').write_text('Disposable launch test\n');run(['git','-C',project,'add','.']);run(['git','-C',project,'commit','-qm','test']);run(['git','-C',project,'worktree','add','-qb',f'fm/{ident}',wt])
(home/'config'/'backlog-backend').write_text('manual\n');(home/'config'/'herdr-presentation-spaces').write_text('off\n');(home/'config'/'claude-permission-mode').write_text('auto\n')
le=env|{'FM_HOME':str(home),'HERDR_SESSION':session,'FM_SPAWN_NO_GUARD':'1'}
run([root/'bin/fm-brief.sh',ident,'project','--mode','local-only','--herdr-lab'],le)
b=home/'data'/ident/'brief.md';s=b.read_text().replace('{TASK}','Verify this disposable worker starts. Reply LAUNCH_READY without modifying project files.').replace('{FIRSTMATE_SPEC}','Reply LAUNCH_READY. Do not run development or lifecycle commands.');b.write_text(s)
logs=[]
try:
 run([helper,'provision',session]);logs.append('Provisioned '+session)
 ws=json.loads(lab('workspace','create','--cwd',str(wt),'--label','claude-start','--no-focus'))['result'];pane=ws['root_pane']['pane_id']
 (home/'state'/f'{ident}.meta').write_text(f'window={session}:{pane}\nendpoint_task_id={ident}\nworktree={wt}\nproject={project}\nharness=claude\nkind=ship\nmode=local-only\nyolo=off\nbranch=fm/{ident}\nbackend=herdr\nherdr_session={session}\nherdr_workspace_id={ws["workspace"]["workspace_id"]}\nherdr_tab_id={ws["tab"]["tab_id"]}\nherdr_pane_id={pane}\n')
 p=run([root/'bin/fm-spawn.sh',ident,'--relaunch'],le,False);logs.append(f'fm-spawn exit={p.returncode}\n'+p.stdout)
 for i in range(15):
  time.sleep(1);screen=lab('pane','read',pane,'--source','recent','--lines','100')
  if 'login' in screen.lower() or 'sign in' in screen.lower() or 'LAUNCH_READY' in screen:break
 logs.append(screen);(ev/'claude-pane.txt').write_text(screen);(ev/'claude-process.json').write_text(lab('pane','process-info','--pane',pane))
finally:
 p=run([helper,'teardown',session],check=False);logs.append(f'Guarded teardown exit={p.returncode}; '+p.stdout)
 (ev/'claude-launch-transcript.txt').write_text('\n'.join(logs));print('\n'.join(logs))
