# Browser mode

```bash
task browser
```

This starts a local web server and serves a visual view of your task tree.

## The canvas

The whole tree is drawn as connected cards. Drag to pan, scroll to zoom.
Double-click a card to center on it and open its edit panel.

<!-- screenshot: a tree with a few branches AND a chain (task next), wide
     enough to show a plain parent/child branch, a chain rendered as its
     straight bold-arrow line with real children fanned off to its side, and
     at least one soft link (dashed ghost card) all in the same shot -->

- **Completed** items are tinted green.
- **`status`** text appears in the top corner of a card (or the color set by
  `STATUS_COLORS` in config, if one's configured for that status).
- **`due_by`**, if set, appears in the bottom corner.
- **Soft links** (`task link`) are drawn as a dashed copy of the linked item
  under its host, distinct from the solid parent/child connectors.
- **Chains** (`task next`/`task chain`) render as a straight bold arrow; a
  chain link's own real children fan out to its side rather than centering
  below it.

## The edit panel

Click a card to select it; double-click it, or press `e`, to open the edit
panel on the right. It has a field for the name, description, status, color,
priority, due date, and completion, plus a comment feed. Changes are saved as
you make them — there is no save button. In a single-line field, `Enter`
commits the change and leaves the field.

<!-- screenshot: the edit panel open on a card with most fields filled in
     (including a couple of comments, to show the feed) -->

## The console

The panel at the bottom takes raw `task` commands and runs them against the
same data, printing their output and refreshing the canvas. Anything you can
type on the command line works here.

<!-- screenshot: the console expanded with a few example commands and their
     output already in the scrollback -->

Filtering sticks: after `show 'priority>=2'` the canvas shows only the matches
(and their parents), and it stays scoped that way as you edit and delete —
until `show all` clears it.

## Keyboard

Press `?` for the full list in the app. The essentials:

| Key | Action |
|---|---|
| arrows | move the selection through the tree |
| `Ctrl`+`↑` / `↓` | jump out of / into a chain member's subtree (`↑`/`↓` walk the chain itself) |
| `Shift`+arrows | pan the view |
| `+` / `-` / `0` | zoom in / out / fit |
| `t` | flip the layout between growing down and growing right |
| `e` | toggle the edit panel |
| `` ` `` | focus / close the console |
| `a` | add a child of the selected card and name it |
| `d` | toggle done on the selected card |
| `Delete` | delete the selected card |
| `Esc` | leave a field, then close the panel, then (with every panel closed) show the whole tree |
