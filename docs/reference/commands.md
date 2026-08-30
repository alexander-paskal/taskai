# Command reference

This is the complete command surface. The exact same text is available offline —
run `task help`, or `task` with no arguments to drop into interactive mode.

:::{note}
This page is generated from `taskai/help_menu.py` at build time, so it can't
drift from what `task help` prints.
:::

```{literalinclude} _help_general.txt
:language: text
```

## Notes

- Commands under **"require the item's id"** will not accept a name — run
  `task show all` to see ids.
- Commands that take `{id|name}` accept either. A name is matched against every
  item with `fnmatch` (so `Doc*` works); if it matches **more than one** item
  the command is rejected and lists the candidate ids — use an id in that case.
- `task ai` sends your prompt to the model named by the `AI_MODEL` config key.
  Set it with `task setup` or `task config set AI_MODEL <provider>/<model>`; see
  [Configuration](config.md).
