"""Integration checks in a private terminal; no Pi/model is launched."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

helper = str(Path.home() / '.config/zellij/bin/zellij-ws')
binary = os.environ['ZELLIJ_TRIAL_BINARY']
root = Path(os.environ['ZELLIJ_WS_STATE'])
pane = os.environ['ZELLIJ_PANE_ID'].removeprefix('terminal_')
session = os.environ['ZELLIJ_SESSION_NAME']
other = session + '-other'
owner = uuid.uuid4().hex
result = Path(os.environ['ZELLIJ_SMOKE_RESULT'])
checks = []

def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError(f'{args!r} exited {result.returncode}: {result.stderr.strip()}')
    return result.stdout.strip()

def event(state, label=None):
    args = [helper, 'event', state, '--pane', pane, '--owner', owner, '--pid', str(os.getpid()), '--session-file=' + str(root / 'fake-session.jsonl')]
    if label is not None: args.append('--label=' + label)
    run(args)

def current():
    live = json.loads(run([binary, '-s', session, 'action', 'list-panes', '--json', '--all']))
    return next(p for p in live if not p['is_plugin'] and str(p['id']) == pane)

try:
    root.mkdir(parents=True, exist_ok=True)
    (root / 'fake-session.jsonl').write_text('')
    event('start', 'test task')
    event('working')
    assert current()['title'] == '[WORK] test task · p' + pane
    checks.append('working title')
    run([helper, 'note', '--', 'stable task note'])
    event('label', 'new automatic name')
    event('asking')
    assert current()['title'] == '[ASK] stable task note · p' + pane
    checks.append('keyboard/shell window note survives agent names and states')
    rows = json.loads(run([helper, 'list', '--attention']))
    assert any(r['pane'] == 'terminal_' + pane and r['session'] == session and r['state'] == 'asking' for r in rows)
    checks.append('cross-workspace attention inventory')
    saved = root / 'layouts' / (hashlib.sha256(session.encode()).hexdigest() + '.kdl')
    text = saved.read_text()
    assert 'zellij-agent' in text and 'start_suspended false' in text
    agent_rows = list((root / 'agents').glob('*.json'))
    assert any(json.loads(p.read_text())['session_file'] == str(root / 'fake-session.jsonl') for p in agent_rows)
    checks.append('exact Pi-session pointer and automatic restoration command')
    run([helper, 'workspace', other, '--dir', '/tmp', '--group=work'])
    spaces = json.loads(run([helper, 'workspaces']))
    assert any(r['session'] == other and r['group'] == 'work' and r['status'] == 'live' for r in spaces), [(r['session'],r['status'],r['group']) for r in spaces]
    checks.append('create grouped background workspace')
    marker = root / 'background-command.txt'
    run([helper, 'open', '--kind=tab', '--in=' + other, '--cwd', str(root), '--name=background check', '--', '/bin/sh', '-c', 'printf ready > background-command.txt'])
    for _ in range(30):
        if marker.exists(): break
        time.sleep(0.05)
    assert marker.read_text() == 'ready'
    other_panes = json.loads(run([binary, '-s', other, 'action', 'list-panes', '--json', '--all']))
    assert not any(p.get('plugin_url') == 'zellij:compact-bar' for p in other_panes)
    checks.append('open a command in an unfocused task tab without a bottom bar')
    run([helper, 'workspace', other, '--focus'])
    checks.append('switch to another session without restarting source process')
    run([helper, '--session=' + session, 'focus', 'terminal_' + pane])
    checks.append('return to a precise task pane')
    run([binary, '-s', session, 'action', 'new-tab', '--name=7:stable slot', '--no-focus'])
    run([helper, 'slot', '7'])
    tabs = json.loads(run([binary, '-s', session, 'action', 'list-tabs', '--json', '--all']))
    assert any(t['name'] == '7:stable slot' and t['active'] for t in tabs)
    checks.append('stable numbered tab selection, independent of position')
    event('done')
    assert current()['title'] == '[DONE] stable task note · p' + pane
    checks.append('done state')
    restored = session + '-restore'
    creation_env = dict(os.environ)
    # Only these disposable resurrection servers get a fake Pi executable.
    # The real wrapper and duplicate-thread guards still run; no model can launch.
    fake_bin = root / 'fake-bin'
    fake_bin.mkdir()
    pi_call = root / 'fake-pi-call.json'
    fake_pi = fake_bin / 'pi'
    fake_pi.write_text('#!/usr/bin/python3\nimport json,sys\nfrom pathlib import Path\n'
                       'Path(' + repr(str(pi_call)) + ').write_text(json.dumps(sys.argv[1:]))\n')
    fake_pi.chmod(0o700)
    creation_env['PATH'] = str(fake_bin) + ':' + creation_env.get('PATH', '')
    for key in ['ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'TMUX', 'TMUX_PANE']:
        creation_env.pop(key, None)
    subprocess.run([binary, '--layout', str(saved), 'attach', '--create-background', restored], env=creation_env, check=True, capture_output=True, text=True, timeout=20)
    for attempt in range(40):
        try:
            restored_panes = json.loads(run([binary, '-s', restored, 'action', 'list-panes', '--json', '--all']))
            candidate = next((p for p in restored_panes if not p.get('is_plugin') and p.get('title') == '[DONE] stable task note · p' + pane), None)
            if candidate and not candidate.get('is_held'):
                screen = run([binary, '-s', restored, 'action', 'dump-screen', '--pane-id', 'terminal_' + str(candidate['id'])])
                if 'This Pi thread is already running in Zellij' in screen:
                    break
            time.sleep(0.05)
        except (subprocess.SubprocessError, json.JSONDecodeError):
            if attempt == 39: raise
            time.sleep(0.05)
    assert candidate and not candidate.get('is_held') and 'This Pi thread is already running in Zellij' in screen
    assert not pi_call.exists(), 'An already active thread must not invoke Pi again'
    checks.append('automatic recreation refuses a duplicate active thread and leaves a shell')
    event('shutdown')
    assert current()['title'] == 'stable task note · p' + pane
    checks.append('agent exit clears live status but retains a unique restoration title')
    metadata = json.loads((root / 'panes' / (hashlib.sha256(session.encode()).hexdigest() + '.json')).read_text())['terminal_' + pane]
    assert not metadata.get('owner') and metadata['session_file'] == str(root / 'fake-session.jsonl')
    text = saved.read_text()
    assert 'args "' + metadata['token'] + '"' in text and 'start_suspended false' in text
    checks.append('shutdown persists an exact-pointer layout without live ownership')
    closed_restore = session + '-closed-restore'
    subprocess.run([binary, '--layout', str(saved), 'attach', '--create-background', closed_restore],
                   env=creation_env, check=True, capture_output=True, text=True, timeout=20)
    for attempt in range(40):
        try:
            closed_panes = json.loads(run([binary, '-s', closed_restore, 'action', 'list-panes', '--json', '--all']))
            if pi_call.exists() and any(not p.get('is_held') and p.get('title') == 'stable task note · p' + pane for p in closed_panes):
                break
        except (subprocess.SubprocessError, json.JSONDecodeError):
            pass
        time.sleep(0.05)
    else:
        raise AssertionError('Post-shutdown exact Pi restoration did not start automatically')
    assert json.loads(pi_call.read_text()) == ['--session', str(root / 'fake-session.jsonl')]
    checks.append('native post-shutdown recreation automatically resumes the same exact Pi thread')
    result.write_text(json.dumps({'passed': checks, 'errors': [], 'other': other}, indent=2))
except Exception as error:
    result.write_text(json.dumps({'passed': checks, 'errors': [str(error)], 'other': other}, indent=2))
    raise
