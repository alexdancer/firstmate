import os, subprocess, pathlib, json, time, secrets, hashlib, shutil
root = pathlib.Path.cwd()
d = root / '.local-test-tmp/pi-live'
d.mkdir()
ev = pathlib.Path('/Users/alex/.no-mistakes/evidence/01M3BH9GJAQT2Z7T9F8BAK50GD/round2')
helper = root / 'bin/fm-herdr-lab.sh'
store = root / '.local-test-tmp/pi-store'
env = os.environ.copy()
for k in ['HERDR_ENV', 'HERDR_PANE_ID', 'HERDR_TAB_ID', 'HERDR_WORKSPACE_ID', 'HERDR_SOCKET_PATH', 'HERDR_SESSION', 'CLAUDECODE', 'FM_TASK_ID']:
    env.pop(k, None)
env.update(TMPDIR=str(root / '.local-test-tmp/tmp'), FM_HERDR_LAB_STATE_DIR=str(root / '.local-test-tmp/labs'), GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', FM_GATE_REFUSE_BYPASS='1', PI_CODING_AGENT_DIR=str(store), PI_CODING_AGENT_SESSION_DIR=str(d / 'sessions'), PI_OFFLINE='1', PI_TELEMETRY='0')
logs = []
def note(s):
    logs.append(s)
    print(s, flush=True)
def run(args, e=None, check=True, timeout=60):
    p = subprocess.run(list(map(str, args)), env=e or env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(p.stdout)
    return p
session = run([helper, 'name', 'pi-brief-proof']).stdout.strip()
def lab(*args, check=True):
    return run([helper, 'run', session, *args], check=check).stdout
project = d / 'project'
wt = d / 'candidate'
home = d / 'home'
ident = f'nmpi-{os.getpid()}'
project.mkdir()
(home / 'state').mkdir(parents=True)
(home / 'config').mkdir()
run(['git', 'init', '-q', project])
run(['git', '-C', project, 'config', 'user.name', 'Test'])
run(['git', '-C', project, 'config', 'user.email', 'test@example.invalid'])
(project / 'README.md').write_text('Disposable Pi launch proof\n')
run(['git', '-C', project, 'add', '.'])
run(['git', '-C', project, 'commit', '-qm', 'test'])
run(['git', '-C', project, 'worktree', 'add', '-qb', f'fm/{ident}', wt])
(wt / 'README.md').write_text('Preserved staged candidate\n')
run(['git', '-C', wt, 'add', 'README.md'])
challenge = {'left': secrets.randbelow(10000) + 10000, 'right': secrets.randbelow(10000) + 10000, 'nonce': secrets.token_hex(8)}
(wt / 'challenge.json').write_text(json.dumps(challenge))
expected = f'LAUNCH_READY {challenge["left"] + challenge["right"]} {challenge["nonce"]}'
def snapshot():
    return {'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in wt.iterdir() if p.is_file() and p.name != '.git'}, 'index': run(['git', '-C', wt, 'diff', '--cached', '--binary']).stdout, 'status': run(['git', '-C', wt, 'status', '--porcelain']).stdout}
before = snapshot()
(home / 'config/backlog-backend').write_text('manual\n')
(home / 'config/herdr-presentation-spaces').write_text('off\n')
(home / 'config/launch-env-allowlist').write_text('PI_CODING_AGENT_DIR\nPI_CODING_AGENT_SESSION_DIR\nPI_OFFLINE\nPI_TELEMETRY\n')
le = env | {'FM_HOME': str(home), 'HERDR_SESSION': session, 'FM_SPAWN_NO_GUARD': '1'}
run([root / 'bin/fm-brief.sh', ident, 'project', '--mode', 'local-only', '--herdr-lab'], le)
b = home / 'data' / ident / 'brief.md'
b.write_text(b.read_text().replace('{TASK}', 'Prove that a real Pi worker processes its launch brief on this isolated Herdr lab. Read challenge.json and reply with LAUNCH_READY, the sum of left and right, and nonce, separated by spaces.').replace('{FIRSTMATE_SPEC}', 'This is a development-only launch evaluation, not implementation work. Use the read tool to read challenge.json in the current candidate directory. Return the requested answer as your final response, without any prefix or extra words. Do not edit any files, run shell commands, commit, push, start validation, spawn workers, or operate Herdr. Do not run any session-start command. Stop after your response. The staged README and untracked challenge are preserved candidate data. No other lifecycle work is requested.'))
active = False
result = {'session': session, 'head': run(['git', 'rev-parse', 'HEAD']).stdout.strip(), 'claude': {'result': 'untested', 'reason': 'Prior Claude run stopped at external-import consent; no consent requested or attempted in this round.'}}
try:
    note('Herdr ' + run(['herdr', '--version']).stdout.strip() + '; Pi ' + run(['pi', '--version']).stdout.strip())
    run([helper, 'provision', session]); active = True
    run([helper, 'viewer', 'start', session]); note('Attached lab viewer with fixed 40x120 pty and drained master.')
    note('Provisioned named isolated lab ' + session)
    ws = json.loads(lab('workspace', 'create', '--cwd', wt, '--label', 'pi-brief-proof', '--no-focus'))['result']
    pane = ws['root_pane']['pane_id']
    (home / 'state' / f'{ident}.meta').write_text(f'window={session}:{pane}\nendpoint_task_id={ident}\nworktree={wt}\nproject={project}\nharness=pi\nkind=ship\nmode=local-only\nyolo=off\nbranch=fm/{ident}\nbackend=herdr\nherdr_session={session}\nherdr_workspace_id={ws["workspace"]["workspace_id"]}\nherdr_tab_id={ws["tab"]["tab_id"]}\nherdr_pane_id={pane}\n')
    p = run([root / 'bin/fm-spawn.sh', ident, '--relaunch', '--model', 'openai-codex/gpt-6-sol', '--effort', 'low'], le, check=False)
    note(f'Public fm-spawn --relaunch exit={p.returncode}\n' + p.stdout)
    assert p.returncode == 0
    # Native output wait, followed by inspection, is readiness evidence only.
    note(lab('pane', 'wait-output', pane, '--match', 'trust', '--timeout', '10000', check=False))
    screen = lab('pane', 'read', pane, '--source', 'recent-unwrapped', '--lines', '200')
    (ev / 'pi-initial-pane.txt').write_text(screen)
    note('Initial pane:\n' + screen)
    if 'trust' in screen.lower() and ('Enter' in screen or 'enter' in screen):
        lab('pane', 'send-keys', pane, 'Enter')
        note('Accepted Pi project trust for this disposable candidate only.')
    messages = []
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        messages = []
        for f in (d / 'sessions').rglob('*.jsonl'):
            for line in f.read_text().splitlines():
                try: item = json.loads(line)
                except ValueError: continue
                if item.get('type') == 'message': messages.append(item['message'])
        replies = [m for m in messages if m.get('role') == 'assistant' and m.get('stopReason') == 'stop']
        if replies: break
        time.sleep(0.5)
    screen = lab('pane', 'read', pane, '--source', 'recent-unwrapped', '--lines', '200')
    (ev / 'pi-final-pane.txt').write_text(screen)
    process = lab('pane', 'process-info', '--pane', pane)
    (ev / 'pi-process.json').write_text(process)
    session_files = list((d / 'sessions').rglob('*.jsonl'))
    if session_files:
        note(run(['pi', '--export', session_files[0], ev / 'pi-session.html']).stdout)
    (ev / 'pi-model-messages.json').write_text(json.dumps([m for m in messages if m.get('role') != 'user'], indent=2))
    result['expected_reply'] = expected
    result['assistant_replies'] = [''.join(c.get('text', '') for c in m.get('content', []) if c.get('type') == 'text') for m in replies]
    result['challenge_read'] = any(m.get('role') == 'assistant' and any(c.get('type') == 'toolCall' and c.get('name') == 'read' and str(c.get('arguments', {}).get('path', '')).endswith('challenge.json') for c in m.get('content', [])) for m in messages)
    result['candidate_identical'] = before == snapshot()
    result['pass'] = result['challenge_read'] and expected in result['assistant_replies'] and result['candidate_identical']
    note(json.dumps(result, indent=2))
    if not result['pass']: note('Final pane:\n' + screen)
    assert result['pass'], 'No verified model reply, challenge read, or preserved candidate'
finally:
    if active:
        p = run([helper, 'teardown', session], check=False)
        result['guarded_teardown_exit'] = p.returncode
        note(f'Guarded teardown/default-session tripwire exit={p.returncode}\n' + p.stdout)
    (ev / 'pi-launch-result.json').write_text(json.dumps(result, indent=2))
    (ev / 'pi-launch-transcript.txt').write_text('\n'.join(logs))
    assert result.get('guarded_teardown_exit', 0) == 0
