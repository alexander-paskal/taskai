


help_general = """

Welcome to Task! Here's what you can do:

Everything is an item - there is no separate concept of a "list". Items form a
tree: any item can be a parent of any other item, to whatever depth you like.

Viewing:
'task show all' --> show every item, with ids prepended, as a tree
'task show {id}' --> show full details for the item with that id
'task show {name|fnmatch pattern}' --> match an item by name (or glob pattern) and show it
'task show {attr}{op}{value} ...' --> show only items matching every filter, each with its parent chain for context
  ops: = > < >= <= ; text uses = with fnmatch (name=Write*), the rest compare numbers/dates
  no spaces around the operator; quote each expression so your shell doesn't treat > < as redirects
  e.g. task show 'status=IN PROGRESS' 'priority>=2' 'due_by<12-31-2026'
  due_by/created_on also accept the keywords today/tomorrow, e.g. 'due_by=today', 'due_by<tomorrow'

Creating:
'task create {name} {--field value ...}' --> create a new top-level (root) item - use this when there's no existing parent to attach to
'task add {parent id|name} {name} {--field value ...}' --> create a new item as a child of an EXISTING parent item - the parent must already exist

Modifying items (an id or a name works everywhere):
'task update {id|name} {--field value ...}' --> update fields on an item
'task rename {id|name} {new name}' --> rename an item
'task status {id|name} {text}' --> set an item's status string
'task comment {id|name} {text}' --> add a comment to an item
'task complete {id|name}' / 'task done {id|name}' --> mark an item complete; add -r (or -recursive) to also complete all its descendants
'task undone {id|name}' --> mark an item not complete; add -r (or -recursive) to also un-complete all its descendants
'task reorder {id1|name} before|after {id2|name}' --> reorder one item relative to a sibling
'task move {id|name} {new parent id|name}' --> reparent an item; pass an empty string for the new parent to move it to the top level
'task link {parent id|name} {item id|name}' --> soft-link item under parent, without reparenting it
'task unlink {parent id|name} {item id|name}' --> remove a soft-link previously added with 'task link'

Chains (a sequence of items, distinct from parent/child - a chain member can
still have its own children, which show up alongside it, not inside it):
'task next {prev id|name} {name} {--field value ...}' --> create a new item and append it to the end of the chain starting at prev
'task chain {prev id|name} {node id|name}' --> link an existing item into a chain, right after prev; if node has a parent, it's popped off it first
'task unchain {node id|name}' --> remove an item from its chain (it survives as an item) - it becomes a child of the chain head's parent instead

Deleting:
'task delete {id}' / 'task delete {name}' --> delete an item, and all its descendants, by id or name
'task delete {id} -chain' --> delete the ENTIRE chain the item belongs to (not just that item onward), no matter which link you target
'task remove ...' --> alias for 'task delete ...'
'task clear' --> delete every completed item, chain members included
'task clear {parent id|name}' --> delete every completed item under a given parent, including anything chained off it
'task nuke' --> delete ALL data for a fresh start (asks for confirmation)

Item fields (pass as named options, e.g. --priority 2, to create/add/update):
  description  string
  due_by       MM-DD-YYYY, YYYY-MM-DD, MM/DD/YYYY, "Dec 31, 2026", or the keywords today/tomorrow
  priority     integer
  status       string
  completed    true|false

AI:
'task ai {prompt}' --> feed a prompt to an LLM, which converts it into a series of the commands above and runs them
  --context {path[,path...]}  fold the contents of one or more files into the prompt as extra context
  --reasoning {level}         how hard the model should think before answering: minimal|low|medium|high|disable|none
'task ai headstart {id}' --> ask an LLM to suggest the next concrete step for an item; the answer is saved as a comment

Config:
'task config show' / 'task config list' --> list current config
'task config set {key} {value}' --> set a config value
'task config get {key}' --> get a config value
'task config pop {key}' --> remove a config value
  browser-relevant keys: STATUS_COLORS="RUNNING=green,BLOCKED=red,..." recolors the DAG node's status label per status string

Other:
'task help' --> show this help
'task examples' --> worked, copy/pasteable command sequences for common workflows
'task setup' --> interactive first-run setup
'task browser {port}' --> launch the web UI: a canvas view of the item tree, click a node to edit it, console for raw commands. Port defaults to 8000.
'task repair' --> attempt to repair a corrupted database
'task pomo {on_minutes} {off_minutes}' --> start a pomodoro timer

"""


help_examples = """

Worked examples - copy/paste and adapt. Names with spaces must be quoted.

Build a small project tree:
  task create "Launch blog" --due_by 09-15-2026
  task add "Launch blog" "Write first post" --priority 1
  task add "Launch blog" "Set up hosting"
  task add "Write first post" "Draft outline"
  task show all

Work an item and finish it:
  task status 4 "in progress"
  task comment 4 "stuck on the intro paragraph"
  task done 4                       # completes just item 4
  task done 4 -r                    # completes item 4 and everything under it
  task undone 4                     # reopen it

Reorganize (reorder/rename/status take an id; move takes an id or a name):
  task move "Set up hosting" "Write first post"
  task reorder 3 before 2
  task rename 2 "Publish first post"

Soft-link an item in a second place without moving it:
  task link "Launch blog" 7        # item 7 now also shows under "Launch blog"
  task unlink "Launch blog" 7

Build and work a chain of tasks:
  task add "Launch blog" "Write outline" --priority 1
  task next "Write outline" "Draft intro"
  task next "Draft intro" "Draft body"
  task show all                    # renders nested under "Write outline", linked with a down-arrow
  task done "Write outline"
  task done "Draft intro"
  task clear "Launch blog"         # sweeps both done items; "Draft body" becomes the new head

Pull an item out of a chain, or delete the whole thing:
  task unchain "Draft body"             # now a normal child of "Launch blog", not a sequence member
  task next "Write first post" "Edit first post"
  task delete "Write first post" -chain # deletes the whole chain, from any link in it

Clean up:
  task clear "Launch blog"         # delete completed items under that parent
  task clear                       # delete every completed item, anywhere
  task delete "Draft outline"      # delete an item and its descendants

Let the AI do it:
  task ai "add a task under Launch blog to buy a domain, due next Friday"
  task ai "break Set up hosting into smaller subtasks" --context notes.md
  task ai headstart 5              # suggest the next concrete step for item 5

Tip: 'task show all' lists ids. A name that matches more than one item is
rejected - use the id in that case.
"""


help_menu = {
    "general": help_general,
    "examples": help_examples,
}