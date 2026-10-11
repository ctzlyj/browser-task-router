---
name: browser-task-router
description: "One router for browser and interface automation: WebCLI, Tencent BrowserSkill, Browser-Use, Browser-Act and Playwright CLI/MCP, with interface-first automation preferred over clicking. Use when a task needs a logged-in website, internal HTTP interface, scraping, downloads/uploads, bulk operations, cross-browser tests or a workflow spanning several browser tools."
metadata:
  short_description: "Route browser + interface automation across WebCLI, BrowserSkill, Browser-Use, Browser-Act and Playwright"
---

# Browser + interface router

Interpret the goal yourself and pick or combine capabilities. The user describes a goal, not a tool.
This is a toolbox, not a whitelist or a task ceiling: add task-local helpers when they fit.

## First run

```bash
python scripts/setup.py          # detect tools, write runtime.json, register aliases
python scripts/toolbox.py status # installed / missing per provider
```

Read `references/providers.md` for the install links and exact entrypoints.
Installed is not the same as connected, and connected is not the same as a usable logged-in session:
check the real account before doing anything that matters.

## Pick the right capability

| Goal | Reach for |
| --- | --- |
| Logged-in site, call its own HTTP interfaces, bulk read or write | **WebCLI** - interface-first, reuses the real session |
| Borrow a user-controlled browser tab, human handoff, live observation | **BrowserSkill** |
| Explore an unknown site, multi-step navigation, scripted browser work | **Browser-Use** |
| Skill-driven actions, local or remote/cloud browser modes | **Browser-Act** |
| Deterministic UI tests, tracing, network inspection, MCP clients | **Playwright CLI / MCP** |
| Static or public HTTP content | Plain HTTP request first; do not start a browser |

Interface-first beats clicking: when a page is backed by an HTTP interface you can call, call it, and keep
page clicking for login, exploration or cases the interface truly cannot cover. See `docs/interface-first.md`.

## Compose across tools without losing state

- Carry context forward: goal, step, site, verified account, read/write intent, owning tool, owned tab or
  session, and where results or receipts are saved. Pass URLs, ids, structured output and files between steps.
- One controller per tab at a time. Before handing off, stop or release the old controller, then re-observe with
  the new tool and re-check identity. Browser element handles, debugger sessions and profile state do not travel.
- Keep the user's own browser and tabs alone unless they asked for them; prefer a task-owned session. Do not
  restart the user's browser or flip its debug settings silently.
- Prefer reusing an existing logged-in session over copying credentials or profiles around.

## Matters that actually bite

- Choosing and switching tools, bounded diagnosis and recovery inside the current goal do not need another
  permission question. Ask only when identity, new authority or a genuine dead end is at stake.
- If a write times out or the response is lost, the result is unknown: read the remote state and the receipt
  before trying again. Switching tools is not permission to replay, and a login or permission error is not a
  reason to route around it with a different tool.
- Credentials, tokens and personal profile data stay out of source, tests, logs, docs, screenshots, commits and
  replies. Do not paste a raw cookie into a script just because it is convenient.
- A tool being installed does not prove a business account works. Verify with the real target before a batch.

## Finish clean

Say which steps ran, which tool handled each one, and what is still unverified. Close only tabs and sessions
this task opened. Keep receipts and user data. A public-page smoke test only proves control of that test
profile, not access to a real account.

## References

- `references/providers.md` - install links, entrypoints and status checks for every tool.
- `references/webcli.md`, `references/browser-skill.md`, `references/browser-use.md`,
  `references/browser-act.md`, `references/playwright-cli.md`, `references/playwright-mcp.md` - per-tool usage.
- `docs/interface-first.md` - how to automate through a site's own interfaces instead of the UI.
- `docs/routing-scenarios.md` - acceptance prompts for checking that routing behaves.
- `references/maintenance.md` - keeping the router and its tools in sync.
