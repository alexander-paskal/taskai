# taskai

A command-line task manager with AI features.

```bash
pip install taskai-cli
```

---

## Setup

```bash
task setup
```
---

## Commands

```
task                              interactive mode

task show all                     show everything
task show <id|name>               show a specific item
task show <id1>,<id2>,...         show multiple items

task create <name>                create a top-level item
task add <parent> <name>          add a child item
task update <id> --field value    update any field
task rename <id> <new name>       rename an item
task move <item> <new parent>     reparent an item
task complete <id>                mark complete (recursive)
task delete <id|name>             delete by id or name
task delete completed             delete all completed items
task clear <parent>               delete completed under a parent

task comment <id> <text>          add a comment
task depend <src_id> <dst_id>     src depends on dst
task link <parent> <item>         soft-link two items
task reorder <id1> before|after <id2>

task status <id> <text>           set a status string
task pomo <on_mins> <off_mins>    pomodoro timer

task ai <prompt>                  natural language → commands
task ai headstart <id>            AI suggests next step, saved as comment

task config show                  list current config
task config set <key> <value>     set a config value
task config get <key>             get a config value
task config pop <key>             remove a config value

task repair                       repair the database
task nuke                         delete all data (asks to confirm)
```

### Item fields

Pass any of these as `--field value` to `create`, `add`, or `update`:

| Field | Format | Example |
|---|---|---|
| `description` | string | `--description "needs review"` |
| `due_by` | MM-DD-YYYY | `--due_by 08-15-2026` |
| `priority` | integer | `--priority 2` |
| `status` | string | `--status "in progress"` |
| `completed` | bool | `--completed true` |
| `depends_on` | comma-separated ids | `--depends_on 3,7` |

---

## Config

AI features require a model, set as a `provider/model` string (via [litellm](https://github.com/BerriAI/litellm)),
plus that provider's credentials set as environment variables (e.g. `GEMINI_API_KEY`, `OPENAI_API_KEY`).
`task setup` will walk you through picking a provider and model and tell you which env vars it needs.

```bash
task config set AI_MODEL gemini/gemini-2.0-flash
```

---

## Example

```
task create "Today"
task add "Today" "Morning run"
task add "Today" "Review pull requests" --status "blocked"
task add "Today" "Call dentist" --due_by 08-02-2026
task show "Today"
task complete 4
task show "Today"
task exit
```

Or:

```bash
task ai "add a task called 'Reply to Alex' under Today, and mark the dentist task as done"
```

---

## Another Example

```bash
task create "Launch website"

# add subtasks (by name or id)
task add "Launch website" "Write copy"
task add "Launch website" "Design mockups" --priority 1
task add "Launch website" "Set up hosting" --due_by 08-15-2026

# check your work
task show "Launch website"

# ask AI what to do first on a specific task
task ai headstart 3

# mark something done and clean up
task complete 2
task clear "Launch website"
```