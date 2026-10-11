#!/usr/bin/env python3
"""Cross-platform launcher for the browser + interface automation toolbox.

Three deliberately small jobs:

1. status    - which configured executables exist, and their versions.
2. run       - launch a configured executable with literal arguments and the
               child exit code intact. No shell string building.
3. eval-url  - ask the configured provider to fetch a URL or run JavaScript
               inside a real page context.

Configuration is read from BROWSER_TOOLBOX_CONFIG or, by default, from
<config dir>/browser-task-router/runtime.json. Generate it with
python scripts/setup.py.

There is no policy layer here on purpose: no approval gate, no verb allowlist,
no forced write protocol. This file only makes sure arguments survive, output
is not silently lost, and the exit code is truthful.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

CONFIG_ENV = 'BROWSER_TOOLBOX_CONFIG'
CONFIG_RELATIVE = Path('browser-task-router') / 'runtime.json'
SHELL_NAMES = {'cmd', 'cmd.exe', 'powershell', 'powershell.exe', 'pwsh', 'pwsh.exe',
               'bash', 'sh', 'zsh', 'fish', 'wsl', 'wsl.exe'}
SHELL_SUFFIXES = {'.cmd', '.bat', '.ps1'}


def default_config_path():
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser()
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA') or (Path.home() / 'AppData' / 'Roaming'))
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or (Path.home() / '.config'))
    return base / CONFIG_RELATIVE


def load_config(path=None):
    target = Path(path).expanduser() if path else default_config_path()
    if not target.is_file():
        raise FileNotFoundError(
            'No toolbox config at ' + str(target)
            + '. Run "python scripts/setup.py" or set ' + CONFIG_ENV + '.'
        )
    return json.loads(target.read_text(encoding='utf-8-sig'))


def resolve_command(provider):
    command = provider.get('command')
    if not command:
        raise ValueError('Provider has no command')
    command = [str(item) for item in command]
    name = Path(command[0]).name.lower()
    if name in SHELL_NAMES:
        raise ValueError(
            'A native executable entrypoint is required; shell commands are not supported: '
            + command[0]
        )
    if Path(command[0]).suffix.lower() in SHELL_SUFFIXES:
        raise ValueError(
            'Use the underlying native executable instead of a shell shim: ' + command[0]
        )
    return command


def execute(provider, arguments, capture=False, timeout=None):
    command = resolve_command(provider)
    environment = os.environ.copy()
    environment.pop('NODE_OPTIONS', None)
    environment.update({str(k): str(v) for k, v in (provider.get('env') or {}).items()})
    environment.setdefault('PYTHONUTF8', '1')
    environment.setdefault('PYTHONIOENCODING', 'utf-8')
    options = {'env': environment, 'shell': False}
    if timeout is not None:
        options['timeout'] = timeout
    if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    if capture:
        options.update(capture_output=True, text=True, encoding='utf-8', errors='replace')
    else:
        options.update(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    return subprocess.run([*command, *arguments], **options)


def locate_executable(executable):
    if not executable:
        return None
    candidate = Path(str(executable)).expanduser()
    if candidate.is_file():
        return str(candidate)
    return shutil.which(str(executable))


def inspect_provider(provider):
    command = provider.get('command') or []
    executable = command[0] if command else None
    located = locate_executable(executable)
    return {
        'installation': 'installed' if located else 'missing',
        'resolved_executable': located,
        'version': provider.get('version'),
        'connection': 'not_probed',
    }


def build_eval_request(tool, code=None, url=None):
    """Translate a neutral request into the chosen provider's own invocation."""
    if not code and not url:
        raise ValueError('provide --code or --url')
    script = code
    if url:
        script = (
            'const r = await fetch(' + json.dumps(url) + ', {credentials: "include"});'
            ' const t = await r.text();'
            ' return {status: r.status, url: r.url, body: t};'
        )
    if tool == 'webcli':
        return {'command': ['browser', 'eval', script],
                'note': 'runs in the active WebCLI page context'}
    if tool == 'browser-use':
        return {'command': ['python', '-'],
                'stdin': 'print(evaluate(' + json.dumps(script) + '))',
                'note': 'browser-use evaluates through its Python helper'}
    return {'command': [],
            'stdin': script,
            'note': 'hand the snippet to the provider CLI; see references/' + tool + '.md'}


def sync_file(target, incoming, baseline, candidates):
    """Non-destructive three-way merge helper.

    Updates only when the local file is absent or still matches the baseline.
    Otherwise the incoming bytes are staged as a candidate and nothing changes.
    """
    target = Path(target)
    if target.exists():
        current = target.read_bytes()
        if current == incoming:
            return 'unchanged'
        if baseline is None or current != baseline:
            candidate = Path(candidates) / target.name
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(incoming)
            return 'merge_required'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.incoming')
    temporary.write_bytes(incoming)
    temporary.replace(target)
    return 'updated'


def build_parser():
    parser = argparse.ArgumentParser(
        description='Launch configured browser/interface tools without losing arguments or output.'
    )
    parser.add_argument('--config', help='Path to runtime.json (defaults to the config dir)')
    subparsers = parser.add_subparsers(dest='operation', required=True)

    status_parser = subparsers.add_parser('status', help='Report installed/missing providers')
    status_parser.add_argument('provider', nargs='?', help='Limit the report to one provider')

    run_parser = subparsers.add_parser('run', help='Launch a provider with literal arguments')
    run_parser.add_argument('provider')
    run_parser.add_argument('arguments', nargs=argparse.REMAINDER)

    eval_parser = subparsers.add_parser('eval-url', help='Read a URL or run JavaScript in a page context')
    eval_parser.add_argument('--with', dest='tool', required=True, help='Provider name to use')
    eval_parser.add_argument('--url', help='Fetch this URL from inside the page context')
    eval_parser.add_argument('--code', help='JavaScript to evaluate in the page context')

    merge_parser = subparsers.add_parser('sync-file', help='Non-destructive three-way file sync')
    merge_parser.add_argument('--target', required=True)
    merge_parser.add_argument('--incoming', required=True)
    merge_parser.add_argument('--baseline')
    merge_parser.add_argument('--candidates', required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.operation == 'sync-file':
        baseline = Path(args.baseline).read_bytes() if args.baseline else None
        result = sync_file(Path(args.target), Path(args.incoming).read_bytes(), baseline, Path(args.candidates))
        print(json.dumps({'status': result}))
        return 3 if result == 'merge_required' else 0

    config = load_config(args.config)
    providers = config.get('providers', {})

    if args.operation == 'status':
        if args.provider:
            if args.provider not in providers:
                raise KeyError('Unknown provider: ' + args.provider)
            report = {args.provider: inspect_provider(providers[args.provider])}
        else:
            report = {name: inspect_provider(provider) for name, provider in providers.items()}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.operation == 'eval-url':
        request = build_eval_request(args.tool, code=args.code, url=args.url)
        print(json.dumps({'provider': args.tool, **request}, ensure_ascii=False))
        return 0

    if args.provider not in providers:
        raise KeyError('Unknown provider: ' + args.provider)
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    return execute(providers[args.provider], arguments).returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, RuntimeError, FileNotFoundError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
