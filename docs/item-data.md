# Modifying an item's data

Beyond its name and place in the tree, each item carries a handful of data
fields. Set them as named options — `--<name> <value>` — on `task create`,
`task add`, and `task update`:

```bash
task create "Ship v2" --due 10-01-2026 --priority 2
task update "Ship v2" --status "in progress" --description "cut the release branch first"
```

| Option | Value | Meaning |
|---|---|---|
| `--description` | text | A longer note on the item. Quote it if it has spaces. |
| `--due` | `MM-DD-YYYY` | When the item is due. |
| `--priority` | integer | A number you choose; sort or filter by it. Default `0`. |
| `--status` | text | A free-form state such as `blocked` or `in review`. Shown on the node in the browser view. |
| `--completed` | `true` / `false` | Whether the item is done. |

## Dedicated commands

Every field above also has its own command, so you can skip `update` and the
`--` for the common case:

```bash
task due 4 tomorrow                 # same as: task update 4 --due tomorrow
task priority 4 2
task status 4 "in review"
task color 4 "#ff8844"
task description 4 needs a rewrite  # the value needn't be quoted
task due 4                          # no value clears the field
```

The value is everything after the item, so multi-word text and dates like
`task due 4 Dec 31 2026` work without quotes.

`task description` takes an `-a` flag to append to the existing description
(on a new line) instead of replacing it:

```bash
task description 4 first draft outline
task description 4 -a also cover the hosting options
```

A few other changes have their own command too:

```bash
task rename 4 "Ship v2.1"
task comment 4 "waiting on QA sign-off"
task complete 4                     # mark item 4 done
task done 4                         # alias for complete
task done 4 -r                      # also complete every descendant
```

`task complete` / `task done` mark just that item complete; add `-r` (or
`-recursive`) to include all its descendants. To reopen something, use
`task undone` (which takes the same `-r` flag) or set the field explicitly:

```bash
task undone 4
task update 4 --completed false
```
