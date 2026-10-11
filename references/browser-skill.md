# BrowserSkill (Tencent)

Upstream: https://github.com/Tencent/BrowserSkill

BrowserSkill connects to a browser you can observe and, when needed, take over by hand. It suits live
observation, human handoff and cases where you want the user watching the same session.

## Check it

```bash
python scripts/toolbox.py status browser-skill
python scripts/toolbox.py run browser-skill -- status
```

## Basic session

```bash
python scripts/toolbox.py run browser-skill -- session start --json
python scripts/toolbox.py run browser-skill -- browsers
python scripts/toolbox.py run browser-skill -- session stop <session-id>
```

Keep the returned session id and use it for everything in this task. When several browsers are connected,
pick an explicit verified browser id rather than whichever is first.

If a daemon or connection is missing, start it deliberately and only once: probe status first, confirm nothing
is already running, then start. A live but unresponsive daemon is a signal to read its logs, not a reason to
start a second one.

## Habits

- Do not grab default focus or borrow the user's working tab unless they asked; prefer a task-owned session.
- Do not disable confirmation or safety settings to make a step go faster.
- Stop only the session you started, and only after checking it is yours.
