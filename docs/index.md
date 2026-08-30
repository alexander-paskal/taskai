# taskai

A command-line task manager with AI features.

Everything is an **item** — a node in a tree. Any item can be the parent of any
other, to any depth, so the same tool handles a one-off reminder and a deeply
nested project without a separate notion of "lists". Optional AI commands turn
plain English into task operations, and a local web UI renders the whole tree
as a canvas you can pan, zoom, and edit.

```bash
pip install taskai-cli
task setup
```

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} 🚀 Getting started
:link: getting-started
:link-type: doc

Install taskai, point it at a model, and build your first item tree.
:::

:::{grid-item-card} 📖 Command reference
:link: reference/commands
:link-type: doc

Every subcommand, argument, and flag — the same text `task help` prints.
:::

:::{grid-item-card} 🏷️ Item fields
:link: reference/item-fields
:link-type: doc

The `--field value` options `create`, `add`, and `update` accept.
:::

:::{grid-item-card} ⚙️ Configuration
:link: reference/config
:link-type: doc

Config keys, and the environment variable each AI provider needs.
:::
::::

```{toctree}
:hidden:
:caption: Getting started

getting-started
```

```{toctree}
:hidden:
:caption: Reference

reference/commands
reference/item-fields
reference/config
```
