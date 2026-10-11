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
import copy
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

sys.dont_write_bytecode = True

CONFIG_ENV = 'BROWSER_TOOLBOX_CONFIG'
CONFIG_RELATIVE = Path('browser-task-router') / 'runtime.json'
LEGACY_CONFIG = Path.home() / '.config' / 'browser-task-router' / 'runtime.json'
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
    if not target.is_file() and LEGACY_CONFIG.is_file():
        target = LEGACY_CONFIG
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


def owned_browser_config(config):
    """True when the config describes an owned, extension-loaded Chromium."""
    return all(key in config for key in ('runtime_root', 'chromium_executable', 'bsk_extension'))


def process_alive(process_id):
    if os.name != 'nt':
        try:
            os.kill(process_id, 0)
            return True
        except ProcessLookupError:
            return False
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x1000, False, process_id)
    if not handle:
        return ctypes.get_last_error() == 5
    try:
        exit_code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise RuntimeError('Cannot verify owned browser process')
        return exit_code.value == 259
    finally:
        kernel.CloseHandle(handle)


def ensure_bsk_daemon(config):
    """Start the BrowserSkill daemon exactly once, or reuse the live one.

    Returns daemon status on success, or None when this install has no
    BSK_HOME to manage and the caller should simply pass through.
    """
    provider = copy.deepcopy(config['providers']['browser-skill'])
    env = provider.setdefault('env', {})
    if 'BSK_HOME' not in env:
        return None
    env['BSK_AUTO_START'] = '0'
    result = execute(provider, ['status', '--json'], capture=True, timeout=8)
    if result.returncode == 0:
        return json.loads(result.stdout)
    daemon_home = Path(env['BSK_HOME']).resolve()
    info = daemon_home / 'daemon.json'
    if info.exists():
        metadata = json.loads(info.read_text(encoding='utf-8'))
        if process_alive(metadata['pid']):
            raise RuntimeError('BrowserSkill daemon is alive but its status failed; no automatic restart')
    elif 'automatic daemon startup is disabled' not in result.stdout + result.stderr:
        raise RuntimeError('BrowserSkill status did not prove daemon absence; inspect the error before starting')
    daemon_home.mkdir(parents=True, exist_ok=True)
    lock = daemon_home / 'toolbox-start.lock'
    try:
        with lock.open('x', encoding='utf-8') as stream:
            stream.write(str(os.getpid()))
    except FileExistsError:
        raise RuntimeError('BrowserSkill startup already pending; do not start another daemon')
    try:
        environment = os.environ.copy()
        environment.update(env)
        options = {'env': environment, 'stdin': subprocess.DEVNULL,
                   'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
        if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            options['creationflags'] = subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen([*provider['command'], 'daemon', 'start', '--foreground'], **options)
        (daemon_home / 'toolbox-process.json').write_text(json.dumps({'pid': process.pid}), encoding='utf-8')
        for attempt in range(15):
            result = execute(provider, ['status', '--json'], capture=True, timeout=8)
            if result.returncode == 0:
                return json.loads(result.stdout)
            if process.poll() is not None:
                raise RuntimeError('Owned BrowserSkill daemon exited during startup; inspect bsk logs')
            time.sleep(0.3)
        raise RuntimeError('Owned BrowserSkill daemon is still starting; inspect its PID instead of repeating startup')
    finally:
        lock.unlink(missing_ok=True)


def browser_endpoint(profile):
    active_port = profile / 'DevToolsActivePort'
    if not active_port.is_file():
        return None
    lines = active_port.read_text(encoding='utf-8').splitlines()
    if len(lines) < 2 or not lines[0].isdigit() or not lines[1].startswith('/devtools/browser/'):
        return None
    endpoint = 'http://127.0.0.1:' + lines[0]
    try:
        with urllib.request.urlopen(endpoint + '/json/version', timeout=2) as response:
            metadata = json.load(response)
        if metadata.get('webSocketDebuggerUrl', '').endswith(lines[1]):
            return endpoint
    except (OSError, ValueError):
        return None
    return None


def ensure_browser(config):
    """Start or reuse one owned headless Chromium and return its CDP endpoint."""
    if not owned_browser_config(config):
        raise ValueError('browser-endpoint requires runtime_root, chromium_executable and bsk_extension in the config')
    root = Path(config['runtime_root']).resolve()
    profile = root / 'state' / 'chromium-profile'
    profile.mkdir(parents=True, exist_ok=True)
    endpoint = browser_endpoint(profile)
    if endpoint:
        return endpoint
    receipt_path = root / 'state' / 'browser-process.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if process_alive(receipt['pid']):
            raise RuntimeError('Owned browser is still running but CDP is unavailable; do not restart or attach a working browser')
    lock = root / 'state' / 'browser-start.lock'
    try:
        with lock.open('x', encoding='utf-8') as stream:
            stream.write(str(os.getpid()))
    except FileExistsError:
        for attempt in range(15):
            endpoint = browser_endpoint(profile)
            if endpoint:
                return endpoint
            time.sleep(0.5)
        raise RuntimeError('Another browser start is pending; inspect its process before retrying')
    try:
        executable = Path(config['chromium_executable'])
        extension = Path(config['bsk_extension'])
        if not executable.is_file() or not (extension / 'manifest.json').is_file():
            raise RuntimeError('Chromium or BrowserSkill extension is missing')
        command = [str(executable), '--headless=new', '--no-first-run', '--no-default-browser-check',
                   '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1',
                   '--user-data-dir=' + str(profile),
                   '--disable-extensions-except=' + str(extension),
                   '--load-extension=' + str(extension), 'about:blank']
        options = {'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
        if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            options['creationflags'] = subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen(command, **options)
        receipt_path.write_text(json.dumps({'pid': process.pid, 'profile': str(profile), 'executable': str(executable)}), encoding='utf-8')
        for attempt in range(30):
            endpoint = browser_endpoint(profile)
            if endpoint:
                return endpoint
            if process.poll() is not None:
                raise RuntimeError('Owned Chromium exited before its CDP endpoint became available')
            time.sleep(0.5)
        raise RuntimeError('Owned Chromium is still starting; inspect it before starting another process')
    finally:
        lock.unlink(missing_ok=True)


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

    subparsers.add_parser('browser-endpoint', help='Start or reuse the owned headless Chromium and print its CDP endpoint')

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

    if args.operation == 'browser-endpoint':
        print(ensure_browser(config))
        return 0

    if args.provider not in providers:
        raise KeyError('Unknown provider: ' + args.provider)
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    provider = copy.deepcopy(providers[args.provider])
    if args.provider == 'browser-skill' and owned_browser_config(config):
        env = provider.setdefault('env', {})
        if 'BSK_HOME' in env:
            env['BSK_AUTO_START'] = '0'
        if arguments[:2] == ['session', 'start']:
            if 'BSK_HOME' in env:
                ensure_bsk_daemon(config)
            ensure_browser(config)
            if '--no-focus' not in arguments:
                arguments = [*arguments, '--no-focus']
    if args.provider == 'browser-use' and owned_browser_config(config) and not any(
        value in {'--help', '-h', '--version', 'skill', 'telemetry', 'auth'} for value in arguments
    ):
        provider.setdefault('env', {})['BU_CDP_URL'] = ensure_browser(config)
    return execute(provider, arguments).returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, RuntimeError, FileNotFoundError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
