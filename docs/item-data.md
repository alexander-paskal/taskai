# Modifying an item's data

Beyond its name and place in the tree, each item carries a handful of data
fields. Set them as named options — `--<name> <value>` — on `task create`,
`task add`, and `task update`:

```bash
task create "Ship v2" --due_by 10-01-2026 --priority 2
task update "Ship v2" --status "in progress" --description "cut the release branch first"
```

| Option | Value | Meaning |
|---|---|---|
| `--description` | text | A longer note on the item. Quote it if it has spaces. |
| `--due_by` | `MM-DD-YYYY` | When the item is due. |
| `--priority` | integer | A number you choose; sort or filter by it. Default `0`. |
| `--status` | text | A free-form state such as `blocked` or `in review`. Shown on the node in the browser view. |
| `--completed` | `true` / `false` | Whether the item is done. |

## Dedicated commands

Some changes have their own command instead of an option:

```bash
task rename 4 "Ship v2.1"
task status 4 "in review"           # same as --status, as its own verb
task comment 4 "waiting on QA sign-off"
task complete 4                     # mark done — also completes descendants
task done 4                         # alias for complete
```

`task complete` / `task done` mark the item **and everything under it**
complete. To reopen something, set it back explicitly:

```bash
task update 4 --completed false
```
