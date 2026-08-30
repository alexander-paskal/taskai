# Configuration

taskai stores a small config dict in the same per-user database as your items.
Inspect and change it with:

```bash
task config show            # or: task config list
task config get <key>
task config set <key> <value>
task config pop <key>       # remove a key; it reverts to its default
```

## Keys

`AI_MODEL`
: The model `task ai` calls, as a `provider/model` string
  ([litellm](https://github.com/BerriAI/litellm) naming, e.g.
  `gemini/gemini-3.7-flash`, `openai/gpt-4o-mini`). Unset by default — the AI
  commands are unavailable until it's set. Easiest to set via `task setup`.

`DISPLAY_STRING`
: Space-separated list of item attributes shown per row by `task show`.
  Default: `id name status due_by`.

`DISPLAY_COLORS`
: Space-separated [Rich](https://rich.readthedocs.io/en/stable/appendix/colors.html)
  colors, positionally matched to `DISPLAY_STRING`. Use `_` to leave a column
  uncolored. Default: `_ white dark_orange _`.

## AI provider credentials

`AI_MODEL` only names the model. Each provider's credentials are read by litellm
from environment variables — not stored in taskai. `task setup` prints the ones
your chosen provider needs; the full map:

```{include} _providers.md
```

For providers with no models listed in `task setup` (`azure`, `ollama`), type
the model name directly at the prompt — for Azure that's your deployment name,
for Ollama whatever you've pulled locally (e.g. `llama3`).

:::{note}
The model list in `task setup` is a convenience menu, not a whitelist, and it
goes stale — providers ship new models constantly. If an option looks wrong,
type the current model name directly; it's passed straight through to litellm.
:::
