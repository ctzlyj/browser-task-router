# Playwright MCP

Upstream: https://github.com/microsoft/playwright-mcp

Playwright exposed as a stdio MCP server, for clients and workflows that benefit from MCP tool calls.

## Check it

```bash
python scripts/toolbox.py status playwright-mcp
```

## Working pattern

```bash
python scripts/toolbox.py run playwright-mcp -- --headless --isolated
```

The server speaks stdio: run it from an MCP-capable client that will initialise it and call tools. Do not
start the server and leave it with no client, and end the client and server when the task is done.

## Habits

- Use MCP when the client or flow genuinely benefits; the CLI is the lower-overhead path otherwise.
- Success means a real navigation and readback, not merely a successful `tools/list`.
- Defaults are headless and isolated; decide deliberately before pointing it at a profile that carries a login.
