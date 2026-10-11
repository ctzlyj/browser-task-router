# Browser-Act

Upstream: https://github.com/browser-act/skills

Browser-Act runs skill-driven browser actions and supports local and remote modes. Read its skill list from
the installed CLI so you use commands that actually exist:

```bash
python scripts/toolbox.py status browser-act
python scripts/toolbox.py run browser-act -- get-skills core
```

## Habits

- Prefer verified local modes for the task at hand; confirm the selected account instead of trusting a label.
- Use a task-named browser or session so cleanup is unambiguous.
- Local/ordinary mode, advanced stealth, proxies, captcha assistance and remote handoff have different
  requirements. Missing remote or service access only rules out that feature, not local mode.
- Do not upload business data to a remote service unless the task actually calls for it.
