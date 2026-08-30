# Configuration

taskai keeps a small set of configuration values alongside your items. Read and
change them with `task config`:

```bash
task config show           # list every key and its current value
task config get <key>
task config set <key> <value>
task config pop <key>      # remove a key; it returns to its default
```

## Keys

`AI_MODEL`
: The model the `task ai` commands call, written as a `provider/model` string
  (for example `gemini/gemini-3.7-flash` or `openai/gpt-4o-mini`). Set it with
  `task setup` or directly with `task config set`. See
  [AI integration](ai-integration.md).

`DISPLAY_STRING`
: Space-separated list of item attributes shown per row by `task show`.
  Default: `id name status due_by`.

`DISPLAY_COLORS`
: Space-separated colors, matched position-for-position to `DISPLAY_STRING`.
  Use `_` to leave a column uncolored. Default: `_ white dark_orange _`.

```bash
task config set DISPLAY_STRING "id name priority due_by"
task config set DISPLAY_COLORS "_ white cyan _"
```
