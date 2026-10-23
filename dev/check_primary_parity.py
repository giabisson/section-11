#!/usr/bin/env python3
"""Read-only source parity check. Private profiles/data are deliberately excluded.

Checks the canonical tracked/nonignored working tree. With --include-runtime,
also checks separate primary runtime/skill/unit copies. Does not print contents,
read credentials, update services, install files or contact an LLM.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def source_files(root):
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=root, capture_output=True, check=True)
    names = sorted(set(result.stdout.decode().split('\0'))-{''})
    for name in names:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or any(p == '.env' or p.startswith('.env.') or p in ('.sync_config.json', 'openclaw.json', 'auth-profiles.json') for p in path.parts) or name.startswith('literature/cycling-training/sources/'):
            raise ValueError('private_or_unsafe_source_path')
        target = root/path
        if target.is_symlink() or not target.is_file():
            raise ValueError('ordinary_source_file_required')
    return names


def targets(root, remote_root, runtime, skill, units, include_runtime=False):
    expected = {}
    names = source_files(root)
    for name in names:
        digest = hashlib.sha256((root/name).read_bytes()).hexdigest()
        expected['checkout/'+name] = {'path': str(remote_root/name), 'sha256': digest}
        if not include_runtime:
            continue
        prefix = 'examples/agentic/openclaw/'
        if name.startswith(prefix):
            relative = name[len(prefix):]
            if Path(relative).suffix in ('.py', '.mjs', '.json'):
                expected['runtime/'+relative] = {'path': str(runtime/relative), 'sha256': digest}
            if relative.startswith('section11-') and Path(relative).suffix in ('.service','.timer'):
                expected['unit/'+relative] = {'path': str(units/relative), 'sha256': digest}
        if name == 'examples/training_history.py':
            expected['runtime/training_history.py'] = {'path': str(runtime/'training_history.py'), 'sha256': digest}
        if name == 'SKILL.md':
            expected['skill/SKILL.md'] = {'path': str(skill/'SKILL.md'), 'sha256': digest}
    return expected


def remote_script(expected):
    # Data travels on stdin. Only a fixed python command is passed to SSH.
    return '''from pathlib import Path
import hashlib,json
expected=json.loads('''+repr(json.dumps(expected))+''')
failures=[]
for name,item in expected.items():
    path=Path(item['path'])
    try:
        valid=path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
    except OSError:
        valid=False
    if not valid: failures.append(name)
print(json.dumps({'matched':not failures,'checked':len(expected),'mismatches':failures,'scope':'Requested source paths only; private configuration and data remain separate.'}))
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='home-server')
    parser.add_argument('--remote-home', type=Path, default=Path.home())
    parser.add_argument('--include-runtime', action='store_true', help='also compare separately installed runtime/skill/unit copies')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@-]*', args.host) or not args.remote_home.is_absolute():
        parser.error('a plain SSH host and absolute remote home are required')
    root=Path(__file__).resolve().parents[1];home=args.remote_home
    expected=targets(root,home/'section-11',home/'.local/share/section11-runtime',home/'.openclaw/workspace/skills/section-11',home/'.config/systemd/user',args.include_runtime)
    result=subprocess.run(['ssh','-T','-x','-o','BatchMode=yes','-o','ConnectTimeout=10',args.host,'python3','-'],input=remote_script(expected),text=True,capture_output=True,timeout=45)
    if result.returncode:
        print('{"matched":false,"error":"remote_parity_check_failed_no_private_diagnostics_printed"}');return 1
    value=json.loads(result.stdout);print(json.dumps(value,indent=2));return 0 if value['matched'] else 1


if __name__=='__main__':raise SystemExit(main())
