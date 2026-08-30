# Managing the tree

Every item is a node in a tree. An item with no parent is a root; any item can
have children, to any depth. The same item type is used whether it's acting as
a project, a list, or a single task.

Most commands accept either an item's numeric id or its name. Names are matched
with shell-style glob patterns, so `task show "Launch*"` works. If a name
matches more than one item the command stops and shows you the ids to choose
from. Names with spaces must be quoted.

## Create items

```bash
task create "Launch blog"                 # a new root item
task add "Launch blog" "Write first post"  # a child of an existing item
```

`create` always makes a root item. `add` attaches a child to a parent that
already exists — give the parent first, then the new item's name. Both accept
[item data](item-data.md) as named options:

```bash
task add "Launch blog" "Set up hosting" --due_by 09-30-2026 --priority 1
```

## View items

```bash
task show all              # the whole tree, ids prepended
task show 4                # one item in full, by id
task show "Set up hosting" # one item in full, by name
```

## Move items

```bash
task move "Set up hosting" "Write first post"   # reparent under another item
task move 5 ""                                  # move back to the top level
```

## Reorder siblings

```bash
task reorder 3 before 2
task reorder "Write copy" after "Design mockups"
```

Both items must be siblings (share the same parent).

## Soft-link an item under a second parent

A soft link makes an item appear under another parent as well, without moving
it. In the [browser view](browser-mode.md) the linked item shows as a dashed
copy under its host.

```bash
task link "Launch blog" 7     # item 7 now also appears under "Launch blog"
task unlink "Launch blog" 7
```

## Delete items

```bash
task delete 4                 # delete an item and everything under it
task remove "Draft outline"   # alias for delete

task clear "Launch blog"      # delete completed items under one parent
task clear                    # delete every completed item, anywhere

task nuke                     # erase all data (asks for confirmation)
```
