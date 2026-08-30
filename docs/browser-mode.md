# Browser mode

```bash
task browser
```

This starts a local web server and serves a visual view of your task tree.

## The canvas

The whole tree is drawn as connected cards. Drag to pan, scroll to zoom, and
double-click a card to center and zoom on it.

- **Completed** items are tinted green.
- **`status`** text appears in the top corner of a card.
- **Soft links** (`task link`) are drawn as a dashed copy of the linked item
  under its host, distinct from the solid parent/child connectors.

## The edit panel

Click a card to select it and open the edit panel on the right. It has a field
for the name, description, status, priority, due date, and completion. Changes
are saved as you make them — there is no save button.

## The console

The panel at the bottom takes raw `task` commands and runs them against the
same data, printing their output and refreshing the canvas. Anything you can
type on the command line works here.
