# Browser-Use

Upstream: https://github.com/browser-use/browser-use

Browser-Use drives a browser through helper calls, which makes it a good fit for exploring an unknown site
and for multi-step navigation.

## Check it

```bash
python scripts/toolbox.py status browser-use
python scripts/toolbox.py run browser-use -- --version
```

## Working pattern

Pass helper code on stdin. A minimal loop:

```bash
python scripts/toolbox.py run browser-use -- python -
```

```python
tab = new_tab("https://example.com")
wait_for_load()
print(page_info())
```

Helpers such as `new_tab`, `wait_for_load`, `page_info` and `close_tab` cover most navigation and reading.
Check the installed guide for the current helper set before assuming an older command name still exists.

## Habits

- Record the tab you created and close only that tab. Never blanket-close all tabs.
- The default profile is usually empty; do not assume a business login exists. Reuse an existing
  authenticated tool when the task needs a real account.
- Do not activate or focus a tab to recover a background failure when the user wants the screen left alone.
