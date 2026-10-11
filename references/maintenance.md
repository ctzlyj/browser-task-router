# Maintenance

Tools change. Keep the router useful by staying honest about versions and state.

## When a tool is upgraded

1. Re-run `python scripts/setup.py --force` to refresh commands and versions in `runtime.json`.
2. Run the tests: `python -m unittest discover -s tests -v`.
3. Validate the changed provider with a real read-only call before trusting it for bulk work.

## Keep local edits

If you edited a provider guide or adapter, do not let an update overwrite it silently. `toolbox.py sync-file`
does a three-way comparison and either updates, or stages the incoming file as a candidate:

```bash
python scripts/toolbox.py sync-file --target <local> --incoming <new-upstream> \
    --baseline <old-upstream> --candidates <dir>
```

`updated` means the local file matched the baseline and was replaced. `merge_required` means it did not, the
local file is untouched, and the incoming copy is sitting in `<dir>` for you to merge by hand. A local-only
file with no baseline is never replaced.

## Do not

- Do not edit files inside npm or pip package directories; they disappear on upgrade. Keep adapters and
  overlays in your own skills directory.
- Do not update a tool while a write from that tool is unresolved; reconcile the result first.
- Do not restore an old whole configuration over newer unrelated changes; roll back only what you touched.
