from pathlib import Path
import os, subprocess, json, shutil, time, shlex
root=Path.cwd(); lab=root/'.cmux-live-phase'; env=os.environ.copy()
env.update(PATH=str(lab/'bin')+':/Applications/cmux.app/Contents/Resources/bin:'+env['PATH'],TMPDIR=str(lab/'tmp'),FM_TEST_SKIP_ORPHAN_REAP='1',FM_GATE_REFUSE_BYPASS='1',FM_TEST_SEAM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
for mode in ['send-failure','precommit','publication','dispatch']:
    case=lab/mode; home=case/'home'; project=home/'projects/probe'; task=f'test-cmux-{mode}-{os.getpid()}'
    for p in ['config','data/'+task,'state','projects/probe']: (home/p).mkdir(parents=True,exist_ok=True)
    (home/'config/backend').write_text('cmux\n'); (home/'config/backlog-backend').write_text('manual\n'); (home/'state/.last-watcher-beat').touch()
    e=env|{'FM_HOME':str(home),'LIVE_CASE':str(case),'LIVE_MODE':mode}
    def run(*args,**kw): return subprocess.run(args,env=e,check=True,text=True,**kw)
    run('git','-C',str(project),'init','-q','-b','main'); run('git','-C',str(project),'config','user.email','live@example.invalid'); run('git','-C',str(project),'config','user.name','Live fixture')
    (project/'README.md').write_text('Isolated live cmux fixture\n');run('git','-C',str(project),'add','README.md');run('git','-C',str(project),'commit','-qm','fixture')
    run(str(root/'bin/fm-brief.sh'),task,'probe','--scout',stdout=subprocess.DEVNULL)
    brief=home/'data'/task/'brief.md';brief.write_text(brief.read_text().replace('{TASK}','Wait for this test to close your endpoint. Do not write files, run commands, or change anything.').replace('{FIRSTMATE_SPEC}','This is an isolated launch recovery probe.'))
    if mode=='dispatch':
        (home/'config/backlog-backend').unlink();(home/'.tasks.toml').write_text('backend = "markdown"\n[markdown]\npath = "data/backlog.md"\n');(home/'data/backlog.md').write_text('# Backlog\n\n## In flight\n\n## Queued\n\n## Done\n')
        run('/Users/alex/.local/bin/tasks-axi','add',task,'Live rollback probe','--kind','scout','--file',str(home/'data/backlog.md'),cwd=home,stdout=subprocess.DEVNULL)
    with (case/'spawn.log').open('w') as log:
        result=subprocess.run([str(root/'bin/fm-spawn.sh'),task,str(project),'--scout','--harness','pi','--backend','cmux'],env=e,stdout=log,stderr=subprocess.STDOUT)
    recovery=home/'state'/f'{task}.cmux-launch-recovery'; data=dict(line.split('=',1) for line in recovery.read_text().splitlines()) if recovery.exists() else {}
    checks={'exit_nonzero':result.returncode!=0,'no_meta':not (home/'state'/f'{task}.meta').exists(),'has_recovery':bool(data),'copy_preserved':Path(data.get('worktree','/absent')).joinpath('README.md').is_file(),'pi_start_accurate':data.get('pi_start_confirmed')==('1' if mode in ['publication','dispatch'] else '0'),'closure_confirmed':data.get('closure')=='confirmed','no_tmux':not (case/'tmux-called').exists()}
    summary={'mode':mode,'task':task,'checks':checks,'recovery':data}
    (case/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
    if not all(checks.values()): break
