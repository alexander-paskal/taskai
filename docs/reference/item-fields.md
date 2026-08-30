# Item fields

Pass any of these as `--field value` to `task create`, `task add`, or
`task update`. Repeat the flag to set several at once.

| Field | Format | Notes | Example |
|---|---|---|---|
| `description` | string | Free text. Quote it if it contains spaces. | `--description "needs review"` |
| `due_by` | `MM-DD-YYYY` | Stored as a date. | `--due_by 09-15-2026` |
| `priority` | integer | Higher is not special-cased anywhere yet; it's yours to sort by. Default `0`. | `--priority 1` |
| `status` | string | Free text (e.g. `"blocked"`, `"in progress"`). Shown on the node in the web UI. | `--status "in progress"` |
| `completed` | `true` / `false` | Prefer `task done` / `task complete`, which also complete descendants. | `--completed true` |

## Fields set by other commands, not `--field`

| Field | Set with |
|---|---|
| name | `task rename <id> <new name>` |
| parent | `task move <id\|name> <new parent id\|name>` |
| soft-links | `task link` / `task unlink` |
| comments | `task comment <id> <text>` |
| sibling order | `task reorder <id1> before\|after <id2>` |

:::{note}
`task update <id> --due_by ...` and `task update <id> --depends_on ...`
currently don't take effect (a known parsing gap). Set `due_by` at
`create` / `add` time, and use `task link` for relationships, until that's
fixed.
:::
