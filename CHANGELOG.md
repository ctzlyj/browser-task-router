# Changelog

## 0.1.0 - 2026-10-12

First public release.

- Unified `scripts/toolbox.py` entrypoint: `status`, `run`, `eval-url`, `browser-endpoint`, `sync-file`.
- Owned-browser management: one headless Chromium per machine, reused across Browser-Use and
  BrowserSkill sessions; managed daemon startup and `--no-focus` when the config describes an owned browser.
- `scripts/setup.py` detects WebCLI, BrowserSkill, Browser-Use, Browser-Act and Playwright CLI/MCP,
  writes `runtime.json`, and registers one alias per tool plus one per WebCLI site adapter.
- Interface-first guidance in `docs/interface-first.md`.
- Per-tool usage guides under `references/`.
- Cross-platform unit tests and a GitHub Actions matrix (ubuntu, windows, macos).
