# Providers, entrypoints and install links

Everything runs through one entrypoint so arguments survive and the exit code is honest:

```bash
python scripts/toolbox.py status
python scripts/toolbox.py status webcli
python scripts/toolbox.py run <provider> -- <arguments...>
```

`status` reports `installation: installed|missing` plus the resolved executable. It cannot prove a
connection or a logged-in account - check that per task with a real, harmless call. If a provider is
missing, install it from the link below and re-run `python scripts/setup.py --force`.

| Provider | Kind | Upstream | Typical entry |
| --- | --- | --- | --- |
| WebCLI | browser-context | interface-first, session reuse | `browser eval`, `browser get`, `browser network` |
| BrowserSkill | browser-context | https://github.com/Tencent/BrowserSkill | `session start`, `status`, `stop` |
| Browser-Use | browser-context | https://github.com/browser-use/browser-use | Python helpers on stdin |
| Browser-Act | browser-context | https://github.com/browser-act/skills | `get-skills`, skill actions |
| Playwright CLI | cli | https://github.com/microsoft/playwright | `playwright-cli -s=<name> ...` |
| Playwright MCP | cli | https://github.com/microsoft/playwright-mcp | stdio MCP server |

WebCLI has no public upstream: it is the local "make any website a CLI" layer that runs inside an already
authenticated browser and is the preferred path for calling a site's own HTTP interfaces. See
`references/webcli.md`.

## Config layout

`python scripts/setup.py` writes `<config dir>/browser-task-router/runtime.json`, where `<config dir>` is
`%APPDATA%` on Windows and `$XDG_CONFIG_HOME` or `~/.config` elsewhere. It also merges `*-local` aliases into
`~/.browser-task-router/local_cli.json` without modifying unrelated entries.

Override the config location with `BROWSER_TOOLBOX_CONFIG` or `--config`. A provider entry looks like:

```json
{
  "kind": "browser-context",
  "command": ["C:/path/to/tool.exe", "--flag"],
  "env": {"TOOL_HOME": "C:/path/to/state"}
}
```

`kind` is `browser-context` for tools that act inside a real browser session and `cli` for command tools.
The router uses `kind` when it needs a browser page context, for example for `toolbox.py eval-url`.
