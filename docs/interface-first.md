# Interface-first automation

Most of the value in browser automation, especially internal systems, comes from calling the interfaces the
page itself already uses, rather than replaying clicks. The page is a rendering of data the site fetches for
you. If you can call the same endpoint, you get structured data, stable field names, and room to batch.

## Why prefer interfaces

- **Structure over pixels.** You get JSON, not a screenshot or a fragile DOM path.
- **Reuse the real session.** Calls made from the page context carry the cookies, headers and tokens the page
  already has, so you do not rebuild authentication.
- **Bulk and resilience.** Paging, retries and partial failures are far easier against an interface than by
  walking a UI.
- **Less breakage.** A stable interface outlives a page layout.

## How to do it

1. **Open the page that owns the data** in the session you want to reuse. The call must originate where the
   session lives.
2. **Find the call.** Watch the network while the page loads or you click the thing you want to automate.
   `browser network` in WebCLI, or the equivalent network view in Playwright, shows method, URL, parameters
   and response.
3. **Call it yourself** and read the JSON back:

   ```bash
   python scripts/toolbox.py eval-url --with webcli --url "https://example.com/api/list?page=1&size=100"
   ```

   Or post a body and inspect the raw response:

   ```bash
   python scripts/toolbox.py eval-url --with webcli --code "const r = await fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify({id: 1})}); return {status: r.status, body: await r.text()}"
   ```

4. **Parameterise** what you learned into a small helper or adapter so the next run is a single call.
5. **Verify** by reading the result back, especially for writes.

## When to fall back to clicking

Not everything is an interface. Keep the UI path for login and one-time setup, for interactions with no
stable endpoint, for actions a single click already does correctly, and for exploring a site you do not know yet.

## Practical notes

- A call from the wrong origin will not carry the session. Stay on the owning page.
- A page being reachable does not mean every endpoint is meant for programmatic use; call what the page itself
  calls, with the scope the account actually has.
- Watch rate limits and batch sizes; prefer paging over flooding.
- Keep tokens, cookies and personal data out of scripts, logs and commits.
