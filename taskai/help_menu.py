


help_general = """

Welcome to Task! Here's what you can do:

Everything is an item - there is no separate concept of a "list". Items form a
tree: any item can be a parent of any other item, to whatever depth you like.

Viewing:
'task show all' --> show every item, with ids prepended, as a tree
'task show {id}' --> show full details for the item with that id
'task show {name|fnmatch pattern}' --> find the first item whose name matches, then show it

Creating:
'task create {name} {--field value ...}' --> create a new top-level (root) item - use this when there's no existing parent to attach to
'task add {parent id|name} {name} {--field value ...}' --> create a new item as a child of an EXISTING parent item - the parent must already exist

Updating (these require the item's id, not its name):
'task update {id} {--field value ...}' --> update fields on an item
'task rename {id} {new name}' --> rename an item
'task status {id} {text}' --> set an item's status string
'task comment {id} {text}' --> add a comment to an item
'task complete {id}' / 'task done {id}' --> mark an item, and all its descendants, complete
'task reorder {id1} before|after {id2}' --> reorder id1 relative to id2 among its siblings (both must be ids)

Updating (these accept either an id or a name):
'task move {id|name} {new parent id|name}' --> reparent an item; pass an empty string for the new parent to move it to the top level
'task link {parent id|name} {item id|name}' --> soft-link item under parent, without reparenting it

Deleting:
'task delete {id}' / 'task delete {name}' --> delete an item, and all its descendants, by id or name
'task remove ...' --> alias for 'task delete ...'
'task clear' --> delete every completed item
'task clear {parent id|name}' --> delete every completed item under a given parent
'task nuke' --> delete ALL data for a fresh start (asks for confirmation)

Item fields (pass as '--field value' to create/add/update):
  description  string
  due_by       MM-DD-YYYY
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

Other:
'task setup' --> interactive first-run setup
'task repair' --> attempt to repair a corrupted database
'task pomo {on_minutes} {off_minutes}' --> start a pomodoro timer

"""


help_menu = {
    "general": help_general,
}