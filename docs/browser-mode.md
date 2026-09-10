# Browser mode

```bash
task browser
```

This starts a local web server and serves a visual view of your task tree.

## The canvas

The whole tree is drawn as connected cards. Drag to pan, scroll to zoom.
Double-click a card to center on it and open its edit panel.

- **Completed** items are tinted green.
- **`status`** text appears in the top corner of a card.
- **Soft links** (`task link`) are drawn as a dashed copy of the linked item
  under its host, distinct from the solid parent/child connectors.

## The edit panel

Click a card to select it; double-click it, or press `e`, to open the edit
panel on the right. It has a field for the name, description, status, priority,
due date, and completion, plus a comment feed. Changes are saved as you make
them — there is no save button. In a single-line field, `Enter` commits the
change and leaves the field.

## The console

The panel at the bottom takes raw `task` commands and runs them against the
same data, printing their output and refreshing the canvas. Anything you can
type on the command line works here.

Filtering sticks: after `show 'priority>=2'` the canvas shows only the matches
(and their parents), and it stays scoped that way as you edit and delete —
until `show all` clears it.

## Keyboard

Press `?` for the full list in the app. The essentials:

| Key | Action |
|---|---|
| arrows | move the selection through the tree |
| `Shift`+arrows | pan the view |
| `+` / `-` / `0` | zoom in / out / fit |
| `e` | toggle the edit panel |
| `` ` `` | focus / close the console |
| `a` | add a child of the selected card and name it |
| `d` | toggle done on the selected card |
| `Delete` | delete the selected card |
| `Esc` | leave a field, then close the panel, then clear the selection |
