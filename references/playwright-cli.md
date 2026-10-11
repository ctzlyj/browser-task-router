# Playwright CLI

Upstream: https://github.com/microsoft/playwright

Playwright excels at deterministic control, tracing, network inspection and cross-browser testing.

## Check it

```bash
python scripts/toolbox.py status playwright-cli
python scripts/toolbox.py run playwright-cli -- --version
```

## Working pattern

```bash
python scripts/toolbox.py run playwright-cli -- -s=<task-name> open https://example.com
python scripts/toolbox.py run playwright-cli -- -s=<task-name> snapshot
python scripts/toolbox.py run playwright-cli -- -s=<task-name> close
```

Use an explicit session name so parallel tasks do not collide, and read `open --help` for current browser
and executable options.

## Habits

- Headless task-owned sessions by default. Only drive a real profile when the task needs that login and the
  user is fine with it.
- Only claim coverage for the engines you actually ran. A Chromium-only pass says nothing about Firefox or
  WebKit.
- For MCP-based integrations, see `references/playwright-mcp.md`; the CLI is the lighter default.
- A first run should open one page, read something real from it, then close the same session.
