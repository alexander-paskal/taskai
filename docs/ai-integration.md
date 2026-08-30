# AI integration

The `task ai` commands send a prompt to a language model and act on its
response. They're optional — the rest of taskai works without them — and need a
model configured first.

## Choosing a model

Run `task setup` and pick a provider, then a model:

```text
$ task setup
Beginning setup
  1. openai
  2. anthropic
  3. gemini
  4. vertex_ai
  5. groq
  ...
  20. ollama

Select a provider (number or name): 3
  1. gemini-3.7-flash
  2. gemini-3.1-pro-preview
  3. gemini-3.6-flash
  4. gemini-3.5-flash-lite
  5. gemini-2.5-pro

Select a model for 'gemini' (number or name): 1
Storing: gemini/gemini-3.7-flash
Make sure these environment variables are set:
  GEMINI_API_KEY
Setup complete! Use 'task config set|get|list' to interact with your configuration options
```

Either prompt also accepts free-typed text, so you can name a model that isn't
in the menu. This stores the `AI_MODEL` config key; you can also set it
directly:

```bash
task config set AI_MODEL openai/gpt-4o-mini
```

## Provider credentials

The model is called through [litellm](https://github.com/BerriAI/litellm),
which reads each provider's credentials from environment variables:

```{include} _generated/providers.md
```

For `azure`, the model name is your deployment name; for `ollama`, it's
whatever model you've pulled locally.

## `task ai <prompt>`

Describe the change you want. The model turns it into a series of ordinary
taskai commands and runs them:

```bash
task ai "add a task under Launch blog to buy a domain, due next Friday"
task ai "mark every hosting-related task done and add a subtask to configure DNS"
```

### `--context <path[,path...]>`

Fold one or more files into the prompt as extra context:

```bash
task ai "turn my meeting notes into tasks under Launch blog" --context notes.md
task ai "reconcile these" --context plan.md,status.md
```

### `--reasoning <level>`

Hint how hard the model should think before answering. Accepts `minimal`,
`low`, `medium`, `high`, `disable`, or `none`. Support and effect vary by
provider and model.

## `task ai headstart <id>`

Narrower than a full prompt: it asks the model for the single next concrete
step on one item and saves the answer as a comment on that item.

```bash
task ai headstart 5
```
