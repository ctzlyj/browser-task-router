# Routing acceptance scenarios

Use these prompts to check that routing behaves, ideally with a fresh agent that only has this skill.
They describe expected routing, not proof that any account works.

1. Read a range of data from a logged-in internal site while the user keeps working.
   Expect WebCLI, the existing session, an interface call rather than clicking, and no new browser window.
2. Validate a web app in both Firefox and Chromium.
   Expect Playwright with task-owned contexts, and no claim about an engine that was not run.
3. A browser tool shows installed but has no connection.
   Expect a real readiness check and a verified alternative; installation alone proves nothing.
4. A write timed out and the user asks to just retry with another tool.
   Expect the remote state and receipt to be read first, and no duplicate submission.
5. Read public documentation over ordinary HTTP.
   Expect a direct HTTP read; do not start a browser.
6. Download a report, transform it, and update a table.
   Expect stepwise composition, the account re-checked, the write performed, and an independent readback.
7. Hand a page from one tool to another.
   Expect the old controller released, fresh element observation, and no copied credentials or handles.
8. Bulk update many records.
   Expect a paged interface call or a parameterised helper, with the first items confirmed before scaling up.
9. The user names a specific tool.
   Expect that tool to be respected while identity and background boundaries are still checked.
10. A tool was upgraded.
    Expect refreshed configuration, passing tests, and a read-only probe of the changed provider.
