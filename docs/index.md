# taskai

A command-line task manager with AI features.

![taskai on the command line](_static/demo.gif)

<!-- demo.gif: record a short terminal session and drop it at
     docs/_static/demo.gif. Full shot list + exact commands in
     docs/_static/demo-script.md (not a published page - a production note
     for whoever records this). -->

## What you can do

- **Manage a tree of todo items** — create, view, update, move, and delete
  items at any depth; there's no separate notion of "lists"
- **Attach data to each item** — description, due date, priority, status,
  completion, comments
- **Filter** — `task show 'priority>=2' 'due<10-01-2026'` narrows the tree to
  matching items and their parents
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
