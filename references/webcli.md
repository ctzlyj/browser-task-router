# WebCLI

Make any website a CLI. WebCLI drives a real, already logged-in browser and exposes both page actions and
the site's own HTTP interfaces. This is the default choice when the goal is "read or write through the
site", because it reuses the real session instead of rebuilding authentication.

## Check it

```bash
python scripts/toolbox.py status webcli
python scripts/toolbox.py run webcli -- --version
python scripts/toolbox.py run webcli -- list
```

`list` shows the adapters available on this machine. Read an adapter before using it:

```bash
python scripts/toolbox.py run webcli -- info <name>
```

## Two ways to work

**Adapter commands** are prebuilt, parameterised calls for a known site. Prefer them when they exist:

```bash
python scripts/toolbox.py run webcli -- <site> <command> <args>
```

**Direct interface calls** run in the active page context, so the request carries the page's own cookies and
session. This is the interface-first path:

```bash
python scripts/toolbox.py eval-url --with webcli --url "https://example.com/api/list?page=1"
python scripts/toolbox.py eval-url --with webcli --code "return document.title"
```

Inside the snippet you get normal page JavaScript: `fetch`, `document`, `window`, and any framework on the
page. Use it to call an interface the page itself calls, then parse the JSON you get back. Prefer this over
repeated clicking whenever the page has a stable interface behind it.

Useful page operators for the parts interfaces cannot cover: `browser open`, `browser get`, `browser click`,
`browser fill`, `browser network` (inspect requests), `browser extract`, `browser screenshot`.

## Habits that keep it reliable

- Stay on the page that owns the interface; a call from an unrelated origin will not carry the right session.
- Capture what an interface needs once (parameters, headers, tokens the page already computes) and reuse it,
  rather than re-deriving it by clicking through the UI each time.
- For bulk reads, page through and check the last page explicitly; do not assume a short page means the end.
- For writes, confirm what actually persisted by reading it back from the interface, not from the UI.
- Keep one tab under one controller. If another tool needs the same page, release it first and re-read state.
