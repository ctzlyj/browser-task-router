#!/usr/bin/env python3
"""Detect installed tools, write runtime.json, and register CLI aliases.

Run once after installing your tools:

    python scripts/setup.py

It probes PATH plus a few common install locations, records what it found in
<config dir>/browser-task-router/runtime.json, and merges local CLI entries
into ~/.browser-task-router/local_cli.json without touching unrelated entries.
Missing tools are reported, not fatal. Add anything unusual with --extra, or
point at a specific install with --webcli-root / --python-root.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve()
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))


def import_toolbox():
    import toolbox
    return toolbox


def default_roots():
    home = Path.home()
    roots = [home / 'tools', home / '.local' / 'bin']
    if sys.platform == 'darwin':
        roots.append(Path('/opt/homebrew/bin'))
    return [str(root) for root in roots]


def candidate_bins(extra_roots):
    bins = []
    for root in [*extra_roots, *default_roots()]:
        bins.append(Path(root).expanduser())
    return [str(item) for item in bins]


PROVIDER_SPECS = [
    {
        'name': 'webcli',
        'kind': 'browser-context',
        'description': 'Drive a real logged-in browser and call site interfaces from page context.',
        'guide': 'references/webcli.md',
        'probes': [['webcli', '--version']],
        'candidates': ['@jd/webcli/dist/src/main.js'],
    },
    {
        'name': 'browser-skill',
        'kind': 'browser-context',
        'description': 'Attach to a controllable browser session for read and write automation.',
        'guide': 'references/browser-skill.md',
        'probes': [['bsk', '--version'], ['browser-skill', '--version']],
        'candidates': ['bsk/bsk.exe', 'bsk/bsk', 'BrowserSkill/bsk.exe'],
    },
    {
        'name': 'browser-use',
        'kind': 'browser-context',
        'description': 'Navigate, observe and script a browser through CLI helpers.',
        'guide': 'references/browser-use.md',
        'probes': [['browser-use', '--version']],
        'candidates': ['browser-use/Scripts/browser-use.exe', 'browser-use/bin/browser-use'],
    },
    {
        'name': 'browser-act',
        'kind': 'browser-context',
        'description': 'Skill-driven browser actions with local or remote modes.',
        'guide': 'references/browser-act.md',
        'probes': [['browser-act', '--version']],
        'candidates': ['browser-act/Scripts/browser-act.exe', 'browser-act/bin/browser-act'],
    },
    {
        'name': 'playwright-cli',
        'kind': 'cli',
        'description': 'Headless browser control, tracing, network inspection and cross-browser tests.',
        'guide': 'references/playwright-cli.md',
        'probes': [['playwright-cli', '--version'], ['npx', '--yes', '@playwright/cli@latest', '--version']],
        'candidates': ['node/node_modules/@playwright/cli/playwright-cli.js'],
        'needs_node': True,
    },
    {
        'name': 'playwright-mcp',
        'kind': 'cli',
        'description': 'Playwright exposed as a stdio MCP server for MCP-capable clients.',
        'guide': 'references/playwright-mcp.md',
        'probes': [['npx', '--yes', '@playwright/mcp@latest', '--version']],
        'candidates': ['node/node_modules/@playwright/mcp/cli.js'],
        'needs_node': True,
    },
]


def config_path(override=None):
    toolbox = import_toolbox()
    return Path(override).expanduser() if override else toolbox.default_config_path()


def read_registry(path):
    if path.is_file():
        return json.loads(path.read_text(encoding='utf-8-sig'))
    return {'format_version': 'browser-task-router/local-cli/v1', 'clis': []}


def merge_registry(existing, additions):
    """Add missing entries; never overwrite or reorder unrelated ones."""
    result = json.loads(json.dumps(existing))
    entries = result.setdefault('clis', [])
    names = {entry.get('name'): index for index, entry in enumerate(entries)}
    added = []
    for addition in additions:
        name = addition['name']
        if name in names:
            index = names[name]
            current = entries[index]
            if current.get('entry_point') == addition.get('entry_point'):
                continue
            if 'entry_point' not in current:
                entries[index] = {**addition, **current}
                added.append(name)
            continue
        entries.append(json.loads(json.dumps(addition)))
        names[name] = len(entries) - 1
        added.append(name)
    return result, added


def run_capture(toolbox, command, timeout=40):
    """Try a command. Returns (ok, first_output_line). Shell shims count as failure."""
    try:
        result = toolbox.execute({'command': command, 'env': {}}, [], capture=True, timeout=timeout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False, None
    if result.returncode != 0:
        return False, None
    lines = (result.stdout or result.stderr or '').strip().splitlines()
    return True, (lines[0] if lines else None)


def find_under_roots(root_strings, relative_paths):
    for root in root_strings:
        base = Path(root).expanduser()
        for relative in relative_paths:
            candidate = base / relative
            if candidate.is_file():
                return str(candidate)
    return None


def find_node(toolbox, extra_roots):
    located = toolbox.locate_executable('node')
    if located:
        return located
    return find_under_roots([*extra_roots], ['nodejs/node.exe', 'node/bin/node', 'node/node.exe'])


def webcli_entry_from_shim(shim_path):
    """Read an npm launcher shim to recover the real JS entry it wraps."""
    try:
        text = Path(shim_path).read_text(encoding='utf-8-sig', errors='replace')
    except OSError:
        return None
    for line in text.splitlines():
        lowered = line.lower()
        if 'node_modules' not in lowered:
            continue
        for marker in ('node_modules/', 'node_modules\\'):
            if marker in line:
                tail = line.split(marker, 1)[1]
                return 'node_modules/' + tail.strip().strip('"').replace('\\', '/')
    return None


def resolve_webcli(toolbox, roots, node, explicit_skill):
    """Find node + the WebCLI entry, preferring a real JS file over a shell shim."""
    if explicit_skill:
        return ([node, explicit_skill] if node else None), 'cli'
    shim = None
    for root in roots:
        for candidate in ('webcli.cmd', 'webcli.ps1', 'webcli'):
            path = Path(root).expanduser() / candidate
            if path.is_file():
                shim = path
                break
        if shim:
            break
    if shim is not None:
        relative = webcli_entry_from_shim(shim)
        if relative:
            resolved = Path(shim).parent / relative
            if resolved.is_file():
                return ([node, str(resolved)] if node else None), 'cli'
    located = find_under_roots(roots, ['@jd/webcli/dist/src/main.js', 'node_modules/@jd/webcli/dist/src/main.js'])
    if located:
        return ([node, located] if node else None), 'cli'
    return None, None


def build_providers(toolbox, only=None, extra=None, roots=None, node_root=None, webcli_skill=None):
    roots = candidate_bins(roots or [])
    if node_root:
        roots = [str(Path(node_root).expanduser()), *roots]
    node = find_node(toolbox, roots)
    providers = {}
    for spec in PROVIDER_SPECS:
        if only and spec['name'] not in only:
            continue
        command = None
        version = None
        if spec['name'] == 'webcli':
            command, _ = resolve_webcli(toolbox, roots, node, webcli_skill)
            if command:
                _, version = run_capture(toolbox, [*command, '--version'])
        else:
            for probe in spec['probes']:
                executable = toolbox.locate_executable(probe[0])
                if not executable:
                    continue
                candidate = [executable, *probe[1:]]
                ok, first_line = run_capture(toolbox, candidate)
                if ok:
                    command, version = candidate, first_line
                    break
            if command is None:
                located = find_under_roots(roots, spec.get('candidates', []))
                if located:
                    candidate = [node, located] if spec.get('needs_node') else [located]
                    if candidate and (spec.get('needs_node') is not True or candidate[0]):
                        ok, first_line = run_capture(toolbox, candidate)
                        if ok:
                            command, version = candidate, first_line
                        else:
                            command = candidate
        if not command:
            continue
        providers[spec['name']] = {
            'kind': spec['kind'],
            'description': spec['description'],
            'guide': spec['guide'],
            'command': command,
            'version': version,
        }
    for item in extra or []:
        name, _, raw = item.partition('=')
        if not raw:
            raise ValueError('--extra expects name=command, got: ' + item)
        providers[name] = {'kind': 'cli', 'command': raw.split(), 'version': None}
    return providers


def build_aliases(providers):
    python = sys.executable
    router = str(REPO / 'scripts' / 'toolbox.py')
    aliases = [{
        'name': 'browser-toolbox-local',
        'display_name': 'Browser + interface toolbox',
        'description': 'Status, launch and interface-automation entry for the installed browser tools.',
        'category': 'web',
        'version': 'local',
        'entry_point': [python, '-X', 'utf8', router],
        'skill_md': str(REPO / 'SKILL.md'),
        'capability_status': 'ready',
        'keywords': ['browser', 'automation', 'interface', 'toolbox'],
    }]
    for name, provider in providers.items():
        aliases.append({
            'name': name + '-local',
            'display_name': name,
            'description': provider.get('description', name),
            'category': 'web',
            'version': provider.get('version') or 'local',
            'entry_point': [python, '-X', 'utf8', router, 'run', name],
            'skill_md': str(REPO / provider.get('guide', 'SKILL.md')),
            'capability_status': 'ready',
            'keywords': ['browser', name, 'automation'],
        })
    return aliases


def discover_webcli_sites(clis_dir):
    """One alias per WebCLI sub-site so each site is callable directly."""
    directory = Path(clis_dir).expanduser()
    if not directory.is_dir():
        return []
    entries = []
    for child in sorted(directory.iterdir()):
        skill = child / 'SKILL.md'
        if not child.is_dir() or not skill.is_file():
            continue
        name = child.name
        title = name
        for line in skill.read_text(encoding='utf-8', errors='replace').splitlines():
            if line.startswith('# '):
                title = line[2:].strip() or name
                break
        entries.append({
            'name': 'webcli:' + name,
            'display_name': title,
            'description': 'WebCLI site adapter: ' + name,
            'category': 'web',
            'command': ['browser', 'eval'],
            'skill_md': str(skill),
        })
    return entries


def build_parser():
    parser = argparse.ArgumentParser(description='Configure the browser + interface toolbox.')
    parser.add_argument('--config', help='Where to write runtime.json')
    parser.add_argument('--registry', help='Where to merge local CLI entries')
    parser.add_argument('--only', action='append', help='Restrict to these provider names (repeatable)')
    parser.add_argument('--extra', action='append', help='Add a provider as name=command (repeatable)')
    parser.add_argument('--root', action='append', help='Extra directory to probe for tools (repeatable)')
    parser.add_argument('--node-root', help='Directory holding node, used for JS-based tools')
    parser.add_argument('--webcli-skill', help='Path to the WebCLI entry script')
    parser.add_argument('--clis-dir', help='WebCLI site adapter directory, for one alias per site')
    parser.add_argument('--no-registry', action='store_true', help='Write runtime.json only')
    parser.add_argument('--force', action='store_true', help='Overwrite an existing runtime.json')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    toolbox = import_toolbox()
    target = config_path(args.config)
    if target.exists() and not args.force:
        raise FileExistsError(str(target) + ' exists; pass --force to overwrite')

    providers = build_providers(
        toolbox,
        only=set(args.only) if args.only else None,
        extra=args.extra,
        roots=args.root,
        node_root=args.node_root,
        webcli_skill=args.webcli_skill,
    )
    config = {'format_version': 'browser-task-router/v1', 'providers': providers}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')

    output = {
        'config': str(target),
        'detected': sorted(providers),
        'missing': sorted(spec['name'] for spec in PROVIDER_SPECS if spec['name'] not in providers),
    }

    if not args.no_registry:
        registry = Path(args.registry).expanduser() if args.registry else Path.home() / '.browser-task-router' / 'local_cli.json'
        aliases = build_aliases(providers)
        sites = discover_webcli_sites(args.clis_dir or (Path.home() / '.webcli' / 'clis'))
        merged, added = merge_registry(read_registry(registry), [*aliases, *sites])
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
        output['registry'] = str(registry)
        output['registered'] = added
        output['webcli_sites'] = [site['name'] for site in sites]

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, FileNotFoundError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
