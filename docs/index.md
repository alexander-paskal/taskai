# taskai

A command-line task manager with AI features.

![taskai on the command line](_static/demo.gif)

<!-- demo.gif: record a short terminal session (create a tree, `task show all`,
     complete an item, `task ai ...`) and drop it at docs/_static/demo.gif -->

## What you can do

- **Manage a tree of todo items** — create, view, update, move, and delete
  items at any depth; there's no separate notion of "lists"
- **Attach data to each item** — description, due date, priority, status,
  completion, comments
- **Soft-link** an item under more than one parent without moving it
- **Interactive mode** — run `task` with no arguments for a live view that
  redraws as you type commands
- **Browser mode** — `task browser` renders the whole tree as a pan/zoom
  canvas with an inline edit panel and a command console
- **AI integration** — describe a change in plain English and let a language
  model carry it out, or ask it for the next step on a given item

New here? Start with **[Getting started](getting-started.md)**.

```{toctree}
:hidden:
:caption: Getting started

getting-started
```

```{toctree}
:hidden:
:caption: Using taskai

configuration
managing-the-tree
item-data
interactive-mode
browser-mode
ai-integration
```

```{toctree}
:hidden:
:caption: Reference

commands
```
