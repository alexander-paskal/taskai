# Changelog

Notable changes, newest first. Loosely follows [Keep a
Changelog](https://keepachangelog.com/); dates are UTC, from the commit
history. Versions before 1.6.6 predate this file and aren't reconstructed
here in detail — see `DEVLOG.md` for the full engineering history back to
the project's start.

## [1.10.0] - Unreleased

CLI expansion.

### Added
- A dedicated command for every item field: `task due 10 tomorrow`,
  `task description 10 ...`, `task priority`, `task color` (`task status`
  already existed). The value needn't be quoted, and leaving it off clears
  the field. `task name` is now an alias for `task rename`.

### Changed
- `due_by` is now just `due` everywhere: `--due`, `task show 'due<...'`, the
  `DISPLAY_STRING` attribute, and the item JSON. Existing databases upgrade
  themselves on load - a stored `due_by` is read in as `due` (only when `due`
  isn't already set) and written back out under the new name, and a saved
  `DISPLAY_STRING` that names `due_by` is rewritten too.

## [Unreleased]

The v1 release polish pass — see `PHASE_1_RELEASE.md` for the full working
list this is drawn from.

### Added
- Per-item DAG node color override (`color` field), and per-status-string
  color mapping via `task config set STATUS_COLORS=...`
- `due_by` shown directly on DAG nodes
- `task browser [port]`
- Multiple accepted `due_by` formats (ISO, `MM/DD/YYYY`, `Dec 31, 2026`,
  etc.) and the relative keywords `today`/`tomorrow`, both when setting a
  value and in filters (`task show 'due_by=today'`)
- Configuration now reaches the browser (`GET /api/style`) — the
  foundation the node-color and status-color features above build on
- Up/down arrows fall back to walking a chain when there's no real tree
  relationship in that direction, instead of dead-ending
- DAG empty-state message when there are no items yet
- Test coverage for the chain feature (previously had none)
- CI: `pytest` and a docs build/linkcheck on every push and PR

### Changed
- **DAG orientation flipped:** the tree now grows rightward with siblings
  stacking downward (previously grew downward with siblings spread
  right) — arrow-key directions rotated to match
- Deleting the selected node in the browser now restores the previously
  selected node instead of always jumping to the whole-tree view
- `task next` now focuses the node it just created in the browser

### Fixed
- Unquoted multi-word input across `create`/`add`/`rename` no longer
  silently truncates

## [1.9.0] - 2026-09-14

Chain data integrity and a full CLI command surface for chains
(`is_chain_head`/`prev_chain_id`/`next_chain_id` and the DAG rendering for
them shipped in the browser work below this).

### Added
- `task chain <prev> <node>` — link two existing items into a chain,
  popping `node` off its current parent first if it has one
- `task unchain <node>` — detach an item from its chain without deleting
  it; it becomes a child of the chain's head's parent
- `task delete <id> -chain` — delete an entire chain in one shot, from
  whichever link you target
- `task clear` now reaches items chained off the thing being cleared, not
  just its direct children

### Fixed
- Deleting a chain's head used to orphan the rest of the chain (the
  parent's `child_ids` kept pointing at the deleted id)
- `task show all` no longer lists every non-head chain member as a
  spurious top-level item
- Linking an item already mid-chain into a different chain no longer
  corrupts both

### Removed
- The stored `is_chain_head` field — it's derived now
  (`prev_chain_id is None and next_chain_id is not None`), removing a
  class of "forgot to update the flag" bugs

## [1.8.1] - 2026-09-10

### Fixed
- Zoom behavior in the browser DAG
- `show` filters persisting correctly through a delete
- Edit panel focus handling, including an `Esc`-related focus bug
- Assorted minor browser UX fixes

## [1.8.0] - 2026-09-09

### Added
- Attribute filters for `task show` (`task show 'priority>=2'
  'due_by<10-01-2026'`), in both the CLI and the browser

## [1.7.1] - 2026-09-09

### Added
- Per-parent "last visited child" memory for `down` navigation in the
  browser DAG

### Changed
- Left/right navigation no longer wraps within a parent's direct
  children - it steps across the whole depth level instead
- `Esc` no longer moves the camera

### Fixed
- Up/down navigation no longer wraps around at the top/bottom of the tree
- Various edit-panel interaction bugs

## [1.7.0] - 2026-09-03

### Added
- Keyboard shortcuts and a shortcuts reference panel in the browser

## [1.6.6] and earlier

Everything from the initial CLI (tree-structured items, no separate
"lists" concept), through the AI layer's migration to `litellm`, to the
first browser DAG view (canvas rendering, pan/zoom, the edit panel, and
the command console). See `DEVLOG.md` for the detailed history.
