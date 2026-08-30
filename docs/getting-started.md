# Getting started

This walks you from an empty machine to a small project tree you can view, edit,
and drive with AI. It should take about five minutes.

## Install

```bash
pip install taskai-cli
```

This puts a single command on your `PATH`: `task`. taskai keeps one database per
machine user, under `.taskai/task_db/<user>.json` in your home directory — no
server, no account.

## Point taskai at a model (optional)

The core task commands work with no configuration. The `task ai` commands need a
language model, which you pick with `task setup`:

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

Either prompt also accepts free-typed text, so you can name a model newer than
the built-in menu. Then export the credential it told you about:

```bash
export GEMINI_API_KEY=...
```

See [Configuration](reference/config.md) for the full provider list and the
other config keys.

## Create your first items

Every item is a tree node. Start with a root item, then hang children off it.
Names with spaces must be quoted.

```bash
task create "Launch blog" --due_by 09-15-2026
task add "Launch blog" "Write first post" --priority 1
task add "Launch blog" "Set up hosting"
task add "Write first post" "Draft outline"
```

`create` makes a new **root** item; `add` attaches a child to an item that
already exists. The parent can be named or referred to by id.

## View the tree

```bash
task show all
```

Every item is listed with its id prepended. Use an id (or a name) to see one
item in full:

```bash
task show "Write first post"
task show 2
```

## Work an item and finish it

```bash
task status 2 "in progress"
task comment 2 "outline done, drafting the intro"
task done 2
```

`task done` (alias: `task complete`) marks the item **and everything under it**
complete. Clean finished work up with `task clear`:

```bash
task clear "Launch blog"   # delete completed items under that parent
task clear                 # delete every completed item, anywhere
```

## Let the AI do it

With a model configured, describe the change instead of spelling out commands.
The model translates your prompt into a series of the commands above and runs
them:

```bash
task ai "add a task under Launch blog to buy a domain, due next Friday"
task ai "break 'Set up hosting' into smaller subtasks" --context notes.md
```

`task ai headstart <id>` is narrower: it asks the model for the single next
concrete step on one item and saves the answer as a comment.

## Open the web UI

```bash
task browser
```

This starts a local web server and serves a canvas view of your tree:

- **pan and zoom** the graph; completed items are tinted green, and soft-links
  (`task link`) appear as dashed "shadow" copies under their host item
- **click a node** to open an edit panel — every field writes back immediately,
  there is no save button
- a **console** at the bottom runs raw `task` commands against the same data

Edits made in the browser are not picked up by an already-running interactive
`task` session until you restart it.

## Where to next

- [Command reference](reference/commands.md) — the complete surface, also
  available offline as `task help`
- [Item fields](reference/item-fields.md) — everything you can set with
  `--field value`
- Run `task examples` for more copy-pasteable command sequences
