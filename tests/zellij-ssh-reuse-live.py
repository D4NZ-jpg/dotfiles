#!/usr/bin/env python3
"""Opt-in native creation test: count owned SSH starts without capturing SSH data."""
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile

REAL_SSH = shutil.which('ssh')
with tempfile.TemporaryDirectory(prefix='ssh-reuse-live-', dir='/tmp') as directory:
    root = Path(directory)
    log = root / 'calls.jsonl'
    shim = root / 'ssh'
    shim.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
control=next((item.split('=',1)[1] for item in args if item.startswith('ControlPath=')),None)
if control and control.startswith('/tmp/zellij-ws-ssh-'):
    record={'control':control,'existing':Path(control).exists(),
            'role':'close' if '-O' in args else 'tty' if '-tt' in args else 'rpc'}
    fd=os.open(''' + repr(str(log)) + ''',os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    with os.fdopen(fd,'w') as output: output.write(json.dumps(record)+'\\n')
os.execv(''' + repr(REAL_SSH) + ''',['ssh',*args])
''')
    shim.chmod(0o700)
    previous = os.environ.get('PATH', '')
    os.environ['PATH'] = str(root) + ':' + previous
    try:
        state = runpy.run_path(str(Path(__file__).with_name('zellij-machine-live.py')))
    except Exception:
        records = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        print('Private SSH failure stages:', [{'role': item['role'], 'existing': item['existing']} for item in records])
        print('Private SSH directories remaining:', sum(Path(item['control']).parent.exists() for item in records))
        raise
    finally:
        os.environ['PATH'] = previous
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert len({call['control'] for call in calls}) == 1, 'Creation did not share one private socket'
    assert [call['existing'] for call in calls].count(False) == 1, 'Creation authenticated more than once'
    assert [call['role'] for call in calls] == ['tty', 'rpc', 'rpc', 'tty', 'close'], calls
    assert calls[-1]['existing'], 'Master was not live when explicitly closed'
    assert not Path(calls[0]['control']).parent.exists(), 'Private SSH directory leaked'
    print(json.dumps({'private_ssh_creation': {'fresh_connections': 1, 'reused_channels': 3,
        'closed': True, 'directory_removed': True}, 'timings': state['timings']}, indent=2))
